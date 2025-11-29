import os
import shlex
from datetime import datetime, time, timezone, timedelta
from dateutil import parser

from nonebot import on_command, logger
from nonebot.adapters import Message
from nonebot.params import CommandArg
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, MessageSegment

from ..utils.data_manager import data_manager
from ..utils.ics_parser import ics_parser
from ..utils.html_image_generator import image_generator


group_schedule = on_command(
    "group_schedule",
    aliases={"群课表", "群友上什么", "群友在上什么", "群友在上什么课"},
    priority=5,
    force_whitespace=True,
    block=True,
)


@group_schedule.handle()
async def _(bot: Bot, event: GroupMessageEvent, arg: Message = CommandArg()):
    group_id = event.group_id
    user_data = data_manager.load_user_data()
    if str(group_id) not in user_data:
        await group_schedule.send("本群还没有人绑定课表哦~")
        return None

    user_ids = user_data[str(group_id)]

    args = shlex.split(arg.extract_plain_text())
    logger.info(f"{group_id} 查询群课表: {args}")
    day = args[0].replace(".", "-") if args and args != [] else ""

    shanghai_tz = timezone(timedelta(hours=8))
    now = datetime.now(shanghai_tz)

    try:
        if day == "":
            target_time = now
            target_date = now.date()
        elif day.isdigit():
            offset_days = int(day)
            target_date = now.date() + timedelta(days=offset_days)
            target_time = datetime.combine(now.date(), time.min).astimezone(
                shanghai_tz
            ) + timedelta(seconds=1)
        else:
            target_time = parser.parse(day)
            target_date = target_time.date()
            target_time = datetime.combine(now.date(), time.min).astimezone(
                shanghai_tz
            ) + timedelta(seconds=1)
    except Exception:
        await group_schedule.finish(
            "时间格式错误，请输入数字或日期，例如：3 或 2025-11-01"
        )

    next_courses = []

    for user_id in user_ids:
        ics_path = data_manager.get_ics_file_path(user_id)
        if not os.path.exists(ics_path):
            continue

        try:
            courses = ics_parser.parse_ics_file(ics_path)
        except Exception:
            continue

        today_courses = [c for c in courses if c["start_time"].date() == target_date]
        current = next_ = None

        for course in today_courses:
            if course["start_time"] <= target_time < course["end_time"]:
                current = course
                break
            elif course["start_time"] > target_time:
                if not next_ or course["start_time"] < next_["start_time"]:
                    next_ = course

        display = current or next_
        user_info = await bot.get_group_member_info(group_id=group_id, user_id=user_id)
        nickname = (
            user_info["card"]
            if user_info["card"] is not None and user_info["card"] != ""
            else user_info["nickname"]
        )

        if display:
            next_courses.append(
                {
                    "summary": display["summary"],
                    "description": display["description"],
                    "location": display["location"],
                    "start_time": display["start_time"],
                    "end_time": display["end_time"],
                    "user_id": user_id,
                    "nickname": nickname,
                }
            )
        else:
            next_courses.append(
                {
                    "summary": "今日无课",
                    "description": "",
                    "location": "",
                    "start_time": None,
                    "end_time": None,
                    "user_id": user_id,
                    "nickname": nickname,
                }
            )

    if not next_courses:
        await group_schedule.send("群友们接下来都没有课啦！")
        return None

    next_courses.sort(key=lambda x: (x["start_time"] is None, x["start_time"]))
    image_path = await image_generator.generate_schedule_image(next_courses)
    await group_schedule.send(MessageSegment.image(image_path))
