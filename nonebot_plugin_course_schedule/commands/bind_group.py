import os

from nonebot import on_command
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message
from ..utils.data_manager import data_manager


bind_group = on_command(
    "bind_group", aliases={"绑定群聊课表", "加入群聊课表"}, force_whitespace=True, priority=5, block=True
)
unbind_group = on_command(
    "unbind_group", aliases={"解绑群聊课表", "退出群聊课表"}, force_whitespace=True, priority=5, block=True
)


@bind_group.handle()
async def bind_group_handle(event: GroupMessageEvent):
    group_id = event.group_id
    user_id = event.user_id

    ics_path = data_manager.get_ics_file_path(user_id)
    if not os.path.exists(ics_path):
        await bind_group.finish(f"请先绑定课表！")

    data_manager.add_user_to_group(user_id, group_id)
    await bind_group.finish(f"绑定群聊成功！")


@unbind_group.handle()
async def unbind_group_handle(event: GroupMessageEvent):
    group_id = event.group_id
    user_id = event.user_id

    data_manager.remove_user_from_group(user_id, group_id)
    await unbind_group.finish(f"解绑群聊成功！")
