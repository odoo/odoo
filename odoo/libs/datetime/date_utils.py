__all__ = [
    "WEEKDAY_NUMBER",
    "Anchor",
    "Granularity",
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
    "parse_iso_date",
    "previous_anchor",
    "real_cpu_time",
    "real_datetime_now",
    "real_time",
    "start_of",
    "subtract",
    "time_to_float",
    "to_timezone",
    "weekend",
    "weeknumber",
    "weekstart",
]

import calendar
import math
import time as _time
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta, tzinfo
from typing import TYPE_CHECKING, Any, Literal, cast

from dateutil.relativedelta import FR, MO, SA, SU, TH, TU, WE, relativedelta

from odoo.libs.numbers.float_utils import float_round

from .tz import utc

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Iterator, Sequence

    import babel


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
    if not 0.0 <= hours <= 24.0:
        msg = f"hours must be a number in [0.0, 24.0], got {hours!r}"
        raise ValueError(msg)
    if hours == 24.0:  # noqa: RUF069  exact boundary: 24.0 is representable and the range is already checked
        return time.max
    fractional, integral = math.modf(hours)
    minutes = int(float_round(60 * fractional, precision_digits=0))
    if minutes == 60:
        integral += 1
        minutes = 0
    if integral >= 24:
        return time.max
    return time(int(integral), minutes, 0)


def time_to_float(duration: time | timedelta) -> float:
    if isinstance(duration, timedelta):
        return duration.total_seconds() / 3600
    if duration == time.max:
        return 24.0
    seconds = duration.microsecond / 1_000_000 + duration.second + duration.minute * 60
    return seconds / 3600 + duration.hour


def localized(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=utc)


def to_timezone(tz: tzinfo | None) -> Callable[[datetime], datetime]:
    if tz is None:
        return lambda dt: dt.astimezone(utc).replace(tzinfo=None)
    return lambda dt: dt.astimezone(tz)


def parse_iso_date(value: str) -> date | datetime:
    if len(value) <= 10:
        return date.fromisoformat(value)
    now = datetime.fromisoformat(value)
    if now.tzinfo is not None:
        raise ValueError(f"expecting only datetimes with no timezone: {value!r}")
    return now


def get_month[D: (date, datetime)](date: D) -> tuple[D, D]:
    return date.replace(day=1), date.replace(
        day=calendar.monthrange(date.year, date.month)[1]
    )


def get_quarter_number(date: date) -> int:
    return (date.month - 1) // 3 + 1


def get_quarter[D: (date, datetime)](date: D) -> tuple[D, D]:
    month_from = (date.month - 1) // 3 * 3 + 1
    date_from = date.replace(month=month_from, day=1)
    date_to = date_from.replace(month=month_from + 2)
    date_to = date_to.replace(day=calendar.monthrange(date_to.year, date_to.month)[1])
    return date_from, date_to


def get_fiscal_year[D: (date, datetime)](
    date: D, day: int = 31, month: int = 12
) -> tuple[D, D]:

    def fix_day(year: int, month: int, day: int) -> int:
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
        date_to += relativedelta(years=1)
        day = fix_day(date_to.year, date_to.month, date_to.day)
        date_to = date_to.replace(day=day)
    return date_from, date_to


_WEEKDAYS = (MO, TU, WE, TH, FR, SA, SU)

TimeUnit = Literal["minute", "hour", "day", "week", "month", "year"]

_RELATIVEDELTA_ARGUMENT: dict[TimeUnit, str] = {
    "minute": "minutes",
    "hour": "hours",
    "day": "days",
    "week": "weeks",
    "month": "months",
    "year": "years",
}

_TIME_UNIT_LABEL: dict[TimeUnit, str] = {
    "minute": "Minutes",
    "hour": "Hours",
    "day": "Days",
    "week": "Weeks",
    "month": "Months",
    "year": "Years",
}

TIME_UNIT_SELECTION: list[tuple[TimeUnit, str]] = [
    (unit, _TIME_UNIT_LABEL[unit]) for unit in _RELATIVEDELTA_ARGUMENT
]


def time_unit_selection(*units: str) -> list[tuple[TimeUnit, str]]:
    unknown = sorted(set(units) - _RELATIVEDELTA_ARGUMENT.keys())
    if unknown:
        msg = f"Not time units: {unknown}"
        raise ValueError(msg)
    keep = set(units)
    return [pair for pair in TIME_UNIT_SELECTION if pair[0] in keep]


def get_timedelta(
    qty: int,
    granularity: TimeUnit,
) -> relativedelta:
    try:
        argument = _RELATIVEDELTA_ARGUMENT[granularity]
    except KeyError:
        allowed = ", ".join(_RELATIVEDELTA_ARGUMENT)
        msg = f"Granularity must be one of {allowed}, got {granularity!r}"
        raise ValueError(msg) from None
    return relativedelta(dt1=None, dt2=None, **{argument: qty})


def start_of[D: (date, datetime)](value: D, granularity: Granularity) -> D:
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
    elif granularity == "hour" and isinstance(value, datetime):
        return datetime.combine(
            value, time.min.replace(fold=value.fold), value.tzinfo
        ).replace(hour=value.hour)
    elif isinstance(value, datetime):
        raise ValueError(
            f"Granularity must be year, quarter, month, week, day or hour for value {value}"
        )
    else:
        raise ValueError(
            f"Granularity must be year, quarter, month, week or day for value {value}"
        )

    if isinstance(value, datetime):
        assert isinstance(result, datetime)  # every branch above preserved the class
        return datetime.combine(
            result, time.min.replace(fold=result.fold), value.tzinfo
        )
    return result


def end_of[D: (date, datetime)](value: D, granularity: Granularity) -> D:
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
    elif granularity == "hour" and isinstance(value, datetime):
        return datetime.combine(
            value, time.max.replace(fold=value.fold), value.tzinfo
        ).replace(hour=value.hour)
    elif isinstance(value, datetime):
        raise ValueError(
            f"Granularity must be year, quarter, month, week, day or hour for value {value}"
        )
    else:
        raise ValueError(
            f"Granularity must be year, quarter, month, week or day for value {value}"
        )

    if isinstance(value, datetime):
        assert isinstance(result, datetime)  # every branch above preserved the class
        return datetime.combine(
            result, time.max.replace(fold=result.fold), value.tzinfo
        )
    return result


def add[D: (date, datetime)](value: D, *args: Any, **kwargs: Any) -> D:
    return value + relativedelta(*args, **kwargs)


def subtract[D: (date, datetime)](value: D, *args: Any, **kwargs: Any) -> D:
    return value - relativedelta(*args, **kwargs)


def date_range[D: (date, datetime)](
    start: D, end: D, step: relativedelta = relativedelta(months=1)
) -> Iterator[D]:
    restore_tz: tzinfo | None = None

    if isinstance(start, datetime) and isinstance(end, datetime):
        are_naive = start.tzinfo is None and end.tzinfo is None
        are_utc = start.tzinfo == utc and end.tzinfo == utc

        are_others = start.tzinfo and end.tzinfo and not are_utc

        if are_others:
            start_key = getattr(start.tzinfo, "key", None) or getattr(
                start.tzinfo, "zone", None
            )
            end_key = getattr(end.tzinfo, "key", None) or getattr(
                end.tzinfo, "zone", None
            )
            if start_key is None and end_key is None:
                mismatched = start.utcoffset() != end.utcoffset()
            else:
                mismatched = start_key != end_key
            if mismatched:
                msg = "Timezones of start argument and end argument seem inconsistent"
                raise ValueError(msg)

        if not are_naive and not are_utc and not are_others:
            msg = "Timezones of start argument and end argument mismatch"
            raise ValueError(msg)

        if not are_naive:
            restore_tz = start.tzinfo
            start = start.replace(tzinfo=None)
            end = end.replace(tzinfo=None)

    elif isinstance(start, date) and isinstance(end, date):
        if type(start + step) is not type(start):
            msg = "the step interval must add only entire days"
            raise ValueError(msg)
    else:
        msg = "start/end should be both date or both datetime type"
        raise ValueError(msg)

    if start > end:
        msg = "start > end, start date must be before end"
        raise ValueError(msg)

    if start >= start + step:
        msg = "Looks like step is null or negative"
        raise ValueError(msg)

    while start <= end:
        if restore_tz is not None and isinstance(start, datetime):
            yield start.replace(tzinfo=restore_tz)
        else:
            yield start
        start += step


def get_intervals_hours(intervals: Iterable[tuple[datetime, datetime, Any]]) -> float:
    return sum(
        (interval[1] - interval[0]).total_seconds() / 3600 for interval in intervals
    )


def weeknumber(
    locale: babel.Locale, date: date, first_week_day: int | None = None
) -> tuple[int, int]:
    if first_week_day is None:
        first_week_day = locale.first_week_day
    if first_week_day == 0 and locale.min_week_days == 4:
        return date.isocalendar()[:2]

    delta = relativedelta(weekday=_WEEKDAYS[first_week_day](-1))
    fdny = date.replace(year=date.year + 1, month=1, day=1) - delta
    if date >= fdny:
        return date.year + 1, 1

    fdow = date.replace(month=1, day=1) - delta
    doy = (date - fdow).days

    return date.year, (doy // 7 + 1)


def weekstart(locale: babel.Locale, date: date) -> date:
    return date + relativedelta(weekday=_WEEKDAYS[locale.first_week_day](-1))


def weekend(locale: babel.Locale, date: date) -> date:
    return weekstart(locale, date) + relativedelta(days=6)


real_time = _time.time
real_cpu_time = _time.thread_time
real_datetime_now = datetime.now


# Two shapes of schedule. A cadence is every N units from a start: below a day
# it steps exact elapsed time, from a day up it steps local wall time, so a
# daily 02:00 job stays at 02:00 across a DST change. An anchored schedule is
# fixed points inside a period, and a day past the end of a short month is
# clamped to its last day -- what leave accrual has always done, and what
# iCalendar's BYMONTHDAY does not: it skips the month instead.
#
# An anchor's occurrence is a boundary: the period it closes ends at the start of
# that day. A last-day anchor is the one exception to how a day is named. Its
# boundary is the first day of the following month, so the period it closes is
# the whole calendar month, but the day it names is the month's last day, which
# anchor_day returns.

_EXACT_UNITS: dict[TimeUnit, str] = {"minute": "minutes", "hour": "hours"}
_ANCHOR_UNITS = frozenset({"day", "week", "month", "year"})


def next_after[D: (date, datetime)](
    start: D,
    after: D,
    interval: int,
    unit: TimeUnit,
    tz: tzinfo | None = None,
) -> D:
    return next(occurrences_after(start, after, interval, unit, tz))


def occurrences_after[D: (date, datetime)](
    start: D,
    after: D,
    interval: int,
    unit: TimeUnit,
    tz: tzinfo | None = None,
) -> Iterator[D]:
    if interval <= 0:
        msg = f"interval must be positive, got {interval}"
        raise ValueError(msg)
    if unit in _EXACT_UNITS:
        step = timedelta(**{_EXACT_UNITS[unit]: interval})
        k = 0 if start > after else (after - start) // step + 1
        while True:
            yield start + k * step
            k += 1

    # Each occurrence is start + k units, never the previous one + 1 unit: a
    # series started on the 31st lands on the 28th in February and back on the
    # 31st in March, instead of staying on the 28th for good.
    delta = get_timedelta(interval, unit)
    local_start: date = start
    local_after: date = after
    if tz is not None and isinstance(start, datetime) and isinstance(after, datetime):
        local_start = start.replace(tzinfo=UTC).astimezone(tz)
        local_after = after.replace(tzinfo=UTC).astimezone(tz)
    # One period short of the whole periods elapsed is strictly before `after`
    # whatever a short month clamps, so the walk starts there instead of at the
    # first occurrence of a series that may be years old.
    k = max(0, _count_elapsed_units(local_start, local_after, unit) // interval - 1)
    while True:
        candidate = local_start + delta * k
        if tz is not None and isinstance(candidate, datetime):
            candidate = candidate.astimezone(UTC).replace(tzinfo=None)
        if candidate > after:
            yield cast("D", candidate)
        k += 1


def _count_elapsed_units(start: date, moment: date, unit: TimeUnit) -> int:
    if unit == "year":
        return moment.year - start.year
    if unit == "month":
        return (moment.year - start.year) * 12 + moment.month - start.month
    days = moment.toordinal() - start.toordinal()
    return days // 7 if unit == "week" else days


@dataclass(frozen=True, slots=True)
class Anchor:
    day: int | None = None
    month: int | None = None
    weekday: int | None = None
    last_day: bool = False


def _clamped(year: int, month: int, day: int) -> date:
    return date(year, month, min(day, calendar.monthrange(year, month)[1]))


def _period_occurrences(
    reference: date, unit: str, anchors: Sequence[Anchor], shift: int
) -> list[date]:
    if unit == "week":
        monday = (
            reference - timedelta(days=reference.weekday()) + timedelta(weeks=shift)
        )
        return sorted({monday + timedelta(days=_require(a.weekday)) for a in anchors})
    if unit == "month":
        first = reference.replace(day=1) + relativedelta(months=shift)
        return sorted({_month_occurrence(first.year, first.month, a) for a in anchors})
    year = reference.year + shift
    return sorted({_month_occurrence(year, _require(a.month), a) for a in anchors})


def _month_occurrence(year: int, month: int, anchor: Anchor) -> date:
    if anchor.last_day:
        return date(year, month, 1) + relativedelta(months=1)
    return _clamped(year, month, _require(anchor.day))


def _require(value: int | None) -> int:
    if value is None:
        msg = "anchor is missing the component its period needs"
        raise ValueError(msg)
    return value


def _check_anchored(unit: str, anchors: Sequence[Anchor]) -> None:
    if unit not in _ANCHOR_UNITS:
        msg = f"anchored schedules have a day, week, month or year period, not {unit!r}"
        raise ValueError(msg)
    if unit != "day" and not anchors:
        msg = f"a {unit} schedule needs at least one anchor"
        raise ValueError(msg)


def next_anchor(after: date, unit: str, anchors: Sequence[Anchor]) -> date:
    _check_anchored(unit, anchors)
    if unit == "day":
        return after + timedelta(days=1)
    for shift in (0, 1):
        for occurrence in _period_occurrences(after, unit, anchors, shift):
            if occurrence > after:
                return occurrence
    msg = "an anchored schedule has an occurrence in every period"
    raise AssertionError(msg)


def previous_anchor(on: date, unit: str, anchors: Sequence[Anchor]) -> date:
    _check_anchored(unit, anchors)
    if unit == "day":
        return on
    for shift in (0, -1):
        for occurrence in reversed(_period_occurrences(on, unit, anchors, shift)):
            if occurrence <= on:
                return occurrence
    msg = "an anchored schedule has an occurrence in every period"
    raise AssertionError(msg)


def anchor_day(boundary: date, unit: str, anchors: Sequence[Anchor]) -> date:
    for anchor in anchors:
        if (
            anchor.last_day
            and boundary.day == 1
            and (unit == "month" or boundary.month == _require(anchor.month) % 12 + 1)
        ):
            return boundary - timedelta(days=1)
    return boundary
