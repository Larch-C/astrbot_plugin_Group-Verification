from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import asyncio
import time

@register("qq_member_verify", "huotuo146", "QQ群成员验证插件", "1.0.1", "https://github.com/huntuo146/astrbot_plugin_Group-Verification/blob/master/README.mdl")
class QQGroupVerifyPlugin(Star):
    def __init__(self, context: Context, config):
        super().__init__(context)
        self.context = context
        self.config = config
        self.pending = {}  # {user_id: group_id}
        self.kick_tasks = {}  # {user_id: task}
        self.last_processed = {}  # 记录上次处理时间

    # 防止重复处理
    def _is_duplicate(self, event_type, data, window=1.0):
        key = f"{event_type}:{data}"
        now = time.time()
        
        if key in self.last_processed:
            if now - self.last_processed[key] < window:
                return True
        
        self.last_processed[key] = now
        return False

    # 确保参数签名完全匹配AstrBot的调用方式
    @filter.event_message_type(filter.EventMessageType.ALL)
    def handle_event(self, event: AstrMessageEvent, context=None, *args, **kwargs):
        # 转发到内部异步处理方法
        asyncio.create_task(self._handle_event_async(event))
        return None  # 返回None表示不拦截事件

    # 发送群消息的辅助方法
    async def _send_group_msg(self, bot, gid, message):
        try:
            await bot.api.call_action(
                "send_group_msg",
                group_id=gid,
                message=message
            )
            return True
        except Exception as e:
            logger.error(f"[QQ Verify] 发送消息失败: {e}")
            try:
                # 使用另一种方式尝试
                platform = self.context.get_platform("aiocqhttp")
                client = platform.get_client()
                await client.api.call_action(
                    "send_group_msg",
                    group_id=gid,
                    message=message
                )
                return True
            except Exception as e2:
                logger.error(f"[QQ Verify] 备选方式发送消息也失败: {e2}")
                return False

    # 踢出群成员的辅助方法
    async def _kick_group_member(self, bot, gid, uid):
        try:
            await bot.api.call_action(
                "set_group_kick",
                group_id=gid,
                user_id=uid,
                reject_add_request=False
            )
            return True
        except Exception as e:
            logger.error(f"[QQ Verify] 踢出用户失败: {e}")
            try:
                # 使用另一种方式尝试
                platform = self.context.get_platform("aiocqhttp")
                client = platform.get_client()
                await client.api.call_action(
                    "set_group_kick",
                    group_id=gid,
                    user_id=uid,
                    reject_add_request=False
                )
                return True
            except Exception as e2:
                logger.error(f"[QQ Verify] 备选方式踢出用户也失败: {e2}")
                return False

    # 内部异步处理方法
    async def _handle_event_async(self, event: AstrMessageEvent):
        try:
            raw = event.message_obj.raw_message
            platform = event.get_platform_name()

            if platform != "aiocqhttp":
                return

            # 入群处理
            if raw.get("post_type") == "notice" and raw.get("notice_type") == "group_increase":
                uid = raw.get("user_id")
                gid = raw.get("group_id")
                
                # 防止1秒内重复处理
                if self._is_duplicate("join", f"{uid}:{gid}"):
                    return
                
                # 存储用户ID (整数和字符串形式)
                self.pending[int(uid)] = gid
                self.pending[str(uid)] = gid
                
                # 尝试获取用户昵称
                member_name = f"QQ:{uid}"
                try:
                    info = await event.bot.api.call_action(
                        "get_group_member_info",
                        group_id=gid,
                        user_id=uid
                    )
                    if info and "card" in info and info["card"]:
                        member_name = info["card"]
                    elif info and "nickname" in info and info["nickname"]:
                        member_name = info["nickname"]
                except Exception as e:
                    logger.warning(f"[QQ Verify] 获取用户信息失败: {e}")
                
                # 格式化提示语
                timeout_minutes = int(self.config["verification_timeout"] / 60)
                join_prompt = self.config["join_prompt"].format(
                    member_name=member_name,
                    timeout=timeout_minutes,
                    verification_word=self.config["verification_word"]
                )
                
                # 发送验证提示
                await self._send_group_msg(
                    event.bot,
                    gid,
                    f'[CQ:at,qq={uid}] {join_prompt}'
                )
                
                logger.info(f"[QQ Verify] 用户 {uid} 加入群 {gid}, 已添加到验证列表")
                
                # 取消可能存在的旧任务
                if uid in self.kick_tasks:
                    task = self.kick_tasks[uid]
                    if task and not task.done():
                        task.cancel()
                
                # 创建并存储新任务
                task = asyncio.create_task(self._timeout_kick(event.bot, uid, gid, member_name))
                self.kick_tasks[uid] = task
            
            # 消息处理
            elif raw.get("post_type") == "message" and raw.get("message_type") == "group":
                uid = event.get_sender_id()
                gid = raw.get("group_id")
                msg_id = raw.get("message_id", "")
                
                # 防止重复处理
                if self._is_duplicate("msg", f"{uid}:{gid}:{msg_id}"):
                    return
                
                text = event.message_str.strip()
                message_chain = raw.get("message", [])
                
                # 检查是否@机器人
                bot_id = str(event.get_self_id())
                at_me = any(seg.get("type") == "at" and str(seg.get("data", {}).get("qq")) == bot_id for seg in message_chain)
                
                # 检查是否在验证列表
                in_pending = uid in self.pending or str(uid) in self.pending
                
                # 检查关键词
                has_keyword = self.config["verification_word"] in text
                
                logger.info(f"[QQ Verify] 消息检查: 用户:{uid}, 在列表:{in_pending}, @我:{at_me}, 包含关键词:{has_keyword}")
                
                # 验证成功
                if in_pending and at_me and has_keyword:
                    logger.info(f"[QQ Verify] 用户 {uid} 验证条件满足，准备取消踢出任务")
                    
                    # 取消踢人任务
                    if uid in self.kick_tasks:
                        task = self.kick_tasks[uid]
                        if task and not task.done():
                            task.cancel()
                            logger.info(f"[QQ Verify] 已取消用户 {uid} 的踢出任务")
                    
                    # 从待验证列表移除
                    self.pending.pop(uid, None)
                    self.pending.pop(str(uid), None)
                    
                    # 发送成功消息
                    await self._send_group_msg(
                        event.bot,
                        gid,
                        f'[CQ:at,qq={uid}] {self.config["welcome_message"]}'
                    )
                    
                    logger.info(f"[QQ Verify] 用户 {uid} 验证成功完成")
        
        except Exception as e:
            logger.error(f"[QQ Verify] 处理事件异常: {e}")

    # 超时踢人
    async def _timeout_kick(self, bot, uid, gid, member_name=""):
        try:
            logger.info(f"[QQ Verify] 开始验证计时: 用户 {uid} 在群 {gid}")
            
            # 验证超时
            await asyncio.sleep(self.config["verification_timeout"])
            
            # 检查是否仍需验证
            needs_verification = uid in self.pending or str(uid) in self.pending
            
            if not needs_verification:
                logger.info(f"[QQ Verify] 用户 {uid} 已验证，不需要踢出")
                return
            
            logger.info(f"[QQ Verify] 用户 {uid} 验证超时，准备发送警告")
            
            # 发送踢出警告
            kick_warning = self.config["failure_message"].format(
                countdown=self.config["kick_countdown"],
                member_name=member_name
            )
            
            await self._send_group_msg(
                bot,
                gid,
                f'[CQ:at,qq={uid}] {kick_warning}'
            )
            
            # 等待踢出倒计时
            logger.info(f"[QQ Verify] 开始踢出倒计时: {self.config['kick_countdown']}秒")
            await asyncio.sleep(self.config["kick_countdown"])
            
            # 再次检查是否仍需验证
            still_needs_verification = uid in self.pending or str(uid) in self.pending
            
            if not still_needs_verification:
                logger.info(f"[QQ Verify] 用户 {uid} 已验证，取消踢出")
                return
            
            logger.info(f"[QQ Verify] 倒计时结束，准备踢出用户 {uid}")
            
            # 执行踢出
            kick_success = await self._kick_group_member(bot, gid, uid)
            
            # 如果踢出成功，发送通知并清理列表
            if kick_success:
                # 发送踢出通知
                kick_message = self.config["kick_message"].format(
                    member_name=member_name
                )
                
                await self._send_group_msg(bot, gid, kick_message)
                
                # 清理待验证列表
                self.pending.pop(uid, None)
                self.pending.pop(str(uid), None)
                
                logger.info(f"[QQ Verify] 用户 {uid} 验证超时，已踢出群 {gid}")
        
        except asyncio.CancelledError:
            logger.info(f"[QQ Verify] 用户 {uid} 的踢人任务被取消")
        except Exception as e:
            logger.error(f"[QQ Verify] 踢人任务异常: {e}")
