import math
import os
from datetime import datetime, timezone, timedelta
from typing import List, Dict

from nonebot import logger, get_bot
from nonebot.adapters.onebot.v11 import MessageSegment

from ..config import config
from .data_manager import data_manager
from .ics_parser import ics_parser

async def check_and_send_reminders():
    """
    定期检查并发送课程提醒。
    range 参数指定检查的时间范围（分钟），与 cron 的检查间隔相对应。
    """
    if not config.course_reminder_enabled:
        return

    shanghai_tz = timezone(timedelta(hours=8))
    now = datetime.now(shanghai_tz)
    
    # 提醒时间点：当前时间 + 偏移量
    # 检查在 (now + offset) 至 (now + offset + range) 内开始的课
    reminder_time = now + timedelta(minutes=config.course_reminder_offset)
    reminder_time_end = reminder_time + timedelta(minutes=config.course_reminder_interval)
    logger.debug(f"正在检查 {reminder_time.strftime('%Y-%m-%d %H:%M')} 到 {reminder_time_end.strftime('%Y-%m-%d %H:%M')} 的课程提醒。")

    user_data: Dict[str, List[int]] = data_manager.load_user_data()
    
    try:
        bot = get_bot()
    except Exception as e:
        logger.warning(f"获取 Bot 失败，跳过本次提醒检查: {e}")
        return

    for group_id_str, user_ids in user_data.items():
        group_id = int(group_id_str)
        for user_id in user_ids:
            ics_path = data_manager.get_ics_file_path(user_id)
            if not os.path.exists(ics_path):
                continue
            
            try:
                courses: List[Dict] = ics_parser.parse_ics_file(str(ics_path))
            except Exception as e:
                logger.error(f"解析用户 {user_id} 的课表失败: {e}")
                continue
            
            courses = ics_parser.merge_duplicate_courses(courses)

            for course in courses:

                start_time = course["start_time"]
                                
                # 检查课程是否在 reminder_time 到 reminder_time_end 之间开始
                if (reminder_time <= start_time < reminder_time_end):
                    
                    # 匹配成功，发送提醒
                    summary = course["summary"]
                    location = course.get("location", "未知地点")
                    minutes_left = math.ceil((start_time - now).total_seconds() / 60)
                    
                    msg = (
                        MessageSegment.at(user_id) + 
                        f" 课程提醒：\n"
                        f"课程：{summary}\n"
                        f"时间：{start_time.strftime('%H:%M')}\n"
                        f"地点：{location}\n"
                        f"还有 {minutes_left} 分钟就要上课啦，记得做好准备哦！"
                    )
                    
                    try:
                        await bot.send_group_msg(group_id=group_id, message=msg)
                        logger.debug(f"已发送提醒给用户 {user_id} (群 {group_id}): {summary}")
                    except Exception as e:
                        logger.error(f"发送提醒到群 {group_id} 失败: {e}")
