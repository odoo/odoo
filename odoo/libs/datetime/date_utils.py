__all__ = [
    "WEEKDAY_NUMBER",
    "Granularity",
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
    "start_of",
    "subtract",
    "sum_intervals",
    "time_to_float",
    "to_timezone",
    "utc",
    "weekend",
    "weeknumber",
    "weekstart",
]

import calendar
import math
from collections.abc import Callable, Iterable, Iterator
from datetime import UTC, date, datetime, time, timedelta, timezone, tzinfo
from typing import TYPE_CHECKING, Literal

from dateutil.relativedelta import relativedelta, weekdays

from odoo.libs.numbers.float_utils import float_round

if TYPE_CHECKING:
    import babel

# Use stdlib UTC for best compatibility
utc = UTC

WEEKDAY_NUMBER = dict(
    zip(
        (
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        ),
        range(7),
        strict=True,
    )
)

Granularity = Literal["year", "quarter", "month", "week", "day", "hour"]


def float_to_time(hours: float) -> time:
    """Convert a number of hours into a time object.

    :param hours: Number of hours (0.0 to 24.0)
    :returns: A time object

    Example::

        >>> float_to_time(8.5)
        datetime.time(8, 30)
        >>> float_to_time(24.0)
        datetime.time(23, 59, 59, 999999)
    """
    if hours == 24.0:
        return time.max
    fractional, integral = math.modf(hours)
    return time(int(integral), int(float_round(60 * fractional, precision_digits=0)), 0)


def time_to_float(duration: time | timedelta) -> float:
    """Convert a time object to a number of hours.

    :param duration: A time object or timedelta
    :returns: Number of hours as float

    Example::

        >>> time_to_float(time(8, 30))
        8.5
        >>> time_to_float(timedelta(hours=2, minutes=15))
        2.25
    """
    if isinstance(duration, timedelta):
        return duration.total_seconds() / 3600
    if duration == time.max:
        return 24.0
    seconds = duration.microsecond / 1_000_000 + duration.second + duration.minute * 60
    return seconds / 3600 + duration.hour


def localized(dt: datetime) -> datetime:
    """When missing, add UTC tzinfo to a datetime.

    :param dt: A datetime object
    :returns: The datetime with tzinfo set to UTC if it was naive

    Example::

        >>> localized(datetime(2024, 1, 1, 12, 0)).tzinfo
        <UTC>
    """
    return dt if dt.tzinfo else dt.replace(tzinfo=utc)


def to_timezone(tz: tzinfo | None) -> Callable[[datetime], datetime]:
    """Get a function converting a datetime to another localized datetime.

    :param tz: Target timezone (None means convert to naive UTC)
    :returns: A function that converts datetimes

    Example::

        >>> from zoneinfo import ZoneInfo
        >>> to_utc = to_timezone(None)
        >>> to_paris = to_timezone(ZoneInfo('Europe/Paris'))
    """
    if tz is None:
        return lambda dt: dt.astimezone(utc).replace(tzinfo=None)
    return lambda dt: dt.astimezone(tz)


def parse_iso_date(value: str) -> date | datetime:
    """Parse an ISO encoded string to a date or datetime.

    :param value: ISO formatted date string (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)
    :returns: A date or datetime object
    :raises ValueError: When the format is invalid or has a timezone

    Example::

        >>> parse_iso_date('2024-01-15')
        datetime.date(2024, 1, 15)
        >>> parse_iso_date('2024-01-15T10:30:00')
        datetime.datetime(2024, 1, 15, 10, 30)
    """
    if len(value) <= 10:
        return date.fromisoformat(value)
    now = datetime.fromisoformat(value)
    if now.tzinfo is not None:
        raise ValueError(f"expecting only datetimes with no timezone: {value!r}")
    return now


def get_month[D: (date, datetime)](date: D) -> tuple[D, D]:
    """Compute the month date range from a date (first and last day of month).

    :param date: Any date within the month
    :returns: Tuple of (first_day, last_day) of the month

    Example::

        >>> get_month(date(2024, 2, 15))
        (datetime.date(2024, 2, 1), datetime.date(2024, 2, 29))
    """
    return date.replace(day=1), date.replace(
        day=calendar.monthrange(date.year, date.month)[1]
    )


def get_quarter_number(date: date) -> int:
    """Get the quarter number from a date (1-4).

    :param date: Any date
    :returns: Quarter number (1, 2, 3, or 4)

    Example::

        >>> get_quarter_number(date(2024, 5, 15))
        2
    """
    return (date.month - 1) // 3 + 1


def get_quarter[D: (date, datetime)](date: D) -> tuple[D, D]:
    """Compute the quarter date range from a date (first and last day of quarter).

    :param date: Any date within the quarter
    :returns: Tuple of (first_day, last_day) of the quarter

    Example::

        >>> get_quarter(date(2024, 5, 15))
        (datetime.date(2024, 4, 1), datetime.date(2024, 6, 30))
    """
    month_from = (date.month - 1) // 3 * 3 + 1
    date_from = date.replace(month=month_from, day=1)
    date_to = date_from.replace(month=month_from + 2)
    date_to = date_to.replace(day=calendar.monthrange(date_to.year, date_to.month)[1])
    return date_from, date_to


def get_fiscal_year[D: (date, datetime)](date: D, day: int = 31, month: int = 12) -> tuple[D, D]:
    """Compute the fiscal year date range from a date.

    A fiscal year is the period used by governments for accounting purposes
    and varies between countries. By default, calling this method with only
    one parameter gives the calendar year (ending YYYY-12-31).

    :param date: A date belonging to the fiscal year
    :param day: The day of month the fiscal year ends (default: 31)
    :param month: The month of year the fiscal year ends (default: 12)
    :returns: Tuple of (first_day, last_day) of the fiscal year

    Example::

        >>> get_fiscal_year(date(2024, 3, 15))
        (datetime.date(2024, 1, 1), datetime.date(2024, 12, 31))
        >>> get_fiscal_year(date(2024, 3, 15), day=31, month=3)
        (datetime.date(2023, 4, 1), datetime.date(2024, 3, 31))
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


def get_timedelta(
    qty: int,
    granularity: Literal["hour", "day", "week", "month", "year"],
):
    """Get a relativedelta object for the given quantity and interval unit.

    :param qty: Number of intervals
    :param granularity: Type of interval ('hour', 'day', 'week', 'month', 'year')
    :returns: A relativedelta object

    Example::

        >>> get_timedelta(3, 'month')
        relativedelta(months=+3)
    """
    switch = {
        "hour": relativedelta(hours=qty),
        "day": relativedelta(days=qty),
        "week": relativedelta(weeks=qty),
        "month": relativedelta(months=qty),
        "year": relativedelta(years=qty),
    }
    return switch[granularity]


def start_of[D: (date, datetime)](value: D, granularity: Granularity) -> D:
    """Get start of a time period from a date or a datetime.

    :param value: Initial date or datetime
    :param granularity: Type of period ('year', 'quarter', 'month', 'week', 'day', 'hour')
    :returns: A date/datetime object corresponding to the start of the period

    Example::

        >>> start_of(date(2024, 5, 15), 'month')
        datetime.date(2024, 5, 1)
        >>> start_of(datetime(2024, 5, 15, 14, 30), 'day')
        datetime.datetime(2024, 5, 15, 0, 0)
    """
    is_datetime = isinstance(value, datetime)
    if granularity == "year":
        result = value.replace(month=1, day=1)
    elif granularity == "quarter":
        result = get_quarter(value)[0]
    elif granularity == "month":
        result = value.replace(day=1)
    elif granularity == "week":
        result = value - relativedelta(
            days=calendar.weekday(value.year, value.month, value.day)
        )
    elif granularity == "day":
        result = value
    elif granularity == "hour" and is_datetime:
        return datetime.combine(value, time.min).replace(hour=value.hour)
    elif is_datetime:
        raise ValueError(
            f"Granularity must be year, quarter, month, week, day or hour for value {value}"
        )
    else:
        raise ValueError(
            f"Granularity must be year, quarter, month, week or day for value {value}"
        )

    return datetime.combine(result, time.min) if is_datetime else result


def end_of[D: (date, datetime)](value: D, granularity: Granularity) -> D:
    """Get end of a time period from a date or a datetime.

    :param value: Initial date or datetime
    :param granularity: Type of period ('year', 'quarter', 'month', 'week', 'day', 'hour')
    :returns: A date/datetime object corresponding to the end of the period

    Example::

        >>> end_of(date(2024, 5, 15), 'month')
        datetime.date(2024, 5, 31)
        >>> end_of(datetime(2024, 5, 15, 14, 30), 'day')
        datetime.datetime(2024, 5, 15, 23, 59, 59, 999999)
    """
    is_datetime = isinstance(value, datetime)
    if granularity == "year":
        result = value.replace(month=12, day=31)
    elif granularity == "quarter":
        result = get_quarter(value)[1]
    elif granularity == "month":
        result = value + relativedelta(day=1, months=1, days=-1)
    elif granularity == "week":
        result = value + relativedelta(
            days=6 - calendar.weekday(value.year, value.month, value.day)
        )
    elif granularity == "day":
        result = value
    elif granularity == "hour" and is_datetime:
        return datetime.combine(value, time.max).replace(hour=value.hour)
    elif is_datetime:
        raise ValueError(
            f"Granularity must be year, quarter, month, week, day or hour for value {value}"
        )
    else:
        raise ValueError(
            f"Granularity must be year, quarter, month, week or day for value {value}"
        )

    return datetime.combine(result, time.max) if is_datetime else result


def add[D: (date, datetime)](value: D, *args, **kwargs) -> D:
    """Return the sum of a date/datetime and a relativedelta.

    :param value: Initial date or datetime
    :param args: Positional args to pass to relativedelta
    :param kwargs: Keyword args to pass to relativedelta
    :returns: The resulting date/datetime

    Example::

        >>> add(date(2024, 1, 15), months=1, days=5)
        datetime.date(2024, 2, 20)
    """
    return value + relativedelta(*args, **kwargs)


def subtract[D: (date, datetime)](value: D, *args, **kwargs) -> D:
    """Return the difference between a date/datetime and a relativedelta.

    :param value: Initial date or datetime
    :param args: Positional args to pass to relativedelta
    :param kwargs: Keyword args to pass to relativedelta
    :returns: The resulting date/datetime

    Example::

        >>> subtract(date(2024, 3, 15), months=1)
        datetime.date(2024, 2, 15)
    """
    return value - relativedelta(*args, **kwargs)


def date_range[D: (date, datetime)](
    start: D, end: D, step: relativedelta = relativedelta(months=1)
) -> Iterator[datetime]:
    """Date range generator with a step interval.

    :param start: Beginning date of the range
    :param end: Ending date of the range (inclusive)
    :param step: Interval of the range (positive, default: 1 month)
    :returns: An iterator of dates/datetimes from start to end

    Example::

        >>> list(date_range(date(2024, 1, 1), date(2024, 3, 1)))
        [datetime.date(2024, 1, 1), datetime.date(2024, 2, 1), datetime.date(2024, 3, 1)]
    """
    post_process = lambda dt: dt  # noqa: E731
    if isinstance(start, datetime) and isinstance(end, datetime):
        are_naive = start.tzinfo is None and end.tzinfo is None
        are_utc = start.tzinfo == utc and end.tzinfo == utc

        are_others = start.tzinfo and end.tzinfo and not are_utc

        # Check timezone consistency using key attribute (works with both pytz and zoneinfo)
        if are_others:
            start_key = getattr(start.tzinfo, "key", None) or getattr(
                start.tzinfo, "zone", None
            )
            end_key = getattr(end.tzinfo, "key", None) or getattr(
                end.tzinfo, "zone", None
            )
            if start_key != end_key:
                raise ValueError(
                    "Timezones of start argument and end argument seem inconsistent"
                )

        if not are_naive and not are_utc and not are_others:
            raise ValueError("Timezones of start argument and end argument mismatch")

        if not are_naive:
            tz = start.tzinfo
            post_process = lambda dt, tz=tz: dt.replace(tzinfo=tz)  # noqa: E731
            start = start.replace(tzinfo=None)
            end = end.replace(tzinfo=None)

    elif isinstance(start, date) and isinstance(end, date):
        if not isinstance(start + step, date):
            raise ValueError("the step interval must add only entire days")
    else:
        raise ValueError("start/end should be both date or both datetime type")

    if start > end:
        raise ValueError("start > end, start date must be before end")

    if start >= start + step:
        raise ValueError("Looks like step is null or negative")

    while start <= end:
        yield post_process(start)
        start += step


def sum_intervals(intervals: Iterable[tuple[datetime, datetime, ...]]) -> float:
    """Sum the intervals duration in hours.

    :param intervals: Iterable of tuples where first two elements are start/end datetimes
    :returns: Total duration in hours

    Example::

        >>> intervals = [(datetime(2024, 1, 1, 9, 0), datetime(2024, 1, 1, 12, 0))]
        >>> sum_intervals(intervals)
        3.0
    """
    return sum(
        (interval[1] - interval[0]).total_seconds() / 3600 for interval in intervals
    )


def weeknumber(locale: babel.Locale, date: date) -> tuple[int, int]:
    """Compute the year and week number of a date.

    The week number is 1-indexed (first week is week number 1).

    For ISO locales (first day of week = monday, min week days = 4) the concept
    is clear and the Python stdlib implements it directly.

    For other locales, the first week of the year is the one which contains
    the first day of the year (taking first day of week into account).

    :param locale: Babel locale object
    :param date: The date to compute week number for
    :returns: Tuple of (year, week_number)
    """
    if locale.first_week_day == 0 and locale.min_week_days == 4:
        return date.isocalendar()[:2]

    fdny = date.replace(year=date.year + 1, month=1, day=1) - relativedelta(
        weekday=weekdays[locale.first_week_day](-1)
    )
    if date >= fdny:
        return date.year + 1, 1

    fdow = date.replace(month=1, day=1) - relativedelta(
        weekday=weekdays[locale.first_week_day](-1)
    )
    doy = (date - fdow).days

    return date.year, (doy // 7 + 1)


def weekstart(locale: babel.Locale, date: date):
    """Return the first weekday of the week containing the date.

    If the date is already that weekday, it is returned unchanged.
    Otherwise, it is shifted back to the most recent such weekday.

    :param locale: Babel locale object
    :param date: The reference date
    :returns: The first day of the week containing the date

    Example (week starts Sunday)::

        weekstart of Sat 30 Aug -> Sun 24 Aug
        weekstart of Sat 23 Aug -> Sun 17 Aug
    """
    return date + relativedelta(weekday=weekdays[locale.first_week_day](-1))


def weekend(locale: babel.Locale, date: date):
    """Return the last weekday of the week containing the date.

    If the date is already that weekday, it is returned unchanged.
    Otherwise, it is shifted forward to the next such weekday.

    :param locale: Babel locale object
    :param date: The reference date
    :returns: The last day of the week containing the date

    Example (week starts Sunday, ends Saturday)::

        weekend of Sun 24 Aug -> Sat 30 Aug
        weekend of Sat 30 Aug -> Sat 30 Aug
    """
    return weekstart(locale, date) + relativedelta(days=6)
