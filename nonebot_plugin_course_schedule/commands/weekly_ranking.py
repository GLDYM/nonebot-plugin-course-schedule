from nonebot import on_command
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, MessageSegment
from datetime import datetime, timedelta, timezone
from ..utils.data_manager import data_manager
from ..utils.ics_parser import ics_parser
from ..utils.image_generator import image_generator
import os

weekly_ranking = on_command(
    "weekly_ranking", aliases={"上课排行", "本周上课排行"}, priority=5, block=True
)


@weekly_ranking.handle()
async def _(bot: Bot, event: GroupMessageEvent):
    group_id = event.group_id
    user_data = data_manager.load_user_data()
    if str(group_id) not in user_data:
        await weekly_ranking.send("本群还没有人绑定课表哦~")
        return None

    user_ids = user_data[str(group_id)]

    now = datetime.now(timezone(timedelta(hours=8)))
    today = now.date()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    ranking_data = []

    for user_id in user_ids:
        ics_path = data_manager.get_ics_file_path(user_id)
        if not os.path.exists(ics_path):
            continue

        try:
            courses = ics_parser.parse_ics_file(ics_path)
        except Exception:
            continue

        total_duration = timedelta()
        course_count = 0
        seen = {}

        for course in courses:
            # 那是谁？是谁？是谁？ 那是复旦，复旦教务，复旦教务~
            key = (course["summary"], course["start_time"], course["end_time"])
            if key in seen:
                continue
            else:
                seen[key] = course

            course_date = course["start_time"].date()
            if start_of_week <= course_date <= end_of_week:
                total_duration += course["end_time"] - course["start_time"]
                course_count += 1

        if course_count > 0:
            user_info = await bot.get_group_member_info(
                group_id=group_id, user_id=user_id
            )
            nickname = (
                user_info["card"]
                if user_info["card"] is not None and user_info["card"] != ""
                else user_info["nickname"]
            )
            ranking_data.append(
                {
                    "user_id": user_id,
                    "nickname": nickname,
                    "total_duration": total_duration,
                    "course_count": course_count,
                }
            )

    if not ranking_data:
        await weekly_ranking.send("本周大家都没有课呢！")
        return

    ranking_data.sort(key=lambda x: x["total_duration"], reverse=True)
    image_bytes = await image_generator.generate_ranking_image(
        ranking_data, start_of_week, end_of_week
    )
    await weekly_ranking.send(MessageSegment.image(image_bytes))
