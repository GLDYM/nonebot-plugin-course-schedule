<div align="center">
    <a href="https://v2.nonebot.dev/store">
    <img src="https://raw.githubusercontent.com/fllesser/nonebot-plugin-template/refs/heads/resource/.docs/NoneBotPlugin.svg" width="310" alt="logo"></a>

# 电子课程表

_✨ 从 https://github.com/advent259141/astrbot_plugin_CourseSchedule 移植 ✨_

<a href="./LICENSE">
    <img src="https://img.shields.io/github/license/GLDYM/nonebot-plugin-course-schedule.svg" alt="license">
</a>
<a href="https://pypi.python.org/pypi/nonebot-plugin-course-schedule">
    <img src="https://img.shields.io/pypi/v/nonebot-plugin-course-schedule.svg" alt="pypi">
</a>
<img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="python">

</div>

这是一个课程表插件，帮助群组成员方便地管理和查询自己以及群友的课程安排。

## ✨ 功能特性

- 与原本插件相同的部分不再赘述
- 将课程表与群聊分离，只和用户有关
- 命令支持偏移参数或指定日期
- 课表图片可以自适应显示，防止超长课程名
- 现在可以显示课程地点
- 对于相同时间相同名称的课程可以去重
- 修正 WakeUp 课程表导入单双周错误的问题

## 💿 安装

<details open>
<summary>使用 nb-cli 安装</summary>
在 nonebot2 项目的根目录下打开命令行, 输入以下指令即可安装

    nb plugin install nonebot-plugin-course-schedule

</details>

<details>
<summary>使用包管理器安装</summary>
在 nonebot2 项目的插件目录下, 打开命令行, 根据你使用的包管理器, 输入相应的安装命令

<details>
<summary>pip</summary>

    pip install nonebot-plugin-course-schedule
</details>
<details>
<summary>pdm</summary>

    pdm add nonebot-plugin-course-schedule
</details>
<details>
<summary>poetry</summary>

    poetry add nonebot-plugin-course-schedule
</details>
<details>
<summary>conda</summary>

    conda install nonebot-plugin-course-schedule
</details>

打开 nonebot2 项目根目录下的 `pyproject.toml` 文件, 在 `[tool.nonebot]` 部分追加写入

    plugins = ["nonebot_plugin_course_schedule"]

</details>

## ⚙️ 配置

在 nonebot2 项目的`.env`文件中添加下表中的配置

| 配置项    | 必填 | 说明                                                           |
|:---------:|:----:|:--------------------------------------------------------------:|
| data_path | 否   | 课表文件与绑定群聊的存储路径，默认 `data/course_schedule`      |
| fort_path | 否   | 字体路径，默认插件目录下 `resource/MapleMono-NF-CN-Medium.ttf` |

## 📝 命令列表

| 命令                    | 功能描述                                                                           |
| :---------------------- | :--------------------------------------------------------------------------------- |
| `绑定课表`              | 在群聊中发送此命令，然后根据提示发送你的 `.ics` 文件或 WakeUp 分享口令来绑定课表。 |
| `绑定群聊`              | 让自己显示在本群的课表中。                                                         |
| `课表 \<offset\|date>`  | 显示你自己今天（或查询日期）接下来要上的课程。                                     |
| `群课表 <offset\|date>` | 显示群里所有成员当前正在上或下一节要上的课程（或查询日期将要上的课）。             |
| `上课排行`              | 显示本周群友上课时长和节数的排行榜。                                               |

## ❓ 如何获取 .ics 文件或 WakeUp 口令？

*   **.ics 文件**：将你的课表导入课表软件（如 **Wakeup课程表** 或类似应用），然后从软件的设置中选择“导出”，并导出为日历文件（通常文件后缀为 `.ics`），即可获得所需文件。
*   **WakeUp 口令**：在 **WakeUp课程表** 应用中，选择“分享课表”，然后选择“分享给好友”，复制生成的口令即可。

## 🤝 贡献

欢迎提交 Pull Request 或 Issue 来改进这个插件！

## 特别感谢

- [Maple Mono](https://github.com/subframe7536/maple-font)