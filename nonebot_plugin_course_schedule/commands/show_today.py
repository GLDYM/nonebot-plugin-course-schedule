import os
import shlex
from datetime import datetime, timezone, timedelta
from dateutil import parser
from typing import Union

from nonebot import on_command, logger
from nonebot.adapters import Message
from nonebot.params import CommandArg
from nonebot.adapters.onebot.v11 import (
    Bot,
    GroupMessageEvent,
    PrivateMessageEvent,
    MessageSegment,
)
from ..utils.data_manager import data_manager
from ..utils.ics_parser import ics_parser
from ..utils.html_image_generator import image_generator

show_today = on_command(
    "show_today",
    aliases={"课表", "查看课表", "查看今日课表", "查看我的课表"},
    force_whitespace=True,
    priority=5,
    block=True,
)


@show_today.handle()
async def _(
    bot: Bot,
    event: Union[GroupMessageEvent, PrivateMessageEvent],
    arg: Message = CommandArg(),
):
    group_id = event.group_id if isinstance(event, GroupMessageEvent) else None
    user_id = event.user_id

    args = shlex.split(arg.extract_plain_text())
    logger.info(f"{user_id} 查询课表: {args}")
    day = args[0].replace(".", "-") if args and args != [] else ""

    shanghai_tz = timezone(timedelta(hours=8))
    now = datetime.now(shanghai_tz)

    try:
        if day == "":
            target_date = now.date()
            mode = "today"
        elif day.isdigit():
            offset_days = int(day)
            target_date = now.date() + timedelta(days=offset_days)
            mode = "offset"
        else:
            target_time = parser.parse(day)
            target_date = target_time.date()
            mode = "specific"
    except Exception:
        await show_today.finish("时间格式错误，请输入数字或日期，例如：3 或 2025-11-01")

    ics_path = data_manager.get_ics_file_path(user_id)
    if not os.path.exists(ics_path):
        await show_today.finish(
            "你还没有绑定课表哦~请在群内发送 绑定课表 指令，然后发送 .ics 文件或 WakeUp 口令来绑定。"
        )

    courses = ics_parser.parse_ics_file(ics_path)
    if mode == "today":
        # 不带参数，只显示剩下的课程
        filtered_courses = [
            c
            for c in courses
            if c["start_time"].date() == target_date and c["end_time"] > now
        ]
    else:
        # 指定天，查询当天全部课程（包括 0）
        filtered_courses = [c for c in courses if c["start_time"].date() == target_date]

    if not filtered_courses:
        await show_today.finish("当日没有课啦！")

    filtered_courses.sort(key=lambda x: x["start_time"])

    # 那是谁？是谁？是谁？ 那是复旦，复旦教务，复旦教务~
    merged_courses = []
    seen = {}
    for course in filtered_courses:
        key = (course["summary"], course["start_time"], course["end_time"])
        if key in seen:
            seen[key]["location"] += f", {course['location']}"
        else:
            seen[key] = course
            merged_courses.append(course)
    filtered_courses = merged_courses

    if group_id:
        user_info = await bot.get_group_member_info(group_id=group_id, user_id=user_id)
        nickname = (
            user_info["card"]
            if user_info["card"] is not None and user_info["card"] != ""
            else user_info["nickname"]
        )
    else:
        user_info = await bot.get_stranger_info(user_id=user_id)
        nickname = user_info["nickname"]

    for course in filtered_courses:
        course["nickname"] = nickname

    image_path = (
        await image_generator.generate_user_schedule_image(filtered_courses, nickname)
        if mode == "today"
        else await image_generator.generate_user_schedule_image(
            filtered_courses, nickname, target_date
        )
    )

    await show_today.finish(MessageSegment.image(image_path))
