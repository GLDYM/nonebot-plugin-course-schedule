from pathlib import Path
import sys
import importlib.util

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def load_ics_parser_class():
    module_path = PROJECT_ROOT / "nonebot_plugin_course_schedule" / "utils" / "ics_parser.py"
    spec = importlib.util.spec_from_file_location("ics_parser_runtime_module", module_path)
    module = importlib.util.module_from_spec(spec)
    if spec is None or spec.loader is None:
        raise RuntimeError("无法加载 ics_parser 模块")
    spec.loader.exec_module(module)
    return module.ICSParser


ICSParser = load_ics_parser_class()


SAMPLE_ICS = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:isdu-2-20260320T162721Z@isdu.app
DTSTAMP:20260320T162721Z
DTSTART;TZID=Asia/Shanghai:20260302T080000
DTEND;TZID=Asia/Shanghai:20260302T095000
SUMMARY:离散数学(双语)
LOCATION:软件园5区107d
DESCRIPTION:教师: ***\\n学分: 4.0\\n上课周: 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16
RDATE;TZID=Asia/Shanghai;VALUE=DATE-TIME:20260309T080000,20260316T080000,20260323T080000
END:VEVENT
END:VCALENDAR
"""


def main() -> None:
    temp_file = Path("_tmp_rdate_sample.ics")
    temp_file.write_text(SAMPLE_ICS, encoding="utf-8")

    parser = ICSParser()
    courses = parser.parse_ics_file(str(temp_file))
    courses = sorted(courses, key=lambda x: x["start_time"])

    print(f"解析结果数量: {len(courses)}")
    for idx, course in enumerate(courses, start=1):
        print(
            f"{idx}. {course['summary']} | "
            f"{course['start_time'].isoformat()} -> {course['end_time'].isoformat()} | "
            f"{course['location']}"
        )

    print("\n说明: 当前解析器仅保留今天起 365 天内的课程。")

    temp_file.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
