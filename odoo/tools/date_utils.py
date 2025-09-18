"""
Date and time utilities for Odoo.

This module re-exports agnostic utilities from odoo.libs.datetime and adds
Odoo-specific functions that require the environment.
"""

import re
import typing
from datetime import UTC, date, datetime, timedelta

from dateutil.relativedelta import relativedelta

# Re-export all agnostic utilities from libs/
from odoo.libs.datetime import (
    WEEKDAY_NUMBER,
    # Arithmetic
    add,
    # Iteration
    date_range,
    end_of,
    # Time conversion
    float_to_time,
    get_fiscal_year,
    # Period calculations
    get_month,
    get_quarter,
    get_quarter_number,
    get_timedelta,
    # Timezone handling
    localized,
    # Parsing
    parse_iso_date,
    start_of,
    subtract,
    sum_intervals,
    time_to_float,
    to_timezone,
    # Constants
    utc,
    weekend,
    # Week utilities
    weeknumber,
    weekstart,
)


def utcnow() -> datetime:
    """Return the current UTC time as a naive datetime.

    Non-deprecated replacement for ``datetime.utcnow()`` that is compatible
    with Odoo's naive-UTC-datetime convention used by ``fields.Datetime``.
    """
    return datetime.now(UTC).replace(tzinfo=None)


if typing.TYPE_CHECKING:
    from odoo.orm.runtime import Environment

# Internal constants used by resolve_date
_TRUNCATE_TODAY = relativedelta(microsecond=0, second=0, minute=0, hour=0)
_TRUNCATE_UNIT = {
    "day": _TRUNCATE_TODAY,
    "month": _TRUNCATE_TODAY,
    "year": _TRUNCATE_TODAY,
    "week": _TRUNCATE_TODAY,
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
    "WEEKDAY_NUMBER",
    "add",
    "date_range",
    "end_of",
    "float_to_time",
    "get_fiscal_year",
    "get_month",
    "get_quarter",
    "get_quarter_number",
    "get_timedelta",
    "localized",
    "parse_iso_date",
    # Odoo-specific
    "resolve_date",
    "start_of",
    "subtract",
    "sum_intervals",
    "time_to_float",
    "to_timezone",
    # Re-exported from libs
    "utc",
    "weekend",
    "weeknumber",
    "weekstart",
]


def resolve_date(value: str, env: Environment) -> date | datetime:
    r"""Parse a technical date string into a date or datetime.

    This supports ISO formatted dates and dates relative to now.
    `parse_iso_date` is used if the input starts with r'\d+-'.
    Otherwise, the date is computed by starting from now at user's timezone.
    We can also start 'today' (resulting in a date type). Then we apply offsets:

    - we can add 'd', 'w', 'm', 'y', 'H', 'M', 'S':
      days, weeks, months, years, hours, minutes, seconds
      - "+3d" to add 3 days
      - "-1m" to subtract one month
    - we can set a part of the date which will reset to midnight or only lower
      date parts
      - "=1d" sets first day of month at midnight
      - "=6m" sets June and resets to midnight
      - "=3H" sets time to 3:00:00
    - weekdays are handled similarly
      - "=tuesday" sets to Tuesday of the current week at midnight
      - "+monday" goes to next Monday (no change if we are on Monday)
      - "=week_start" sets to the first day of the current week, according to the locale

    The DSL for relative dates is as follows:
    ```
    relative_date := ('today' | 'now')? offset*
    offset := date_rel | time_rel | weekday
    date_rel := (regex) [=+-]\d+[dwmy]
    time_rel := (regex) [=+-]\d+[HMS]
    weekday := [=+-] ('monday' | ... | 'sunday' | 'week_start')
    ```

    An equivalent function is JavaScript is `parseSmartDateInput`.

    :param value: The string to parse
    :param env: The environment to get the current date (in user's tz)
    :returns: A date or datetime object
    """
    if re.match(r"\d+-", value):
        return parse_iso_date(value)
    terms = value.split()
    if not terms:
        raise ValueError("Empty date value")

    # Find the starting point
    from odoo.orm.fields import Date, Datetime

    dt: datetime | date = Datetime.now()
    term = terms.pop(0) if terms[0] in ("today", "now") else "now"
    if term == "today":
        dt = Date.context_today(env["base"], dt)
    else:
        dt = Datetime.context_timestamp(env["base"], dt)

    for term in terms:
        operator = term[0]
        if operator not in ("+", "-", "=") or len(term) < 3:
            raise ValueError(f"Invalid term {term!r} in expression date: {value!r}")

        # Weekday
        dayname = term[1:]
        if dayname in WEEKDAY_NUMBER or dayname == "week_start":
            week_start = (
                int(env["res.lang"]._get_data(code=env.user.lang).week_start) - 1
            )
            weekday = week_start if dayname == "week_start" else WEEKDAY_NUMBER[dayname]
            weekday_offset = ((weekday - week_start) % 7) - (
                (dt.weekday() - week_start) % 7
            )
            if operator in ("+", "-"):
                if operator == "+" and weekday_offset < 0:
                    weekday_offset += 7
                elif operator == "-" and weekday_offset > 0:
                    weekday_offset -= 7
            elif isinstance(dt, datetime):
                dt += _TRUNCATE_TODAY
            dt += timedelta(weekday_offset)
            continue

        # Operations on dates
        try:
            unit = _SHORT_DATE_UNIT[term[-1]]
            if operator in ("+", "-"):
                number = int(term[:-1])  # positive or negative
            else:
                number = int(term[1:-1])
                unit = unit.removesuffix("s")
                if isinstance(dt, datetime):
                    dt += _TRUNCATE_UNIT[unit]
                # note: '=Nw' is not supported
            dt += relativedelta(**{unit: number})
        except ValueError, TypeError, KeyError:
            raise ValueError(f"Invalid term {term!r} in expression date: {value!r}")

    # always return a naive date
    if isinstance(dt, datetime) and dt.tzinfo is not None:
        dt = dt.astimezone(UTC).replace(tzinfo=None)
    return dt
