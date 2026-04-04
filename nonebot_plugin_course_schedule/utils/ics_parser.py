# -*- coding: utf-8 -*-
"""
本模块负责处理 .ics 文件和 WakeUp 口令的解析、转换和数据获取。
"""
import json
import re
from datetime import datetime, timezone, timedelta, date, time as dt_time
from typing import Dict, List, Optional

import aiohttp
from icalendar import Calendar, Event
from dateutil.rrule import rrulestr

from nonebot import logger


class ICSParser:
    """ICS 和 WakeUp 数据解析器"""

    def __init__(self):
        self.course_cache: Dict[str, List[Dict]] = {}

    def _to_local_datetime(self, value, target_tz: timezone) -> datetime:
        """将 ICS 属性值统一转换为带时区的 datetime。"""
        if isinstance(value, date) and not isinstance(value, datetime):
            value = datetime.combine(value, dt_time.min)

        if not isinstance(value, datetime):
            raise ValueError(f"Unsupported datetime value type: {type(value)}")

        return (
            value.astimezone(target_tz)
            if value.tzinfo
            else value.replace(tzinfo=target_tz)
        )

    def _extract_datetime_values(self, prop_value, target_tz: timezone) -> List[datetime]:
        """从 RDATE/EXDATE 等 ICS 属性中提取 datetime 列表。"""
        if not prop_value:
            return []

        values = prop_value if isinstance(prop_value, list) else [prop_value]
        results: List[datetime] = []

        for value in values:
            if hasattr(value, "dts"):
                for dt_item in value.dts:
                    results.append(self._to_local_datetime(dt_item.dt, target_tz))
            elif hasattr(value, "dt"):
                results.append(self._to_local_datetime(value.dt, target_tz))
            else:
                results.append(self._to_local_datetime(value, target_tz))

        return results

    def parse_ics_file(self, file_path: str) -> List[Dict]:
        """解析 .ics 文件并返回课程列表，包括重复事件。使用缓存以提高性能。"""
        #if file_path in self.course_cache: # TODO: 这里的缓存有时候清理不掉，原因不明。此外性能瓶颈不在这里。
        #    return self.course_cache[file_path]

        courses = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                cal_content = f.read()
        except (FileNotFoundError, IOError) as e:
            logger.error(f"无法读取 ICS 文件 {file_path}: {e}")
            return []

        cal = Calendar.from_ical(cal_content)
        shanghai_tz = timezone(timedelta(hours=8))
        start_of_today_utc = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        # 通常而言，一个学期的长度不会超过 24 周，也不会有人闲得无聊查那么久
        history_limit_utc = start_of_today_utc - timedelta(days=180)
        future_limit_utc = start_of_today_utc + timedelta(days=180)

        for component in cal.walk():
            if component.name == "VEVENT":
                summary = component.get("summary")
                description = component.get("description")
                location = component.get("location")
                dtstart = component.get("dtstart").dt
                dtend_prop = component.get("dtend")
                duration_prop = component.get("duration")
                
                rrule_prop = component.get("rrule")
                rdate_prop = component.get("rdate")
                exdate_prop = component.get("exdate")
                exrule_prop = component.get("exrule")

                dtstart = self._to_local_datetime(dtstart, shanghai_tz)

                if dtend_prop:
                    dtend = self._to_local_datetime(dtend_prop.dt, shanghai_tz)
                elif duration_prop:
                    dtend = dtstart + duration_prop.dt
                else:
                    dtend = dtstart

                course_duration = dtend - dtstart

                has_recurrence = bool(rrule_prop or rdate_prop)

                if has_recurrence:
                    included_occurrences_utc = {
                        dtstart.astimezone(timezone.utc)
                    }

                    # 处理 RRULE
                    if rrule_prop:
                        if "UNTIL" in rrule_prop:
                            until_dt = rrule_prop["UNTIL"][0]
                            if isinstance(until_dt, date) and not isinstance(
                                until_dt, datetime
                            ):
                                until_dt = datetime.combine(until_dt, dt_time.max)
                            if until_dt.tzinfo is None:
                                until_dt = until_dt.replace(tzinfo=shanghai_tz)
                            rrule_prop["UNTIL"][0] = until_dt.astimezone(timezone.utc)

                        dtstart_utc = dtstart.astimezone(timezone.utc)
                        rrule = rrulestr(
                            rrule_prop.to_ical().decode(), dtstart=dtstart_utc
                        )

                        for occurrence_utc in rrule.between(
                            history_limit_utc, future_limit_utc, inc=True
                        ):
                            included_occurrences_utc.add(occurrence_utc)

                    # 处理 RDATE
                    for rdate_dt in self._extract_datetime_values(rdate_prop, shanghai_tz):
                        included_occurrences_utc.add(rdate_dt.astimezone(timezone.utc))

                    # 处理 EXDATE
                    excluded_occurrences_utc = set()
                    for exdate_dt in self._extract_datetime_values(exdate_prop, shanghai_tz):
                        excluded_occurrences_utc.add(exdate_dt.astimezone(timezone.utc))

                    # 处理 EXRULE，说实话很少见到
                    if exrule_prop:
                        exrule_values = (
                            exrule_prop if isinstance(exrule_prop, list) else [exrule_prop]
                        )
                        for exrule_value in exrule_values:
                            exrule = rrulestr(
                                exrule_value.to_ical().decode(),
                                dtstart=dtstart.astimezone(timezone.utc),
                            )
                            for excluded_utc in exrule.between(
                                history_limit_utc, future_limit_utc, inc=True
                            ):
                                excluded_occurrences_utc.add(excluded_utc)

                    for occurrence_utc in sorted(included_occurrences_utc):
                        if not (history_limit_utc <= occurrence_utc <= future_limit_utc):
                            continue
                        if occurrence_utc in excluded_occurrences_utc:
                            continue

                        occurrence_local = occurrence_utc.astimezone(shanghai_tz)
                        courses.append(
                            {
                                "summary": summary,
                                "description": description,
                                "location": location,
                                "start_time": occurrence_local,
                                "end_time": occurrence_local + course_duration,
                            }
                        )
                else:
                    courses.append(
                        {
                            "summary": summary,
                            "description": description,
                            "location": location,
                            "start_time": dtstart,
                            "end_time": dtend,
                        }
                    )
        self.course_cache[file_path] = courses
        return courses

    def clear_cache(self, file_path: str):
        """清除指定文件的缓存"""
        self.course_cache.pop(file_path, None)

    def parse_wakeup_token(self, text: str) -> Optional[str]:
        """从文本中解析 WakeUp 分享口令"""
        match = re.search(r"「([a-f0-9]{32})」", text)
        if match:
            return match.group(1)
        return None

    async def fetch_wakeup_schedule(self, token: str) -> Optional[List]:
        """通过 WakeUp API 获取课程表数据"""
        url = f"https://i.wakeup.fun/share_schedule/get?key={token}"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("status") == 1:
                            # Wakeup 的数据是多个 JSON 对象拼接成的字符串，需要分割
                            parts = data["data"].strip().split("\n")
                            json_parts = [json.loads(p) for p in parts]
                            return json_parts
                        else:
                            logger.error(
                                f"WakeUp API returned error: {data.get('message')}"
                            )
                            return None
                    else:
                        logger.error(
                            f"Failed to fetch WakeUp schedule, status code: {response.status}"
                        )
                        return None
            except Exception as e:
                logger.error(f"Error fetching WakeUp schedule: {e}")
                return None

    def convert_wakeup_to_ics(self, data: List) -> Optional[str]:
        """将 WakeUp JSON 数据转换为 ICS 格式"""
        try:
            # Wakeup 的数据是多个 JSON 对象拼接成的字符串，需要分割
            # data 已经是 fetch_wakeup_schedule 解析后的列表了
            time_table_info = data[1]  # 时间表
            schedule_settings = data[2]  # 课表设置
            course_definitions = data[3]  # 课程定义
            course_arrangements = data[4]  # 课程安排

            course_id_to_name = {c["id"]: c["courseName"] for c in course_definitions}

            start_date_str = schedule_settings.get("startDate", "2023-09-04")
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()

            cal = Calendar()
            cal.add("prodid", "-//WakeUp Schedule Converter//")
            cal.add("version", "2.0")

            for arrangement in course_arrangements:
                course_def_id = arrangement.get("id")
                course_name = course_id_to_name.get(course_def_id, "未知课程")

                start_week = arrangement.get("startWeek")
                end_week = arrangement.get("endWeek")
                day_of_week = arrangement.get("day")
                start_node = arrangement.get("startNode")
                step = arrangement.get("step", 1)
                class_type = arrangement.get("type", 0)                

                teacher = arrangement.get("teacher", "")
                room = arrangement.get("room", "")

                start_time_str = "00:00"
                end_time_str = "00:00"
                for time_slot in time_table_info:
                    if time_slot.get("node") == start_node:
                        start_time_str = time_slot.get("startTime", "00:00")
                        end_node = start_node + step - 1
                        for end_slot in time_table_info:
                            if end_slot.get("node") == end_node:
                                end_time_str = end_slot.get("endTime", "00:00")
                                break
                        break

                start_time = dt_time.fromisoformat(start_time_str)
                end_time = dt_time.fromisoformat(end_time_str)

                weekday_map = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]
                byday = weekday_map[day_of_week - 1]

                first_day_offset = day_of_week - start_date.weekday() - 1
                if first_day_offset < 0:
                    first_day_offset += 7
                first_day = start_date + timedelta(
                    weeks=start_week - 1, days=first_day_offset
                )

                last_day_offset = day_of_week - start_date.weekday() - 1
                if last_day_offset < 0:
                    last_day_offset += 7
                last_day = start_date + timedelta(
                    weeks=end_week - 1, days=last_day_offset
                )
                until_datetime = datetime.combine(last_day, end_time)
                
                interval = 1 if class_type == 0 else 2

                event = Event()
                event.add("summary", course_name)
                event.add("dtstart", datetime.combine(first_day, start_time))
                event.add("dtend", datetime.combine(first_day, end_time))
                event.add(
                    "rrule", {"freq": "weekly", "byday": byday, "until": until_datetime, "interval": interval}
                )
                event.add("location", room)
                event.add("description", f"{teacher}")

                cal.add_component(event)

            return cal.to_ical().decode("utf-8")

        except Exception as e:
            logger.error(f"转换 WakeUp 数据到 ICS 失败: {e}")
            return None


ics_parser = ICSParser()
