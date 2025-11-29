import os
from datetime import datetime, timedelta
from typing import Union

import aiohttp

from nonebot import on_command, logger
from nonebot.matcher import Matcher
from nonebot.params import Arg

from nonebot.adapters.onebot.v11 import (
    Bot,
    GroupMessageEvent,
    PrivateMessageEvent,
    Message,
    MessageSegment,
)
from nonebot_plugin_apscheduler import scheduler

from ..utils.data_manager import data_manager
from ..utils.ics_parser import ics_parser


bind_schedule = on_command(
    "bind_schedule",
    aliases={"绑定课表", "绑定课程"},
    force_whitespace=True,
    priority=5,
    block=True,
)
unbind_schedule = on_command(
    "unbind_schedule",
    aliases={"解绑课表", "解绑课程"},
    force_whitespace=True,
    priority=5,
    block=True,
)
binding_requests = {}


@bind_schedule.handle()
async def handle_bind_entry(
    matcher: Matcher, event: Union[GroupMessageEvent, PrivateMessageEvent]
):
    user_id = event.user_id

    async def timeout():
        await matcher.send(
            MessageSegment.at(user_id)
            + "绑定请求已过期，请重新发送 绑定课表 命令以绑定。"
        )
        return None

    scheduler.add_job(
        func=timeout,
        trigger="date",
        run_date=datetime.now() + timedelta(seconds=60),
        id=f"expire_bind_request_{user_id}",
        replace_existing=True,
    )

    await matcher.send("请在60秒内发送你的 .ics 文件或 WakeUp 分享口令。")


@bind_schedule.got("schedule_input", prompt="等待你的课表文件或口令中…")
async def handle_schedule_input(
    bot: Bot,
    matcher: Matcher,
    event: Union[GroupMessageEvent, PrivateMessageEvent],
    schedule_input: Message = Arg(),
):
    group_id = event.group_id if isinstance(event, GroupMessageEvent) else None
    user_id = event.user_id
    scheduler.remove_job(f"expire_bind_request_{user_id}")

    # await matcher.send(f"Arg: {str(schedule_input)}")

    # Wake Up Token
    token = ics_parser.parse_wakeup_token(str(schedule_input))
    if token:
        try:
            json_data = await ics_parser.fetch_wakeup_schedule(token)

            if not json_data:
                await matcher.send(
                    "无法获取 WakeUp 课程表数据，请检查口令是否正确或已过期。"
                )
                return None
            ics_content = ics_parser.convert_wakeup_to_ics(json_data)
            if not ics_content:
                await matcher.send("课程表数据解析失败，无法生成 ICS 文件。")
                return None
            ics_path = data_manager.get_ics_file_path(user_id)
            with open(ics_path, "w", encoding="utf-8") as f:
                f.write(ics_content)

            if group_id:
                data_manager.add_user_to_group(user_id, group_id)

            ics_parser.clear_cache(ics_path)
            await matcher.send("通过 WakeUp 口令绑定课表成功！")
            return None
        except Exception as e:
            await matcher.finish(f"处理 WakeUp 口令失败: {e}")
            logger.error(e)

    # .ics 文件上传
    for seg in schedule_input:
        if seg.type == "file":
            try:
                file_id = seg.data.get("file_id")
                file_url = await get_file_url(bot, event, file_id)

                async with aiohttp.ClientSession() as session:
                    async with session.get(file_url) as resp:
                        ics_content = await resp.text()

                ics_path = data_manager.get_ics_file_path(user_id)
                with open(ics_path, "w", encoding="utf-8") as f:
                    f.write(ics_content)

                # 防止炒饭
                ics_parser.clear_cache(ics_path)
                parsed = ics_parser.parse_ics_file(ics_path)
                if parsed == []:
                    os.remove(ics_path)
                    raise ValueError("Not Valid ICS File.")

                if group_id:
                    data_manager.add_user_to_group(user_id, group_id)

                await matcher.send("课表文件绑定成功！")

            except Exception as e:
                raise e
                # await matcher.finish(f"下载或保存课表文件失败：{e}")
            return

    await matcher.finish(
        "未识别的口令或文件格式，请确认是否为 WakeUp 分享口令或 .ics 文件。"
    )


async def get_file_url(
    bot: Bot, event: Union[GroupMessageEvent, PrivateMessageEvent], file_id: str
) -> str:
    if isinstance(event, GroupMessageEvent):
        data = await bot.get_group_file_url(
            group=event.group_id, group_id=event.group_id, file_id=file_id
        )
        return data["url"]
    elif isinstance(event, PrivateMessageEvent):
        data = await bot.get_private_file_url(user_id=bot.self_id, file_id=file_id)
        return data["url"]


@unbind_schedule.handle()
async def handle_unbind_entry(event: Union[GroupMessageEvent, PrivateMessageEvent]):
    user_id = event.user_id

    ics_path = data_manager.get_ics_file_path(user_id)
    if os.path.exists(ics_path):
        os.remove(ics_path)
    ics_parser.clear_cache(str(ics_path))

    user_data = data_manager.load_user_data()

    for group_id in list(user_data.keys()):
        if user_id in user_data[group_id]:
            user_data[group_id].remove(user_id)

    data_manager.save_user_data(user_data)

    await unbind_schedule.finish(f"解绑成功啦！")
