from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import asyncio

@register(
    "qq_member_verify",
    "huotuo146",
    "QQ群成员验证插件",
    "1.0.4",
    "https://github.com/huntuo146/astrbot_plugin_Group-Verification"
)
class QQGroupVerifyPlugin(Star):
    def __init__(self, context: Context, config):
        super().__init__(context)
        self.context = context
        self.config = config
        self.pending = {}         # {user_id (str): group_id (int)}
        self.timeout_tasks = {}   # {user_id (str): asyncio.Task}

    @filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE)
    async def handle_event(self, event: AstrMessageEvent):
        raw = event.message_obj.raw_message
        platform = event.get_platform_name()

        if platform != "aiocqhttp":
            return

        post_type = raw.get("post_type")
        message_type = raw.get("message_type")

        # ✅ 群成员加入（post_type: notice）
        if post_type == "notice" and raw.get("notice_type") == "group_increase":
            uid = str(raw.get("user_id"))
            gid = raw.get("group_id")
            self.pending[uid] = gid

            logger.info(f"[QQ Verify] 用户 {uid} 加入群 {gid}，加入验证列表")

            await event.bot.api.call_action(
                "send_group_msg",
                group_id=gid,
                message=f'[CQ:at,qq={uid}] 欢迎加入，请在 5 分钟内 @我 并发送 "{self.config.get("verification_word", "进行验证")}" 以完成验证，否则将被自动请出群聊'
            )

            task = asyncio.create_task(self._timeout_kick(uid, gid))
            self.timeout_tasks[uid] = task

        # ✅ 群消息事件（post_type: message）
        elif post_type == "message" and message_type == "group":
            uid = str(event.get_sender_id())
            gid = raw.get("group_id")
            text = event.message_str.strip()
            message_chain = raw.get("message", [])

            bot_id = str(event.get_self_id())
            at_me = any(seg.get("type") == "at" and str(seg.get("data", {}).get("qq")) == bot_id for seg in message_chain)

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
            await asyncio.sleep(self.config.get("verification_timeout", 300))

            if uid not in self.pending:
                logger.info(f"[QQ Verify] 用户 {uid} 已验证，取消踢出")
                return

            bot = self.context.get_platform("aiocqhttp").get_client()

            try:
                user_info = await bot.api.call_action("get_group_member_info", group_id=gid, user_id=int(uid))
                nickname = user_info.get("nickname", uid)
            except Exception as e:
                logger.error(f"[QQ Verify] 获取昵称失败: {e}")
                nickname = uid

            await bot.api.call_action(
                "send_group_msg",
                group_id=gid,
                message=self.config.get("failure_message", "验证失败，用户将被踢出群聊")
            )

            await asyncio.sleep(self.config.get("kick_delay", 10))

            await bot.api.call_action(
                "set_group_kick",
                group_id=gid,
                user_id=int(uid),
                reject_add_request=False
            )

            await bot.api.call_action(
                "send_group_msg",
                group_id=gid,
                message=self.config.get("kick_message", "{member_name} 因验证失败被踢出群聊").format(member_name=nickname)
            )

            logger.info(f"[QQ Verify] 用户 {uid} 验证失败，已踢出群 {gid}")

        except asyncio.CancelledError:
            logger.info(f"[QQ Verify] 踢出任务被取消：用户 {uid}")
        finally:
            self.pending.pop(uid, None)
            self.timeout_tasks.pop(uid, None)
