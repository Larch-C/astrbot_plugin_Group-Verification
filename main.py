from astrbot.api.event import filter, AstrMessageEvent, EventMessageType
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import asyncio

@register("qq_member_verify", "YourName", "QQ群成员验证插件", "1.0.0", "https://your.repo.url")
class QQGroupVerifyPlugin(Star):
    def __init__(self, context: Context, config):
        super().__init__(context)
        self.context = context
        self.config = config
        self.pending = {}  # {user_id: group_id}

    @filter.event_message_type(EventMessageType.ALL)
    async def handle_event(self, event: AstrMessageEvent):
        raw = event.message_obj.raw_message
        platform = event.get_platform_name()

        if platform != "aiocqhttp":
            return

        # 新成员入群
        if raw.get("post_type") == "notice" and raw.get("notice_type") == "group_increase":
            uid = raw.get("user_id")
            gid = raw.get("group_id")
            self.pending[uid] = gid

            await event.bot.api.call_action(
                "send_group_msg",
                group_id=gid,
                message=f"[CQ:at,qq={uid}] 欢迎加入，请在 5 分钟内发送 “进行验证” 以完成验证，否则将被自动请出群聊"
            )

            asyncio.create_task(self._timeout_kick(uid, gid))

        # 群消息：验证处理
        elif raw.get("post_type") == "message" and raw.get("message_type") == "group":
            uid = event.get_sender_id()
            gid = raw.get("group_id")
            text = event.message_str.strip()

            if uid in self.pending and text == self.config["verification_keyword"]:
                self.pending.pop(uid, None)
                await event.plain_result(f"[CQ:at,qq={uid}] 验证成功，欢迎加入！")
                event.stop_event()

    async def _timeout_kick(self, uid: int, gid: int):
        await asyncio.sleep(self.config["verification_timeout"])

        if uid in self.pending:
            await self.context.get_platform("aiocqhttp") \
                .get_client().api.call_action(
                    "send_group_msg",
                    group_id=gid,
                    message=f"[CQ:at,qq={uid}] 验证失败，你将于 {self.config['kick_delay']} 秒后自动请出群聊"
                )

            await asyncio.sleep(self.config["kick_delay"])

            await self.context.get_platform("aiocqhttp") \
                .get_client().api.call_action(
                    "set_group_kick",
                    group_id=gid,
                    user_id=uid,
                    reject_add_request=False
                )

            self.pending.pop(uid, None)
            logger.info(f"[QQ Verify] 用户 {uid} 因验证失败被踢出群 {gid}")
