from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import asyncio
from typing import Dict, Any

@register(
    "qq_member_verify",
    "huotuo146",
    "QQ群成员验证插件",
    "1.1.1",  # 版本号微调
    "https://github.com/huntuo146/astrbot_plugin_Group-Verification"
)
class QQGroupVerifyPlugin(Star):
    def __init__(self, context: Context, config: Dict[str, Any]):
        super().__init__(context)
        self.context = context
        
        self.verification_word = config.get("verification_word", "进行验证")
        self.welcome_message = config.get("welcome_message", "验证成功，欢迎你的加入！")
        self.failure_message = config.get("failure_message", "验证超时，你将被请出本群。")
        self.kick_message = config.get("kick_message", "{member_name} 因未在规定时间内完成验证，已被请出本群。")
        self.verification_timeout = config.get("verification_timeout", 300)
        self.kick_delay = config.get("kick_delay", 5)

        self.pending: Dict[str, int] = {}
        self.timeout_tasks: Dict[str, asyncio.Task] = {}

    # <--- 修正: 将所有事件处理逻辑合并回 handle_event ---
    @filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE)
    async def handle_event(self, event: AstrMessageEvent):
        if event.get_platform_name() != "aiocqhttp":
            return

        raw = event.message_obj.raw_message
        post_type = raw.get("post_type")

        # 根据 post_type 分发到不同的处理逻辑
        if post_type == "notice":
            notice_type = raw.get("notice_type")
            if notice_type == "group_increase":
                await self._process_new_member(event)
            elif notice_type == "group_decrease":
                await self._process_member_decrease(event)
        
        elif post_type == "message" and raw.get("message_type") == "group":
            await self._process_verification_message(event)

    async def _process_new_member(self, event: AstrMessageEvent):
        """处理新成员入群的逻辑"""
        raw = event.message_obj.raw_message
        uid = str(raw.get("user_id"))
        gid = raw.get("group_id")
        
        if uid in self.timeout_tasks:
            old_task = self.timeout_tasks.pop(uid, None)
            if old_task and not old_task.done():
                old_task.cancel()
        
        self.pending[uid] = gid
        logger.info(f"[QQ Verify] 用户 {uid} 加入群 {gid}，启动验证流程。")

        await event.bot.api.call_action(
            "send_group_msg",
            group_id=gid,
            message=f'[CQ:at,qq={uid}] 欢迎加入本群！请在 {self.verification_timeout // 60} 分钟内 @我 并发送“{self.verification_word}”以完成验证，否则将被自动移出群聊。'
        )

        task = asyncio.create_task(self._timeout_kick(uid, gid))
        self.timeout_tasks[uid] = task

    async def _process_verification_message(self, event: AstrMessageEvent):
        """处理群聊消息验证的逻辑"""
        uid = str(event.get_sender_id())
        if uid not in self.pending:
            return
        
        text = event.message_str.strip()
        raw = event.message_obj.raw_message
        gid = raw.get("group_id")

        bot_id = str(event.get_self_id())
        at_me = any(seg.get("type") == "at" and str(seg.get("data", {}).get("qq")) == bot_id for seg in raw.get("message", []))

        if at_me and self.verification_word in text:
            self.pending.pop(uid, None)
            task = self.timeout_tasks.pop(uid, None)

            if task and not task.done():
                task.cancel()
                logger.info(f"[QQ Verify] 用户 {uid} 验证成功，踢出任务已取消。")

            await event.bot.api.call_action(
                "send_group_msg",
                group_id=gid,
                message=f"[CQ:at,qq={uid}] {self.welcome_message}"
            )
            logger.info(f"[QQ Verify] 用户 {uid} 在群 {gid} 验证成功。")
            event.stop_event()

    async def _process_member_decrease(self, event: AstrMessageEvent):
        """处理成员减少的逻辑"""
        raw = event.message_obj.raw_message
        uid = str(raw.get("user_id"))

        if uid in self.pending:
            self.pending.pop(uid, None)
            task = self.timeout_tasks.pop(uid, None)
            if task and not task.done():
                task.cancel()
            logger.info(f"[QQ Verify] 待验证用户 {uid} 已离开群聊，清理其验证状态。")

    async def _timeout_kick(self, uid: str, gid: int):
        """在超时后执行踢人操作的协程（此部分无需修改）"""
        try:
            await asyncio.sleep(self.verification_timeout)

            if uid not in self.pending:
                logger.debug(f"[QQ Verify] 踢出任务唤醒，但用户 {uid} 已不在待验证列表，任务终止。")
                return

            bot = self.context.get_platform("aiocqhttp").get_client()
            nickname = uid

            try:
                user_info = await bot.api.call_action("get_group_member_info", group_id=gid, user_id=int(uid))
                nickname = user_info.get("card", "") or user_info.get("nickname", uid)
                
                await bot.api.call_action("send_group_msg", group_id=gid, message=self.failure_message)
                await asyncio.sleep(self.kick_delay)
                
                await bot.api.call_action("set_group_kick", group_id=gid, user_id=int(uid), reject_add_request=False)
                logger.info(f"[QQ Verify] 用户 {uid} ({nickname}) 验证超时，已从群 {gid} 踢出。")
                
                await bot.api.call_action("send_group_msg", group_id=gid, message=self.kick_message.format(member_name=nickname))
            
            except Exception as e:
                logger.error(f"[QQ Verify] 在为用户 {uid} 执行踢出流程时发生错误: {e}")

        except asyncio.CancelledError:
            logger.info(f"[QQ Verify] 踢出任务被取消：用户 {uid} 已验证或已离开。")
        finally:
            self.pending.pop(uid, None)
            self.timeout_tasks.pop(uid, None)
