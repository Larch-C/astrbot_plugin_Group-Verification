from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import asyncio

@register("qq_member_verify", "huotuo146", "QQ群成员验证插件", "1.0.1", "https://github.com/huntuo146/astrbot_plugin_Group-Verification/blob/master/README.md")
class QQGroupVerifyPlugin(Star):
    def __init__(self, context: Context, config):
        super().__init__(context)
        self.context = context
        self.config = config
        self.pending = {}  # {user_id: group_id}

    @filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE)
    async def handle_event(self, event: AstrMessageEvent):
        raw = event.message_obj.raw_message
        platform = event.get_platform_name()

        if platform != "aiocqhttp":
            return

        if raw.get("post_type") == "notice" and raw.get("notice_type") == "group_increase":
            uid = raw.get("user_id")
            gid = raw.get("group_id")
            self.pending[int(uid)] = gid
            self.pending[str(uid)] = gid

            logger.info(f"[QQ Verify] 用户 {uid} 加入群 {gid}，已加入验证列表")

            await event.bot.api.call_action(
                "send_group_msg",
                group_id=gid,
                message=f'[CQ:at,qq={uid}] 欢迎加入，请在 5 分钟内 @我 并发送 "{self.config.get("verification_word", "默认验证词")}" 以完成验证，否则将被自动请出群聊'
            )

            asyncio.create_task(self._timeout_kick(uid, gid))

        elif raw.get("post_type") == "message" and raw.get("message_type") == "group":
            uid = event.get_sender_id()
            gid = raw.get("group_id")
            text = event.message_str.strip()
            message_chain = raw.get("message", [])

            bot_id = str(event.get_self_id())
            at_me = any(seg.get("type") == "at" and str(seg.get("data", {}).get("qq")) == bot_id for seg in message_chain)

            uid_int = int(uid) if str(uid).isdigit() else None
            uid_str = str(uid)

            is_in_pending = (uid_int in self.pending) or (uid_str in self.pending)
            has_keyword = self.config.get("verification_word", "默认验证词") in text

            if is_in_pending and at_me and has_keyword:
                if uid_int is not None:
                    self.pending.pop(uid_int, None)
                self.pending.pop(uid_str, None)

                await event.bot.api.call_action(
                    "send_group_msg",
                    group_id=gid,
                    message=f"[CQ:at,qq={uid}] {self.config.get('welcome_message', '欢迎信息')}"
                )

                logger.info(f"[QQ Verify] 用户 {uid} 在群 {gid} 验证成功")
                event.stop_event()

    async def _timeout_kick(self, uid: int, gid: int):
        await asyncio.sleep(self.config.get("verification_timeout", 300))

        uid_int = int(uid)
        uid_str = str(uid)
        is_in_pending = (uid_int in self.pending) or (uid_str in self.pending)

        logger.info(f"[QQ Verify] 检查用户 {uid} 验证超时状态，是否在待验证列表: {is_in_pending}")

        if is_in_pending:
            bot = self.context.get_platform("aiocqhttp").get_client()

            try:
                user_info = await bot.api.call_action("get_group_member_info", group_id=gid, user_id=uid)
                nickname = user_info.get("nickname", str(uid))
            except Exception as e:
                logger.error(f"[QQ Verify] 获取用户昵称失败: {e}")
                nickname = str(uid)

            await bot.api.call_action(
                "send_group_msg",
                group_id=gid,
                message=self.config.get("failure_message", "验证失败，用户将被踢出群聊")
            )

            await asyncio.sleep(self.config.get("kick_delay", 10))

            await bot.api.call_action(
                "set_group_kick",
                group_id=gid,
                user_id=uid,
                reject_add_request=False
            )

            await bot.api.call_action(
                "send_group_msg",
                group_id=gid,
                message=self.config.get("kick_message", "{member_name} 因验证失败被踢出群聊").format(member_name=nickname)
            )

            self.pending.pop(uid_int, None)
            self.pending.pop(uid_str, None)

            logger.info(f"[QQ Verify] 用户 {uid} 因验证失败被踢出群 {gid}")
