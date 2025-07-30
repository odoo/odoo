from __future__ import annotations

import calendar
import math
import re
import typing
from datetime import date, datetime, time, timedelta, tzinfo

import pytz
from dateutil.relativedelta import relativedelta, weekdays

from .float_utils import float_round

if typing.TYPE_CHECKING:
    import babel
    from collections.abc import Callable, Iterable, Iterator
    from odoo.orm.types import Environment
    D = typing.TypeVar('D', date, datetime)

utc = pytz.utc

TRUNCATE_TODAY = relativedelta(microsecond=0, second=0, minute=0, hour=0)
TRUNCATE_UNIT = {
    'day': TRUNCATE_TODAY,
    'month': TRUNCATE_TODAY,
    'year': TRUNCATE_TODAY,
    'week': TRUNCATE_TODAY,
    'hour': relativedelta(microsecond=0, second=0, minute=0),
    'minute': relativedelta(microsecond=0, second=0),
    'second': relativedelta(microsecond=0),
}
WEEKDAY_NUMBER = dict(zip(
    ('monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'),
    range(7),
    strict=True,
))
_SHORT_DATE_UNIT = {
    'd': 'days',
    'm': 'months',
    'y': 'years',
    'w': 'weeks',
    'H': 'hours',
    'M': 'minutes',
    'S': 'seconds',
}

__all__ = [
    'date_range',
    'float_to_time',
    'get_fiscal_year',
    'get_month',
    'get_quarter',
    'get_quarter_number',
    'get_timedelta',
    'localized',
    'parse_date',
    'parse_iso_date',
    'sum_intervals',
    'time_to_float',
    'to_timezone',
]


def float_to_time(hours: float) -> time:
    """ Convert a number of hours into a time object. """
    if hours == 24.0:
        return time.max
    fractional, integral = math.modf(hours)
    return time(int(integral), int(float_round(60 * fractional, precision_digits=0)), 0)


def time_to_float(duration: time | timedelta) -> float:
    """ Convert a time object to a number of hours. """
    if isinstance(duration, timedelta):
        return duration.total_seconds() / 3600
    if duration == time.max:
        return 24.0
    seconds = duration.microsecond / 1_000_000 + duration.second + duration.minute * 60
    return seconds / 3600 + duration.hour


def localized(dt: datetime) -> datetime:
    """ When missing, add tzinfo to a datetime. """
    return dt if dt.tzinfo else dt.replace(tzinfo=utc)


def to_timezone(tz: tzinfo | None) -> Callable[[datetime], datetime]:
    """ Get a function converting a datetime to another localized datetime. """
    if tz is None:
        return lambda dt: dt.astimezone(utc).replace(tzinfo=None)
    return lambda dt: dt.astimezone(tz)


def parse_iso_date(value: str) -> date | datetime:
    """ Parse a ISO encoded string to a date or datetime.

    :raises ValueError: when the format is invalid or has a timezone
    """
    # Looks like ISO format
    if len(value) <= 10:
        return date.fromisoformat(value)
    now = datetime.fromisoformat(value)
    if now.tzinfo is not None:
        raise ValueError(f"expecting only datetimes with no timezone: {value!r}")
    return now


def parse_date(value: str, env: Environment) -> date | datetime:
    r""" Parse a technical date string into a date or datetime.

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
    :param naive: Whether to cast the result to a naive datetime.
    """
    if re.match(r'\d+-', value):
        return parse_iso_date(value)
    terms = value.split()
    if not terms:
        raise ValueError("Empty date value")

    # Find the starting point
    from odoo.orm.fields_temporal import Date, Datetime  # noqa: PLC0415

    dt: datetime | date = Datetime.now()
    term = terms.pop(0) if terms[0] in ('today', 'now') else 'now'
    if term == 'today':
        dt = Date.context_today(env['base'], dt)
    else:
        dt = Datetime.context_timestamp(env['base'], dt)

    for term in terms:
        operator = term[0]
        if operator not in ('+', '-', '=') or len(term) < 3:
            raise ValueError(f"Invalid term {term!r} in expression date: {value!r}")

        # Weekday
        dayname = term[1:]
        if dayname in WEEKDAY_NUMBER or dayname == "week_start":
            week_start = int(env["res.lang"]._get_data(code=env.user.lang).week_start) - 1
            weekday = week_start if dayname == "week_start" else WEEKDAY_NUMBER[dayname]
            weekday_offset = ((weekday - week_start) % 7) - ((dt.weekday() - week_start) % 7)
            if operator in ('+', '-'):
                if operator == '+' and weekday_offset < 0:
                    weekday_offset += 7
                elif operator == '-' and weekday_offset > 0:
                    weekday_offset -= 7
            elif isinstance(dt, datetime):
                dt += TRUNCATE_TODAY
            dt += timedelta(weekday_offset)
            continue

        # Operations on dates
        try:
            unit = _SHORT_DATE_UNIT[term[-1]]
            if operator in ('+', '-'):
                number = int(term[:-1])  # positive or negative
            else:
                number = int(term[1:-1])
                unit = unit.removesuffix('s')
                if isinstance(dt, datetime):
                    dt += TRUNCATE_UNIT[unit]
                # note: '=Nw' is not supported
            dt += relativedelta(**{unit: number})
        except (ValueError, TypeError, KeyError):
            raise ValueError(f"Invalid term {term!r} in expression date: {value!r}")

    # always return a naive date
    if isinstance(dt, datetime) and dt.tzinfo is not None:
        dt = dt.astimezone(pytz.utc).replace(tzinfo=None)
    return dt


def get_month(date: D) -> tuple[D, D]:
    """ Compute the month date range from a date (set first and last day of month).
    """
    return date.replace(day=1), date.replace(day=calendar.monthrange(date.year, date.month)[1])


def get_quarter_number(date: date) -> int:
    """ Get the quarter from a date (1-4)."""
    return (date.month - 1) // 3 + 1


def get_quarter(date: D) -> tuple[D, D]:
    """ Compute the quarter date range from a date (set first and last day of quarter).
    """
    month_from = (date.month - 1) // 3 * 3 + 1
    date_from = date.replace(month=month_from, day=1)
    date_to = date_from.replace(month=month_from + 2)
    date_to = date_to.replace(day=calendar.monthrange(date_to.year, date_to.month)[1])
    return date_from, date_to


def get_fiscal_year(date: D, day: int = 31, month: int = 12) -> tuple[D, D]:
    """ Compute the fiscal year date range from a date (first and last day of fiscal year).
    A fiscal year is the period used by governments for accounting purposes and vary between countries.
    By default, calling this method with only one parameter gives the calendar year because the ending date of the
    fiscal year is set to the YYYY-12-31.

    :param date: A date belonging to the fiscal year
    :param day:     The day of month the fiscal year ends.
    :param month:   The month of year the fiscal year ends.
    :return: The start and end dates of the fiscal year.
    """

    def fix_day(year, month, day):
        max_day = calendar.monthrange(year, month)[1]
        if month == 2 and day in (28, max_day):
            return max_day
        return min(day, max_day)

    date_to = date.replace(month=month, day=fix_day(date.year, month, day))

    if date <= date_to:
        date_from = date_to - relativedelta(years=1)
        day = fix_day(date_from.year, date_from.month, date_from.day)
        date_from = date_from.replace(day=day)
        date_from += relativedelta(days=1)
    else:
        date_from = date_to + relativedelta(days=1)
        date_to = date_to + relativedelta(years=1)
        day = fix_day(date_to.year, date_to.month, date_to.day)
        date_to = date_to.replace(day=day)
    return date_from, date_to


def get_timedelta(qty: int, granularity: typing.Literal['hour', 'day', 'week', 'month', 'year']):
    """ Helper to get a `relativedelta` object for the given quantity and interval unit.
    """
    switch = {
        'hour': relativedelta(hours=qty),
        'day': relativedelta(days=qty),
        'week': relativedelta(weeks=qty),
        'month': relativedelta(months=qty),
        'year': relativedelta(years=qty),
    }
    return switch[granularity]


Granularity = typing.Literal['year', 'quarter', 'month', 'week', 'day', 'hour']


def start_of(value: D, granularity: Granularity) -> D:
    """
    Get start of a time period from a date or a datetime.

    :param value: initial date or datetime.
    :param granularity: type of period in string, can be year, quarter, month, week, day or hour.
    :return: a date/datetime object corresponding to the start of the specified period.
    """
    is_datetime = isinstance(value, datetime)
    if granularity == "year":
        result = value.replace(month=1, day=1)
    elif granularity == "quarter":
        # Q1 = Jan 1st
        # Q2 = Apr 1st
        # Q3 = Jul 1st
        # Q4 = Oct 1st
        result = get_quarter(value)[0]
    elif granularity == "month":
        result = value.replace(day=1)
    elif granularity == 'week':
        # `calendar.weekday` uses ISO8601 for start of week reference, this means that
        # by default MONDAY is the first day of the week and SUNDAY is the last.
        result = value - relativedelta(days=calendar.weekday(value.year, value.month, value.day))
    elif granularity == "day":
        result = value
    elif granularity == "hour" and is_datetime:
        return datetime.combine(value, time.min).replace(hour=value.hour)
    elif is_datetime:
        raise ValueError(
            "Granularity must be year, quarter, month, week, day or hour for value %s" % value
        )
    else:
        raise ValueError(
            "Granularity must be year, quarter, month, week or day for value %s" % value
        )

    return datetime.combine(result, time.min) if is_datetime else result


def end_of(value: D, granularity: Granularity) -> D:
    """
    Get end of a time period from a date or a datetime.

    :param value: initial date or datetime.
    :param granularity: Type of period in string, can be year, quarter, month, week, day or hour.
    :return: A date/datetime object corresponding to the start of the specified period.
    """
    is_datetime = isinstance(value, datetime)
    if granularity == "year":
        result = value.replace(month=12, day=31)
    elif granularity == "quarter":
        # Q1 = Mar 31st
        # Q2 = Jun 30th
        # Q3 = Sep 30th
        # Q4 = Dec 31st
        result = get_quarter(value)[1]
    elif granularity == "month":
        result = value + relativedelta(day=1, months=1, days=-1)
    elif granularity == 'week':
        # `calendar.weekday` uses ISO8601 for start of week reference, this means that
        # by default MONDAY is the first day of the week and SUNDAY is the last.
        result = value + relativedelta(days=6 - calendar.weekday(value.year, value.month, value.day))
    elif granularity == "day":
        result = value
    elif granularity == "hour" and is_datetime:
        return datetime.combine(value, time.max).replace(hour=value.hour)
    elif is_datetime:
        raise ValueError(
            "Granularity must be year, quarter, month, week, day or hour for value %s" % value
        )
    else:
        raise ValueError(
            "Granularity must be year, quarter, month, week or day for value %s" % value
        )

    return datetime.combine(result, time.max) if is_datetime else result


def add(value: D, *args, **kwargs) -> D:
    """
    Return the sum of ``value`` and a :class:`relativedelta`.

    :param value: initial date or datetime.
    :param args: positional args to pass directly to :class:`relativedelta`.
    :param kwargs: keyword args to pass directly to :class:`relativedelta`.
    :return: the resulting date/datetime.
    """
    return value + relativedelta(*args, **kwargs)


def subtract(value: D, *args, **kwargs) -> D:
    """
    Return the difference between ``value`` and a :class:`relativedelta`.

    :param value: initial date or datetime.
    :param args: positional args to pass directly to :class:`relativedelta`.
    :param kwargs: keyword args to pass directly to :class:`relativedelta`.
    :return: the resulting date/datetime.
    """
    return value - relativedelta(*args, **kwargs)


def date_range(start: D, end: D, step: relativedelta = relativedelta(months=1)) -> Iterator[datetime]:
    """Date range generator with a step interval.

    :param start: beginning date of the range.
    :param end: ending date of the range (inclusive).
    :param step: interval of the range (positive).
    :return: a range of datetime from start to end.
    """

    post_process = lambda dt: dt  # noqa: E731
    if isinstance(start, datetime) and isinstance(end, datetime):
        are_naive = start.tzinfo is None and end.tzinfo is None
        are_utc = start.tzinfo == pytz.utc and end.tzinfo == pytz.utc

        # Cases with miscellenous timezone are more complexe because of DST.
        are_others = start.tzinfo and end.tzinfo and not are_utc

        if are_others and start.tzinfo.zone != end.tzinfo.zone:
            raise ValueError("Timezones of start argument and end argument seem inconsistent")

        if not are_naive and not are_utc and not are_others:
            raise ValueError("Timezones of start argument and end argument mismatch")

        if not are_naive:
            post_process = start.tzinfo.localize
            start = start.replace(tzinfo=None)
            end = end.replace(tzinfo=None)

    elif isinstance(start, date) and isinstance(end, date):
        if not isinstance(start + step, date):
            raise ValueError("the step interval must add only entire days")  # noqa: TRY004
    else:
        raise ValueError("start/end should be both date or both datetime type")  # noqa: TRY004

    if start > end:
        raise ValueError("start > end, start date must be before end")

    if start >= start + step:
        raise ValueError("Looks like step is null or negative")

    while start <= end:
        yield post_process(start)
        start += step


def sum_intervals(intervals: Iterable[tuple[datetime, datetime, ...]]) -> float:
    """ Sum the intervals duration (unit: hour)"""
    return sum(
        (interval[1] - interval[0]).total_seconds() / 3600
        for interval in intervals
    )


def weeknumber(locale: babel.Locale, date: date) -> tuple[int, int]:
    """Computes the year and weeknumber of `date`. The week number is 1-indexed
    (so the first week is week number 1).

    For ISO locales (first day of week = monday, min week days = 4) the concept
    is clear and the Python stdlib implements it directly.

    For other locales, it's basically nonsensical as there is no actual
    definition. For now we will implement non-split first-day-of-year, that is
    the first week of the year is the one which contains the first day of the
    year (taking first day of week in account), and the days of the previous
    year which are part of that week are considered to be in the next year for
    calendaring purposes.

    That is December 27, 2015 is in the first week of 2016.

    An alternative is to split the week in two, so the week from December 27,
    2015 to January 2, 2016 would be *both* W53/2015 and W01/2016.
    """
    if locale.first_week_day == 0 and locale.min_week_days == 4:
        # woohoo nothing to do
        return date.isocalendar()[:2]

    # first find the first day of the first week of the next year, if the
    # reference date is after that then it must be in the first week of the next
    # year, remove this if we decide to implement split weeks instead
    fdny = date.replace(year=date.year + 1, month=1, day=1) \
       - relativedelta(weekday=weekdays[locale.first_week_day](-1))
    if date >= fdny:
        return date.year + 1, 1

    # otherwise get the number of periods of 7 days between the first day of the
    # first week and the reference
    fdow = date.replace(month=1, day=1) \
       - relativedelta(weekday=weekdays[locale.first_week_day](-1))
    doy = (date - fdow).days

    return date.year, (doy // 7 + 1)
