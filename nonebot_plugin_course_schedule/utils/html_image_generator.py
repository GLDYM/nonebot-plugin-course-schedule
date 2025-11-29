# -*- coding: utf-8 -*-
"""
本模块负责使用HTML模板生成插件所需的图片，如图形化课程表和排行榜。
"""
import tempfile
import os
from datetime import datetime, timezone, timedelta, date
from typing import Dict, List
from pathlib import Path

from nonebot import logger, require
from jinja2 import Environment, FileSystemLoader

from ..config import config

# 设置fontconfig配置文件路径
fontconfig_path = Path(__file__).parent.parent / "resources" / "fonts.conf"
os.environ["FONTCONFIG_FILE"] = str(fontconfig_path)

# 导入HTML渲染插件
require("nonebot_plugin_htmlkit")
from nonebot_plugin_htmlkit import template_to_pic


class HTMLImageGenerator:
    """HTML图片生成器"""

    def __init__(self):
        # 设置模板环境
        template_path = Path(__file__).parent.parent / "templates"
        self.env = Environment(loader=FileSystemLoader(template_path))
        self.template_path = str(template_path)
        
        # 加载字体配置
        self.font_path = config.course_font_path

    async def generate_schedule_image(self, courses: List[Dict]) -> str:
        """生成群课程表图片并返回图片文件路径"""
        try:
            # 格式化课程数据
            formatted_courses = []
            now = datetime.now(timezone(timedelta(hours=8)))
            
            for course in courses:
                # 确定课程状态和状态文本
                time_diff = ""
                if course.get("start_time") and course.get("end_time"):
                    if course["start_time"] <= now < course["end_time"]:
                        status = "ongoing"
                        status_text = "进行中"
                        # 计算剩余时间
                        remaining = course["end_time"] - now
                        hours = remaining.seconds // 3600
                        minutes = (remaining.seconds % 3600) // 60
                        if hours > 0:
                            time_diff = f"(剩余 {hours} 小时 {minutes} 分钟)"
                        else:
                            time_diff = f"(剩余 {minutes} 分钟)"
                    elif now < course["start_time"]:
                        status = "next"
                        status_text = "下一节"
                        # 计算距离开始时间
                        until_start = course["start_time"] - now
                        hours = until_start.seconds // 3600
                        minutes = (until_start.seconds % 3600) // 60
                        if hours > 0:
                            time_diff = f"({hours} 小时 {minutes} 分钟后)"
                        else:
                            time_diff = f"({minutes} 分钟后)"
                else:
                    status = "ended"
                    status_text = "已结束"
                
                # 格式化时间信息
                if course.get("start_time") and course.get("end_time"):
                    time_str = f"{course['start_time'].strftime('%H:%M')} - {course['end_time'].strftime('%H:%M')}"
                elif status == "ended":
                    time_str = "今日所有课程已结束"
                
                # 格式化课程信息
                if course.get("summary") != "今日无课":
                    course_info = course.get("summary", "无课程信息")
                    if course.get("location"):
                        course_info += f" @ {course['location']}"
                else:
                    course_info = "今日无课"
                
                # 构建avatar_url
                avatar_url = f"https://q1.qlogo.cn/g?b=qq&nk={course.get('user_id', '')}&s=640"
                
                formatted_courses.append({
                    "avatar_url": avatar_url,
                    "nickname": course.get("nickname", "未知用户"),
                    "status": status,
                    "status_text": status_text,
                    "course_info": course_info,
                    "time_info": time_str,
                    "time_diff": time_diff
                })
            
            # 准备模板数据
            template_data = {
                "courses": formatted_courses
            }
            
            # 渲染模板
            img_data = await template_to_pic(
                template_path=self.template_path,
                template_name="group_schedule.html",
                templates=template_data,
                max_width=1200,
                device_height=800,
            )
            
            # 将图片数据保存到临时文件并返回文件路径
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
            temp_path = temp_file.name
            temp_file.write(img_data)
            temp_file.close()
            
            return temp_path
        except Exception as e:
            logger.error(f"生成群课程表图片失败: {e}")
            raise

    def _estimate_char_units(self, text: str) -> int:
        """估计字符宽度"""
        count = 0
        for ch in text:
            if ch in " @" or ch.isascii():
                count += 1
            else:
                count += 2
        return count

    def _wrap_text(self, text: str, max_units: int) -> List[str]:
        """将文本按最大宽度进行切分"""
        lines = []
        current_line = ""
        current_units = 0

        for ch in text:
            unit = 1 if ch in " @" or ch.isascii() else 2
            if current_units + unit > max_units:
                lines.append(current_line)
                current_line = ch
                current_units = unit
            else:
                current_line += ch
                current_units += unit

        if current_line:
            lines.append(current_line)

        return lines

    async def generate_user_schedule_image(
        self, courses: List[Dict], nickname: str, date: datetime = None
    ) -> str:
        """为单个用户生成课程表图片并返回图片文件路径"""
        try:
            # 准备日期信息
            day: str = date.strftime("%m-%d ") if date else "今日"
            weekday: int = date.weekday() if date else datetime.now(timezone(timedelta(hours=8))).weekday()
            weeklist = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
            
            # 准备模板数据
            title_lines = [f"{nickname}的", f"{day}课程（{weeklist[weekday]}）"]
            
            # 格式化课程数据
            formatted_courses = []
            for course in courses:
                start_time = course.get("start_time")
                end_time = course.get("end_time")
                time_str = f"{start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}" if start_time and end_time else "时间未知"
                
                # 格式化课程详情
                summary = course.get("summary", "无课程信息")
                location = course.get("location", "未知地点")
                teacher = course.get("description", "未知教师")
                
                # 实现与PIL渲染器一致的换行逻辑
                test_line = f"{summary} @ {location} @ {teacher}"
                test_wrapped = self._wrap_text(test_line, 66)  # US_ROW_MAX_UNIT = 66
                
                if len(test_wrapped) == 1:
                    # 如果整体长度不长则单行显示
                    detail_lines = test_wrapped
                else:
                    # 否则多行显示
                    detail_lines = self._wrap_text(summary, 66)
                    detail_lines += self._wrap_text(location, 66)
                    detail_lines += self._wrap_text(teacher, 66)
                
                formatted_courses.append({
                    "time_str": time_str,
                    "detail_lines": detail_lines
                })
            
            # 生成时间
            generate_time = datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S')
            
            # 准备模板数据
            template_data = {
                "title_lines": title_lines,
                "courses": formatted_courses,
                "generate_time": generate_time
            }
            
            # 渲染模板
            img_data = await template_to_pic(
                template_path=self.template_path,
                template_name="user_schedule.html",
                templates=template_data,
                max_width=1200,
                device_height=600,
            )
            
            # 将图片数据保存到临时文件并返回文件路径
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
            temp_path = temp_file.name
            temp_file.write(img_data)
            temp_file.close()
            
            return temp_path
        except Exception as e:
            logger.error(f"生成用户课程表图片失败: {e}")
            raise

    async def generate_ranking_image(
        self, ranking_data: List[Dict], start_date: date, end_date: date
    ) -> str:
        """生成排行榜图片并返回图片文件路径"""
        try:
            # 准备日期范围字符串
            date_range = f"{start_date.strftime('%Y/%m/%d')} - {end_date.strftime('%Y/%m/%d')}"
            
            # 格式化排名数据
            formatted_ranking_data = []
            for i, data in enumerate(ranking_data):
                rank = i + 1
                
                # 确定排名样式类
                rank_class = "other"
                if rank == 1:
                    rank_class = "first"
                elif rank == 2:
                    rank_class = "second"
                elif rank == 3:
                    rank_class = "third"
                
                # 格式化时长
                total_seconds = data["total_duration"].total_seconds()
                hours = int(total_seconds // 3600)
                minutes = int((total_seconds % 3600) // 60)
                duration_str = f"{hours}h {minutes}m"
                
                # 格式化课程数量
                count_str = f"{data['course_count']} 节"
                
                # 头像URL
                avatar_url = f"https://q1.qlogo.cn/g?b=qq&nk={data['user_id']}&s=100"
                
                formatted_ranking_data.append({
                    "row_index": i,
                    "rank": str(rank),
                    "rank_class": rank_class,
                    "avatar_url": avatar_url,
                    "nickname": data["nickname"],
                    "duration_str": duration_str,
                    "count_str": count_str
                })
            
            # 准备模板数据
            template_data = {
                "date_range": date_range,
                "ranking_data": formatted_ranking_data
            }
            
            # 渲染模板
            img_data = await template_to_pic(
                template_path=self.template_path,
                template_name="ranking.html",
                templates=template_data,
                max_width=1200,
                device_height=800,
            )
            
            # 将图片数据保存到临时文件并返回文件路径
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
            temp_path = temp_file.name
            temp_file.write(img_data)
            temp_file.close()
            
            return temp_path
        except Exception as e:
            logger.error(f"生成排行榜图片失败: {e}")
            raise


image_generator = HTMLImageGenerator()