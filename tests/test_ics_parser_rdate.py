from pathlib import Path
import importlib.util
import unittest
from datetime import datetime, timedelta


def _load_ics_parser_class():
    project_root = Path(__file__).resolve().parents[1]
    module_path = project_root / "nonebot_plugin_course_schedule" / "utils" / "ics_parser.py"
    spec = importlib.util.spec_from_file_location("ics_parser_test_module", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module.ICSParser


ICSParser = _load_ics_parser_class()


class TestIcsParserRdate(unittest.TestCase):
    def test_parse_user_sample_keeps_recent_past_occurrences(self):
        """验证样例不会因窗口过滤而丢失。"""
        ics_text = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:isdu-2-20260320T162721Z@isdu.app
DTSTAMP:20260320T162721Z
DTSTART;TZID=Asia/Shanghai:20260302T080000
DTEND;TZID=Asia/Shanghai:20260302T095000
SUMMARY:离散数学(双语)
LOCATION:软件园5区107d
DESCRIPTION:教师: ***\\n学分: 4.0\\n上课周: 1,2,3,4
RDATE;TZID=Asia/Shanghai;VALUE=DATE-TIME:20260309T080000,20260316T080000,20260323T080000
END:VEVENT
END:VCALENDAR
"""

        file_path = Path(__file__).parent / "_tmp_user_sample_rdate.ics"
        file_path.write_text(ics_text, encoding="utf-8")

        parser = ICSParser()
        courses = parser.parse_ics_file(str(file_path))
        courses = sorted(courses, key=lambda x: x["start_time"])
        file_path.unlink(missing_ok=True)

        self.assertEqual(len(courses), 4)

    def test_parse_rdate_event_expands_all_occurrences(self):
        """验证 RDATE 列出的多次上课时间可被完整展开。"""
        base = datetime.now().replace(hour=8, minute=0, second=0, microsecond=0) + timedelta(days=7)
        r1 = base + timedelta(days=7)
        r2 = base + timedelta(days=14)
        r3 = base + timedelta(days=21)
        end = base.replace(hour=9, minute=50)

        dtstart_str = base.strftime("%Y%m%dT%H%M%S")
        dtend_str = end.strftime("%Y%m%dT%H%M%S")
        rdate_str = ",".join(
            [r1.strftime("%Y%m%dT%H%M%S"), r2.strftime("%Y%m%dT%H%M%S"), r3.strftime("%Y%m%dT%H%M%S")]
        )

        ics_text = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:isdu-2-20990320T162721Z@isdu.app
DTSTAMP:20990320T162721Z
DTSTART;TZID=Asia/Shanghai:{dtstart}
DTEND;TZID=Asia/Shanghai:{dtend}
SUMMARY:离散数学(双语)
LOCATION:软件园5区107d
DESCRIPTION:教师: ***\\n学分: 4.0\\n上课周: 1,2,3,4
RDATE;TZID=Asia/Shanghai;VALUE=DATE-TIME:{rdate}
END:VEVENT
END:VCALENDAR
""".format(dtstart=dtstart_str, dtend=dtend_str, rdate=rdate_str)

        file_path = Path(__file__).parent / "_tmp_sample_rdate.ics"
        file_path.write_text(ics_text, encoding="utf-8")

        parser = ICSParser()
        courses = parser.parse_ics_file(str(file_path))
        courses = sorted(courses, key=lambda x: x["start_time"])
        file_path.unlink(missing_ok=True)

        self.assertEqual(len(courses), 4)
        self.assertEqual(
            [c["start_time"].strftime("%Y-%m-%d %H:%M") for c in courses],
            [
                base.strftime("%Y-%m-%d %H:%M"),
                r1.strftime("%Y-%m-%d %H:%M"),
                r2.strftime("%Y-%m-%d %H:%M"),
                r3.strftime("%Y-%m-%d %H:%M"),
            ],
        )
        self.assertTrue(all(c["summary"] == "离散数学(双语)" for c in courses))


    def test_parse_rdate_with_exdate_excludes_occurrence(self):
        """验证 EXDATE 能从 RDATE 重复集合中排除指定日期。"""
        base = datetime.now().replace(hour=8, minute=0, second=0, microsecond=0) + timedelta(days=7)
        r1 = base + timedelta(days=7)
        r2 = base + timedelta(days=14)
        r3 = base + timedelta(days=21)
        end = base.replace(hour=9, minute=50)

        dtstart_str = base.strftime("%Y%m%dT%H%M%S")
        dtend_str = end.strftime("%Y%m%dT%H%M%S")
        rdate_str = ",".join(
            [r1.strftime("%Y%m%dT%H%M%S"), r2.strftime("%Y%m%dT%H%M%S"), r3.strftime("%Y%m%dT%H%M%S")]
        )
        exdate_str = r2.strftime("%Y%m%dT%H%M%S")

        ics_text = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:isdu-3-20990320T162721Z@isdu.app
DTSTAMP:20990320T162721Z
DTSTART;TZID=Asia/Shanghai:{dtstart}
DTEND;TZID=Asia/Shanghai:{dtend}
SUMMARY:离散数学(双语)
LOCATION:软件园5区107d
DESCRIPTION:教师: ***
RDATE;TZID=Asia/Shanghai;VALUE=DATE-TIME:{rdate}
EXDATE;TZID=Asia/Shanghai;VALUE=DATE-TIME:{exdate}
END:VEVENT
END:VCALENDAR
""".format(dtstart=dtstart_str, dtend=dtend_str, rdate=rdate_str, exdate=exdate_str)

        file_path = Path(__file__).parent / "_tmp_sample_rdate_exdate.ics"
        file_path.write_text(ics_text, encoding="utf-8")

        parser = ICSParser()
        courses = parser.parse_ics_file(str(file_path))
        courses = sorted(courses, key=lambda x: x["start_time"])
        file_path.unlink(missing_ok=True)

        self.assertEqual(len(courses), 3)
        self.assertEqual(
            [c["start_time"].strftime("%Y-%m-%d %H:%M") for c in courses],
            [
                base.strftime("%Y-%m-%d %H:%M"),
                r1.strftime("%Y-%m-%d %H:%M"),
                r3.strftime("%Y-%m-%d %H:%M"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
