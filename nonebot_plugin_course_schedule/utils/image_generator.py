# -*- coding: utf-8 -*-
"""
本模块负责生成插件所需的各种图片，如图形化课程表和排行榜。
"""
import asyncio
import tempfile
from datetime import datetime, timezone, timedelta, date
from io import BytesIO
from typing import Dict, List

import aiohttp
from PIL import Image, ImageDraw, ImageFont

from nonebot import logger

from . import constants as c
from ..config import config


class ImageGenerator:
    """图片生成器"""

    def __init__(self):
        self.font_path = config.course_font_path
        self.font_main = self._load_font(32)
        self.font_sub = self._load_font(24)
        self.font_title = self._load_font(48)
        self.font_header = self._load_font(26)
        self.font_text = self._load_font(28)
        self.font_rank = self._load_font(36)
        self.font_subtitle = self._load_font(24)  # 添加缺失的 font_subtitle 属性
        self.user_font_main = self._load_font(28)
        self.user_font_sub = self._load_font(22)
        self.user_font_title = self._load_font(40)

    def _load_font(self, size: int) -> ImageFont.FreeTypeFont:
        """加载指定大小的字体"""
        try:
            return (
                ImageFont.truetype(self.font_path, size, encoding="utf-8")
                if self.font_path
                else ImageFont.load_default()
            )
        except IOError:
            logger.warning(f"无法加载字体文件: {self.font_path}，将使用默认字体。")
            return ImageFont.load_default()

    def _sanitize_for_pil(self, text: str, font: ImageFont.FreeTypeFont) -> str:
        """移除字体不支持的字符"""
        sanitized_text = ""
        for char in text:
            try:
                font.getbbox(char)
                sanitized_text += char
            except (TypeError, ValueError):
                sanitized_text += " "
        return sanitized_text

    def _draw_rounded_rectangle(self, draw, xy, radius, fill):
        """手动绘制圆角矩形"""
        x1, y1, x2, y2 = xy
        draw.rectangle([x1, y1 + radius, x2, y2 - radius], fill=fill)
        draw.rectangle([x1 + radius, y1, x2 - radius, y2], fill=fill)
        draw.pieslice([x1, y1, x1 + radius * 2, y1 + radius * 2], 180, 270, fill=fill)
        draw.pieslice([x2 - radius * 2, y1, x2, y1 + radius * 2], 270, 360, fill=fill)
        draw.pieslice([x1, y2 - radius * 2, x1 + radius * 2, y2], 90, 180, fill=fill)
        draw.pieslice([x2 - radius * 2, y2 - radius * 2, x2, y2], 0, 90, fill=fill)

    async def _fetch_avatars(self, user_ids: List[str]) -> List[bytes]:
        """异步获取多个用户的头像"""

        async def fetch_avatar(session, user_id):
            avatar_url = (
                f"https://q1.qlogo.cn/g?b=qq&nk={user_id}&s=100"
            )
            try:
                async with session.get(avatar_url) as response:
                    if response.status == 200:
                        return await response.read()
            except Exception as e:
                logger.error(f"Failed to download avatar for {user_id}: {e}")
            return None

        async with aiohttp.ClientSession() as session:
            tasks = [fetch_avatar(session, user_id) for user_id in user_ids]
            return await asyncio.gather(*tasks)
        
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
    
    async def generate_schedule_image(self, courses: List[Dict]) -> str:
        """生成课程表图片并返回临时文件路径"""
        height = c.GS_PADDING * 2 + 120 + len(courses) * c.GS_ROW_HEIGHT
        image = Image.new("RGB", (c.GS_WIDTH, height), c.GS_BG_COLOR)
        draw = ImageDraw.Draw(image)

        draw.rectangle(
            [c.GS_PADDING, c.GS_PADDING, c.GS_PADDING + 20, c.GS_PADDING + 60],
            fill="#26A69A",
        )
        draw.text(
            (c.GS_PADDING + 40, c.GS_PADDING),
            "“群友在上什么课?”",
            font=self.font_title,
            fill=c.GS_TITLE_COLOR,
        )
        draw.rectangle(
            [
                c.GS_PADDING + 40,
                c.GS_PADDING + 70,
                c.GS_PADDING + 40 + 300,
                c.GS_PADDING + 75,
            ],
            fill="#A7FFEB",
        )

        user_ids = [course.get("user_id", "N/A") for course in courses]
        avatar_datas = await self._fetch_avatars(user_ids)

        y_offset = c.GS_PADDING + 120
        now = datetime.now(timezone(timedelta(hours=8)))

        for i, course in enumerate(courses):
            user_id = course.get("user_id", "N/A")
            nickname = course.get("nickname", user_id)
            summary = course.get("summary", "无课程信息")
            start_time = course.get("start_time")
            end_time = course.get("end_time")
            location = course.get("location", "未知地点")

            avatar_data = avatar_datas[i]
            if avatar_data:
                avatar = Image.open(BytesIO(avatar_data)).convert("RGBA")
                avatar = avatar.resize((c.GS_AVATAR_SIZE, c.GS_AVATAR_SIZE))
                mask = Image.new("L", (c.GS_AVATAR_SIZE, c.GS_AVATAR_SIZE), 0)
                mask_draw = ImageDraw.Draw(mask)
                mask_draw.ellipse((0, 0, c.GS_AVATAR_SIZE, c.GS_AVATAR_SIZE), fill=255)
                image.paste(
                    avatar,
                    (
                        c.GS_PADDING,
                        y_offset + (c.GS_ROW_HEIGHT - c.GS_AVATAR_SIZE) // 2,
                    ),
                    mask,
                )

            arrow_x = c.GS_PADDING + c.GS_AVATAR_SIZE + 20
            arrow_y = y_offset + c.GS_ROW_HEIGHT // 2
            arrow_points = [
                (arrow_x, arrow_y - 20),
                (arrow_x + 30, arrow_y),
                (arrow_x, arrow_y + 20),
            ]
            draw.polygon(arrow_points, fill="#BDBDBD")

            status_text = ""
            detail_text = ""

            if start_time and end_time:
                if start_time <= now < end_time:
                    status_text = "进行中"
                    remaining_minutes = (end_time - now).total_seconds() // 60
                    if remaining_minutes > 60:
                        detail_text = f"剩余 {int(remaining_minutes // 60)} 小时 {int(remaining_minutes % 60)} 分钟"
                    else:
                        detail_text = f"剩余 {int(remaining_minutes)} 分钟"
                elif now < start_time:
                    status_text = "下一节"
                    delta_minutes = (start_time - now).total_seconds() // 60
                    if delta_minutes > 60:
                        detail_text = f"{int(delta_minutes // 60)} 小时 {int(delta_minutes % 60)} 分钟后"
                    else:
                        detail_text = f"{int(delta_minutes)} 分钟后"
                else:
                    status_text = "已结束"
                    detail_text = "今日所有课程已结束"
            else:
                status_text = "已结束"
                detail_text = "今日所有课程已结束"

            text_x = arrow_x + 50
            nickname = self._sanitize_for_pil(nickname, self.font_main)
            draw.text(
                (text_x, y_offset + 15),
                str(nickname),
                font=self.font_main,
                fill=c.GS_FONT_COLOR,
            )

            status_bg, status_fg = c.GS_STATUS_COLORS.get(
                status_text, ("#000000", "#FFFFFF")
            )
            draw.rectangle(
                [text_x, y_offset + 60, text_x + 100, y_offset + 95], fill=status_bg
            )
            draw.text(
                (text_x + 10, y_offset + 65),
                status_text,
                font=self.font_sub,
                fill=status_fg,
            )

            draw.text(
                (text_x + 120, y_offset + 65),
                f"{summary} @ {location}",
                font=self.font_sub,
                fill=c.GS_FONT_COLOR,
            )
            if start_time and end_time:
                time_str = (
                    f"{start_time.strftime('%H:%M')}-{end_time.strftime('%H:%M')}"
                )
                draw.text(
                    (text_x + 120, y_offset + 95),
                    f"{time_str} ({detail_text})",
                    font=self.font_sub,
                    fill=c.GS_SUBTITLE_COLOR,
                )
            else:
                draw.text(
                    (text_x + 120, y_offset + 95),
                    detail_text,
                    font=self.font_sub,
                    fill=c.GS_SUBTITLE_COLOR,
                )

            y_offset += c.GS_ROW_HEIGHT

        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        temp_path = temp_file.name
        image.save(temp_path, format="PNG")
        temp_file.close()

        return temp_path

    async def generate_user_schedule_image(
        self, courses: List[Dict], nickname: str, date: datetime = None 
    ) -> str:
        """为单个用户生成今日课程表图片"""
        day: str = date.strftime("%m-%d ") if date else "今日"
        weekday: int = date.weekday() if date else datetime.now(timezone(timedelta(hours=8))).weekday()
        weeklist = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

        # 超长 title 换行预算
        sanitized_nickname = self._sanitize_for_pil(nickname, self.user_font_title)
        title = f"{sanitized_nickname}的"
        wrapped_title = self._wrap_text(title, c.US_MAX_UNIT)
        wrapped_title.append(f"{day}课程（{weeklist[weekday]}）")
        nickname_lines = len(wrapped_title)
        title_height = nickname_lines * 40 + nickname_lines * c.US_SPACING
        
        # 超长 course 换行预算
        course_heights = []
        for course in courses:
            summary = course.get("summary", "无课程信息")
            location = course.get("location", "未知地点")
            teacher = course.get("description", "未知教师")
            
            # 如果整体长度不长则单行显示
            test_line = self._wrap_text(f"{summary} @ {location} @ {teacher}", c.US_ROW_MAX_UNIT)
            if len(test_line) == 1:
                row_height = c.US_ROW_HEIGHT
                course_heights.append(row_height)
                continue
            
            # 否则多行显示
            wrapped_lines = self._wrap_text(summary, c.US_ROW_MAX_UNIT)
            wrapped_lines += self._wrap_text(location, c.US_ROW_MAX_UNIT)
            wrapped_lines += self._wrap_text(teacher, c.US_ROW_MAX_UNIT)
            row_height = c.US_ROW_HEIGHT + (len(wrapped_lines) - 1) * (22 + c.US_ROW_SPACING)
            course_heights.append(row_height)
        
        height = c.US_PADDING * 2 + title_height + sum(course_heights) + 35
        image = Image.new("RGB", (c.US_WIDTH, height), c.US_BG_COLOR)
        draw = ImageDraw.Draw(image)
        
        y = c.US_PADDING
        for line in wrapped_title:
            draw.text(
                (c.US_PADDING, y),
                line,
                font=self.user_font_title,
                fill=c.US_TITLE_COLOR,
            )
            y += (40 + c.US_SPACING)


        y_offset = c.US_PADDING * 2 + title_height

        for course in courses:
            summary = course.get("summary", "无课程信息")
            start_time = course.get("start_time")
            end_time = course.get("end_time")
            location = course.get("location", "未知地点")
            teacher = course.get("description", "未知教师")

            test_line = self._wrap_text(f"{summary} @ {location} @ {teacher}", c.US_ROW_MAX_UNIT)
            if len(test_line) == 1:
                wrapped_lines = test_line
                row_height = c.US_ROW_HEIGHT
            else:
                wrapped_lines = self._wrap_text(summary, c.US_ROW_MAX_UNIT)
                wrapped_lines += self._wrap_text(location, c.US_ROW_MAX_UNIT)
                wrapped_lines += self._wrap_text(teacher, c.US_ROW_MAX_UNIT)
                row_height = c.US_ROW_HEIGHT + (len(wrapped_lines) - 1) * (22 + c.US_ROW_SPACING)

            self._draw_rounded_rectangle(
                draw,
                [
                    c.US_PADDING,
                    y_offset,
                    c.US_WIDTH - c.US_PADDING,
                    y_offset + row_height - 10,
                ],
                10,
                fill=c.US_COURSE_BG_COLOR,
            )

            time_str = f"{start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}"
            draw.text(
                (c.US_PADDING + 20, y_offset + 15),
                time_str,
                font=self.user_font_main,
                fill=c.US_TITLE_COLOR,
            )

            y = y_offset + 55
            for line in wrapped_lines:
                draw.text(
                    (c.US_PADDING + 20, y),
                    line,
                    font=self.user_font_sub,
                    fill=c.US_FONT_COLOR,
                )
                y += 22 + c.US_ROW_SPACING

            y_offset += row_height

        footer_text = f"生成时间: {datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S')}"
        draw.text(
            (c.US_PADDING, height - c.US_PADDING),
            footer_text,
            font=self.user_font_sub,
            fill=c.US_SUBTITLE_COLOR,
        )

        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        temp_path = temp_file.name
        image.save(temp_path, format="PNG")
        temp_file.close()

        return temp_path

    async def generate_ranking_image(
        self, ranking_data: List[Dict], start_date: date, end_date: date
    ) -> str:
        """生成排行榜图片"""
        height = (
            c.RANKING_HEADER_HEIGHT
            + len(ranking_data) * c.RANKING_ROW_HEIGHT
            + c.RANKING_PADDING
        )
        image = Image.new("RGB", (c.RANKING_WIDTH, height), c.RANKING_BG_COLOR)
        draw = ImageDraw.Draw(image)

        draw.text(
            (c.RANKING_PADDING, c.RANKING_PADDING),
            "本周上课排行榜",
            font=self.font_title,
            fill=c.RANKING_TITLE_COLOR,
        )
        date_range_str = (
            f"{start_date.strftime('%Y/%m/%d')} - {end_date.strftime('%Y/%m/%d')}"
        )
        draw.text(
            (c.RANKING_PADDING, c.RANKING_PADDING + 70),
            date_range_str,
            font=self.font_subtitle,
            fill=c.RANKING_SUBTITLE_COLOR,
        )

        user_ids = [data["user_id"] for data in ranking_data]
        avatar_datas = await self._fetch_avatars(user_ids)

        y_offset = c.RANKING_HEADER_HEIGHT
        for i, data in enumerate(ranking_data):
            rank = i + 1

            if i % 2 == 1:
                draw.rectangle(
                    [
                        c.RANKING_PADDING,
                        y_offset,
                        c.RANKING_WIDTH - c.RANKING_PADDING,
                        y_offset + c.RANKING_ROW_HEIGHT,
                    ],
                    fill=c.RANKING_ROW_BG_COLOR,
                )

            rank_color = c.RANKING_COLORS.get(rank, c.RANKING_FONT_COLOR)
            rank_text = str(rank)
            try:
                rank_bbox = self.font_rank.getbbox(rank_text)
                rank_width = rank_bbox - rank_bbox
                rank_height = rank_bbox - rank_bbox
            except (TypeError, ValueError):
                rank_width = 10
                rank_height = 10
            draw.text(
                (
                    c.RANKING_PADDING + 40 - rank_width / 2,
                    y_offset + (c.RANKING_ROW_HEIGHT - rank_height) / 2,
                ),
                rank_text,
                font=self.font_rank,
                fill=rank_color,
            )

            avatar_data = avatar_datas[i]
            if avatar_data:
                avatar = Image.open(BytesIO(avatar_data)).convert("RGBA")
                avatar = avatar.resize((c.RANKING_AVATAR_SIZE, c.RANKING_AVATAR_SIZE))
                mask = Image.new("L", (c.RANKING_AVATAR_SIZE, c.RANKING_AVATAR_SIZE), 0)
                mask_draw = ImageDraw.Draw(mask)
                mask_draw.ellipse(
                    (0, 0, c.RANKING_AVATAR_SIZE, c.RANKING_AVATAR_SIZE), fill=255
                )
                image.paste(
                    avatar,
                    (
                        c.RANKING_PADDING + 100,
                        y_offset + (c.RANKING_ROW_HEIGHT - c.RANKING_AVATAR_SIZE) // 2,
                    ),
                    mask,
                )

            nickname = self._sanitize_for_pil(data["nickname"], self.font_text)
            draw.text(
                (c.RANKING_PADDING + 210, y_offset + (c.RANKING_ROW_HEIGHT - 30) / 2),
                nickname,
                font=self.font_text,
                fill=c.RANKING_FONT_COLOR,
            )

            total_seconds = data["total_duration"].total_seconds()
            hours = int(total_seconds // 3600)
            minutes = int((total_seconds % 3600) // 60)
            duration_str = f"{hours}h {minutes}m"
            count_str = f"{data['course_count']} 节"

            try:
                duration_bbox = self.font_text.getbbox(duration_str)
                duration_width = duration_bbox - duration_bbox
            except (TypeError, ValueError):
                duration_width = 100
            draw.text(
                (
                    c.RANKING_WIDTH - c.RANKING_PADDING - duration_width - 20,
                    y_offset + (c.RANKING_ROW_HEIGHT - 30) / 2 - 15,
                ),
                duration_str,
                font=self.font_text,
                fill=c.RANKING_FONT_COLOR,
            )

            try:
                count_bbox = self.font_subtitle.getbbox(count_str)
                count_width = count_bbox - count_bbox
            except (TypeError, ValueError):
                count_width = 80
            draw.text(
                (
                    c.RANKING_WIDTH - c.RANKING_PADDING - count_width - 20,
                    y_offset + (c.RANKING_ROW_HEIGHT - 30) / 2 + 25,
                ),
                count_str,
                font=self.font_subtitle,
                fill=c.RANKING_SUBTITLE_COLOR,
            )

            y_offset += c.RANKING_ROW_HEIGHT

        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        temp_path = temp_file.name
        image.save(temp_path, format="PNG")
        temp_file.close()
        return temp_path


image_generator = ImageGenerator()
