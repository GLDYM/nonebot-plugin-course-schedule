import importlib
import re
from contextlib import redirect_stderr, redirect_stdout
from datetime import date, datetime, time, timedelta
from io import StringIO

from dateutil import parser as dateutil_parser


_SIGNED_INT_RE = re.compile(r"^[+-]?\d+$")
_FULL_DAY_START = time.min
_FULL_DAY_END = time(23, 59, 59)
_JIONLP_MODULE = None


class DateParseError(ValueError):
    """Raised when a command argument cannot be resolved to a single date."""


def parse_schedule_date_arg(raw_arg: str, now: datetime) -> tuple[date, str]:
    text = raw_arg.strip()
    if text == "":
        return now.date(), "today"

    normalized = text.replace(".", "-")
    if _SIGNED_INT_RE.fullmatch(normalized):
        return now.date() + timedelta(days=int(normalized)), "offset"

    target_date = _parse_single_day_date(normalized, now)
    return target_date, "specific"


def _parse_single_day_date(text: str, now: datetime) -> date:
    jionlp_date = _parse_with_jionlp(text, now)
    if jionlp_date is not None:
        return jionlp_date

    try:
        return dateutil_parser.parse(text).date()
    except Exception as exc:  # pragma: no cover - fallback error path
        raise DateParseError(str(exc)) from exc


def _parse_with_jionlp(text: str, now: datetime) -> date | None:
    try:
        jionlp = _get_jionlp()
        result = jionlp.parse_time(text, time_base=now)
    except Exception:
        return None

    if not isinstance(result, dict):
        return None

    if result.get("type") not in {"time_point", "time_span"}:
        return None

    time_range = result.get("time")
    if not isinstance(time_range, list) or len(time_range) != 2:
        return None

    try:
        start = datetime.fromisoformat(time_range[0])
        end = datetime.fromisoformat(time_range[1])
    except (TypeError, ValueError):
        return None

    if start.date() != end.date():
        return None

    if start.time() != _FULL_DAY_START or end.time() != _FULL_DAY_END:
        return None

    return start.date()


def _get_jionlp():
    global _JIONLP_MODULE
    if _JIONLP_MODULE is None:
        stream = StringIO()
        # jionlp imports print a startup banner; silence it so bot logs stay clean.
        with redirect_stdout(stream), redirect_stderr(stream):
            _JIONLP_MODULE = importlib.import_module("jionlp")
    return _JIONLP_MODULE
