from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import asyncio

@register(
    "qq_member_verify",
    "huotuo146",
    "QQ群成员验证插件",
    "1.0.3",
    "https://github.com/huntuo146/astrbot_plugin_Group-Verification"
)
class QQGroupVerifyPlugin(Star):
    def __init__(self, context: Context, config):
        super().__init__(context)
        self.context = context
        self.config = config
        self.pending = {}         # {user_id: group_id}
        self.timeout_tasks = {}   # {user_id: asyncio.Task}

    @filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE)
    async def handle_event(self, event: AstrMessageEvent):
        raw = event.message_obj.raw_message
        platform = event.get_platform_name()

        if platform != "aiocqhttp":
            return

        # 用户加入群
        if raw.get("post_type") == "notice" and raw.get("notice_type") == "group_increase":
            uid = raw.get("user_id")
            gid = raw.get("group_id")

            enabled_groups = self.config.get("enabled_groups", [])
            if enabled_groups and gid not in enabled_groups:
                logger.debug(f"[QQ Verify] 群 {gid} 未在启用验证列表中，忽略验证")
                return

            self.pending[str(uid)] = gid
            logger.info(f"[QQ Verify] 用户 {uid} 加入群 {gid}，已加入验证列表")

            verification_word = self.config.get("verification_word", "进行验证")
            timeout_minutes = int(self.config.get("verification_timeout", 300) / 60)
            join_prompt = self.config.get(
                "join_prompt",
                "欢迎 {member_name} 加入本群！请在{timeout}分钟内@机器人并回复\"{verification_word}\"完成验证，否则将被踢出群聊。"
            )
            prompt = join_prompt.format(
                member_name=f"[CQ:at,qq={uid}]",
                timeout=timeout_minutes,
                verification_word=verification_word
            )

            await event.bot.api.call_action(
                "send_group_msg",
                group_id=gid,
                message=prompt
            )

            task = asyncio.create_task(self._timeout_kick(str(uid), gid))
            self.timeout_tasks[str(uid)] = task

        # 群消息
        elif raw.get("post_type") == "message" and raw.get("message_type") == "group":
            uid = str(event.get_sender_id())
            gid = raw.get("group_id")

            enabled_groups = self.config.get("enabled_groups", [])
            if enabled_groups and gid not in enabled_groups:
                return

            text = event.message_str.strip()
            message_chain = raw.get("message", [])

            bot_id = str(event.get_self_id())
            at_me = any(
                seg.get("type") == "at" and str(seg.get("data", {}).get("qq")) == bot_id
                for seg in message_chain
            )

            is_in_pending = uid in self.pending
            has_keyword = self.config.get("verification_word", "进行验证") in text

            if is_in_pending and at_me and has_keyword:
                self.pending.pop(uid, None)
                task = self.timeout_tasks.pop(uid, None)
                if task and not task.done():
                    task.cancel()
                    logger.info(f"[QQ Verify] 用户 {uid} 验证成功，踢出任务已取消")

                await event.bot.api.call_action(
                    "send_group_msg",
                    group_id=gid,
                    message=f"[CQ:at,qq={uid}] {self.config.get('welcome_message', '欢迎信息')}"
                )
                logger.info(f"[QQ Verify] 用户 {uid} 在群 {gid} 验证成功")
                event.stop_event()

    async def _timeout_kick(self, uid: str, gid: int):
        try:
            timeout = self.config.get("verification_timeout", 300)
            await asyncio.sleep(timeout)

            if uid not in self.pending:
                logger.info(f"[QQ Verify] 用户 {uid} 已验证，取消踢出操作")
                return

            bot = self.context.get_platform("aiocqhttp").get_client()

            try:
                user_info = await bot.api.call_action(
                    "get_group_member_info", group_id=gid, user_id=int(uid)
                )
                nickname = user_info.get("nickname", uid)
            except Exception as e:
                logger.error(f"[QQ Verify] 获取用户昵称失败: {e}")
                nickname = uid

            failure_message = self.config.get("failure_message", "验证失败，你将在{countdown}秒后被踢出该群聊")
            kick_delay = self.config.get("kick_delay", 60)

            await bot.api.call_action(
                "send_group_msg",
                group_id=gid,
                message=failure_message.format(countdown=kick_delay)
            )

            await asyncio.sleep(kick_delay)

            await bot.api.call_action(
                "set_group_kick",
                group_id=gid,
                user_id=int(uid),
                reject_add_request=False
            )

            kick_message = self.config.get(
                "kick_message", "{member_name}未完成验证，已被踢出群聊"
            ).format(member_name=nickname)

            await bot.api.call_action(
                "send_group_msg",
                group_id=gid,
                message=kick_message
            )

            logger.info(f"[QQ Verify] 用户 {uid} 因验证失败被踢出群 {gid}")

        except asyncio.CancelledError:
            logger.info(f"[QQ Verify] 超时踢出任务被取消：用户 {uid}")
        finally:
            self.pending.pop(uid, None)
            self.timeout_tasks.pop(uid, None)
