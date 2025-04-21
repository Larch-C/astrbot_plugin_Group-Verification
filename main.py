from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import asyncio

@register("qq_member_verify", "huotuo146", "QQ群成员验证插件", "1.0.1", "https://github.com/huntuo146/astrbot_plugin_Group-Verification/blob/master/README.mdl")
class QQGroupVerifyPlugin(Star):
    def __init__(self, context: Context, config):
        super().__init__(context)
        self.context = context
        self.config = config
        self.pending = {}  # {user_id: group_id}

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def handle_event(self, event: AstrMessageEvent):
        raw = event.message_obj.raw_message
        platform = event.get_platform_name()

        if platform != "aiocqhttp":
            return

        # 用户入群处理
        if raw.get("post_type") == "notice" and raw.get("notice_type") == "group_increase":
            uid = raw.get("user_id")
            gid = raw.get("group_id")
            # 同时存储整数和字符串形式以防止类型不一致
            self.pending[int(uid)] = gid
            self.pending[str(uid)] = gid
            
            logger.info(f"[QQ Verify] 用户 {uid} 加入群 {gid}，已加入验证列表")

            # 修复引号问题，使用不同的引号类型
            await event.bot.api.call_action(
                "send_group_msg",
                group_id=gid,
                message=f'[CQ:at,qq={uid}] 欢迎加入，请在 5 分钟内 @我 并发送 "{self.config["verification_keyword"]}" 以完成验证，否则将被自动请出群聊'
            )

            asyncio.create_task(self._timeout_kick(uid, gid))

        # 消息处理：检测是否为验证指令
        elif raw.get("post_type") == "message" and raw.get("message_type") == "group":
            uid = event.get_sender_id()
            gid = raw.get("group_id")
            text = event.message_str.strip()
            message_chain = raw.get("message", [])

            # 检查是否@了机器人
            bot_id = str(event.get_self_id())
            at_me = any(seg.get("type") == "at" and str(seg.get("data", {}).get("qq")) == bot_id for seg in message_chain)

            logger.info(f"[DEBUG] 来自{uid}的消息: {text}, 是否@我: {at_me}")
            
            # 同时检查整数和字符串形式的用户ID
            uid_int = int(uid) if str(uid).isdigit() else None
            uid_str = str(uid)
            
            is_in_pending = (uid_int in self.pending) or (uid_str in self.pending)
            has_keyword = self.config["verification_keyword"] in text
            
            logger.info(f"[DEBUG] 用户{uid}验证检查: 在待验证列表中:{is_in_pending}, @我:{at_me}, 包含关键词:{has_keyword}")
            logger.info(f"[DEBUG] pending列表: {self.pending}")

            # 验证成功条件
            if is_in_pending and at_me and has_keyword:
                # 清理两种类型的ID
                if uid_int is not None:
                    self.pending.pop(uid_int, None)
                self.pending.pop(uid_str, None)
                
                await event.bot.api.call_action(
                    "send_group_msg",
                    group_id=gid,
                    message=f"[CQ:at,qq={uid}] 恭喜你验证成功，欢迎加入群聊！"
                )
                logger.info(f"[QQ Verify] 用户 {uid} 在群 {gid} 验证成功")
                event.stop_event()

    # 超时踢人逻辑
    async def _timeout_kick(self, uid: int, gid: int):
        await asyncio.sleep(self.config["verification_timeout"])
        
        # 检查整数和字符串形式
        uid_int = int(uid)
        uid_str = str(uid)
        is_in_pending = (uid_int in self.pending) or (uid_str in self.pending)
        
        logger.info(f"[QQ Verify] 检查用户 {uid} 验证超时状态，是否在待验证列表: {is_in_pending}")

        if is_in_pending:
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

            # 清理两种形式的ID
            self.pending.pop(uid_int, None)
            self.pending.pop(uid_str, None)
            logger.info(f"[QQ Verify] 用户 {uid} 因验证失败被踢出群 {gid}")
