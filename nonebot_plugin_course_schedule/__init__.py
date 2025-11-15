from nonebot.plugin import PluginMetadata
from .config import Config, config

__plugin_meta__ = PluginMetadata(
    name="电子课程表",
    description="绑定课表、查看课程、查看群友的课程，以及……上课排行",
    usage="""▶ 课表帮助：打印本信息
▶ 绑定课表：发送你的 .ics 文件或 WakeUp 分享口令来绑定课表
  ▷ 可以重新绑定，可以通过旦夕导出
▶ 解绑课表：删掉课表
  ▷ 解绑会将你解绑所有群聊
▶ 绑定群聊：让自己显示在本群的课表中
  ▷ 绑定课表时会自动绑定群聊
▶ 解绑群聊：让自己从本群的课表中消失
▶ 查看课表 <offset|date>：显示你今天要上的课程
▶ 群课表 <offset|date>：显示群友正在上的课和将要上的课
▶ 上课排行：看看苦逼群友本周上了多少课
""",
    type="application",
    homepage="https://github.com/GLDYM/nonebot-plugin-course-schedule",
    config=Config,
    supported_adapters={"~onebot.v11"},
    extra={"author": "Polaris_Light", "version": "1.0.3", "priority": 5},
)

from nonebot import require

require("nonebot_plugin_apscheduler")
require("nonebot_plugin_localstore")

from typing import Union
from nonebot import on_command
from nonebot.adapters.onebot.v11 import (
    GroupMessageEvent,
    PrivateMessageEvent,
)

from .commands import (
    bind_schedule,
    bind_group,
    show_today,
    group_schedule,
    weekly_ranking,
)

help_cmd = on_command(
    "course_help",
    aliases={"课表帮助", "课程帮助"},
    force_whitespace=True,
    priority=5,
    block=True,
)


@help_cmd.handle()
async def _(event: Union[GroupMessageEvent, PrivateMessageEvent]):
    await help_cmd.finish(__plugin_meta__.usage)
