import re
import typing
from datetime import UTC, date, datetime, timedelta
from typing import Any

from dateutil.relativedelta import relativedelta

from odoo.libs.datetime import (
    TIME_UNIT_SELECTION,
    WEEKDAY_NUMBER,
    Anchor,
    TimeUnit,
    add,
    anchor_day,
    date_range,
    end_of,
    float_to_time,
    get_fiscal_year,
    get_intervals_hours,
    get_month,
    get_quarter,
    get_quarter_number,
    get_timedelta,
    localized,
    next_after,
    next_anchor,
    occurrences_after,
    parse_iso_date,
    previous_anchor,
    start_of,
    subtract,
    time_to_float,
    time_unit_selection,
    to_timezone,
    utc,
    weekend,
    weeknumber,
    weekstart,
)
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


if typing.TYPE_CHECKING:
    from odoo.orm.runtime import Environment

_TRUNCATE_TODAY = relativedelta(microsecond=0, second=0, minute=0, hour=0)
_TRUNCATE_UNIT = {
    "day": _TRUNCATE_TODAY,
    "month": _TRUNCATE_TODAY,
    "year": _TRUNCATE_TODAY,
    "hour": relativedelta(microsecond=0, second=0, minute=0),
    "minute": relativedelta(microsecond=0, second=0),
    "second": relativedelta(microsecond=0),
}
_SHORT_DATE_UNIT = {
    "d": "days",
    "m": "months",
    "y": "years",
    "w": "weeks",
    "H": "hours",
    "M": "minutes",
    "S": "seconds",
}

__all__ = [
    "TIME_UNIT_SELECTION",
    "WEEKDAY_NUMBER",
    "Anchor",
    "TimeUnit",
    "add",
    "anchor_day",
    "date_range",
    "end_of",
    "float_to_time",
    "get_fiscal_year",
    "get_intervals_hours",
    "get_month",
    "get_quarter",
    "get_quarter_number",
    "get_timedelta",
    "localized",
    "next_after",
    "next_anchor",
    "occurrences_after",
    "parse_date_expression",
    "parse_iso_date",
    "previous_anchor",
    "start_of",
    "subtract",
    "time_to_float",
    "time_unit_selection",
    "to_timezone",
    "utc",
    "weekend",
    "weeknumber",
    "weekstart",
]


def _apply_weekday_term(
    dt: datetime | date, operator: str, dayname: str, week_start: int
) -> datetime | date:
    weekday = week_start if dayname == "week_start" else WEEKDAY_NUMBER[dayname]
    offset = ((weekday - week_start) % 7) - ((dt.weekday() - week_start) % 7)
    if operator == "+":
        if offset < 0:
            offset += 7
    elif operator == "-":
        if offset > 0:
            offset -= 7
    elif isinstance(dt, datetime):
        dt += _TRUNCATE_TODAY
    return dt + timedelta(offset)


def _apply_unit_term(dt: datetime | date, operator: str, term: str) -> datetime | date:
    unit = _SHORT_DATE_UNIT[term[-1]]
    if operator in ("+", "-"):
        number = int(term[:-1])
    else:
        number = int(term[1:-1])
        unit = unit.removesuffix("s")
        if unit not in _TRUNCATE_UNIT:
            raise ValueError(f"{term[-1]!r} cannot be set with '='; use '+' or '-'")
        if isinstance(dt, datetime):
            dt += _TRUNCATE_UNIT[unit]
    return dt + relativedelta(dt1=None, dt2=None, **{unit: number})


def parse_date_expression(value: str, env: Environment) -> date | datetime:
    if re.match(r"\d+-", value):
        return parse_iso_date(value)
    terms = value.split()
    if not terms:
        msg = "Empty date value"
        raise ValueError(msg)

    from odoo.orm.fields import Date, Datetime

    now = Datetime.now()
    term = terms.pop(0) if terms[0] in ("today", "now") else "now"
    started_as_date = term == "today"
    dt: datetime | date
    if started_as_date:
        dt = Date.context_today(env["base"], now)
    else:
        dt = Datetime.context_timestamp(env["base"], now)

    week_start: int | None = None

    for term in terms:
        operator = term[0]
        if operator not in ("+", "-", "=") or len(term) < 3:
            raise ValueError(f"Invalid term {term!r} in expression date: {value!r}")

        dayname = term[1:]
        if dayname in WEEKDAY_NUMBER or dayname == "week_start":
            if week_start is None:
                res_lang: Any = env["res.lang"]
                week_start = (
                    int(res_lang._get_data(code=env.user.lang).week_start) - 1  # type: ignore[attr-defined]
                )
            dt = _apply_weekday_term(dt, operator, dayname, week_start)
            continue

        try:
            dt = _apply_unit_term(dt, operator, term)
        except ValueError, TypeError, KeyError:
            raise ValueError(
                f"Invalid term {term!r} in expression date: {value!r}"
            ) from None

    if isinstance(dt, datetime):
        if dt.tzinfo is not None:
            dt = dt.astimezone(UTC).replace(tzinfo=None)
        elif started_as_date:
            dt = (
                dt.replace(tzinfo=env["base"].env.tz)
                .astimezone(UTC)
                .replace(tzinfo=None)
            )
    _debug.logic(
        "date_utils.expression_parsed",
        expression=value,
        terms=len(terms),
        started_as_date=started_as_date,
        week_start=week_start,
        result=str(dt),
    )
    return dt
