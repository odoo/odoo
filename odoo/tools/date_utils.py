# -*- coding: utf-8 -*-
import calendar
import math
from datetime import date, datetime, time
from typing import TypeVar, Tuple, Iterator

import pytz
from dateutil.relativedelta import relativedelta

from .func import lazy
from odoo.loglevels import ustr

Dateish = TypeVar('Dateish', date, datetime)

def get_month(date: Dateish) -> Tuple[Dateish, Dateish]:
    """ Compute the month date(ish) range on which the 'date' parameter belongs to.
    """
    date_from = date.replace(day=1)
    date_to = date.replace(day=calendar.monthrange(date.year, date.month)[1])
    return date_from, date_to


def get_quarter_number(date: date) -> int:
    """ Get the number of the quarter to which the 'date' parameter belongs.

    :return: an integer between 1 and 4
    """
    return math.ceil(date.month / 3)


def get_quarter(date: Dateish) -> Tuple[Dateish, Dateish]:
    """ Compute the quarter dates range to which the 'date' parameter belongs.
    """
    quarter_number = get_quarter_number(date)
    month_from = ((quarter_number - 1) * 3) + 1
    date_from = date.replace(month=month_from, day=1)
    date_to = (date_from + relativedelta(months=2))
    date_to = date_to.replace(day=calendar.monthrange(date_to.year, date_to.month)[1])
    return date_from, date_to


def get_fiscal_year(date: Dateish, day: int = 31, month: int = 12) -> Tuple[Dateish, Dateish]:
    """ Compute the fiscal year dates range to which the 'date' parameter belongs.

    A fiscal year is the period used by governments for accounting purposes and
    vary between countries. This variability can be provided through the ``day``
    and ``month`` parameters.

    By default, calling this method with only one parameter gives the calendar
    year because the ending date of the fiscal year is set to the YYYY-12-31.

    :param date: reference date for the fiscal year.
    :param day: The day of month the fiscal year ends.
    :param month: The month of year the fiscal year ends.
    """
    max_day = calendar.monthrange(date.year, month)[1]
    date_to = date.replace(month=month, day=min(day, max_day))

    # Force at 29 February instead of 28 in case of leap year.
    if date_to.month == 2 and date_to.day == 28 and max_day == 29:
        date_to = date.replace(month=2, day=29)

    if date <= date_to:
        date_from = date_to - relativedelta(years=1)
        max_day = calendar.monthrange(date_from.year, date_from.month)[1]

        # Force at 29 February instead of 28 in case of leap year.
        if date_from.month == 2 and date_from.day == 28 and max_day == 29:
            date_from = date.replace(month=2, day=29)

        date_from += relativedelta(days=1)
    else:
        date_from = date_to + relativedelta(days=1)
        max_day = calendar.monthrange(date_to.year + 1, date_to.month)[1]
        date_to = date.replace(year=date.year + 1, month=month, day=min(day, max_day))

        # Force at 29 February instead of 28 in case of leap year.
        if date_to.month == 2 and date_to.day == 28 and max_day == 29:
            date_to += relativedelta(days=1)
    return date_from, date_to


# typing.Literal requires 3.8+
def get_timedelta(qty: int, granularity: str) -> relativedelta:
    """ Helper to get a `relativedelta` object for the given quantity and interval unit.

    :param qty: the number of unit to apply on the delta to return.
    :param granularity: Type of period in string, can be year, quarter, month, week, day or hour.
    """
    switch = {
        'hour': relativedelta(hours=qty),
        'day': relativedelta(days=qty),
        'week': relativedelta(weeks=qty),
        'month': relativedelta(months=qty),
        'year': relativedelta(years=qty),
    }
    return switch[granularity]


def start_of(value: Dateish, granularity: str) -> Dateish:
    """Get start of a time period from a date or a datetime.

    :param value: the reference date
    :param granularity: type of period in string, can be year, quarter, month, week, day or hour (for datetimes only).
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


def end_of(value: Dateish, granularity: str) -> Dateish:
    """ Get end of a time period from a date or a datetime.

    :param value: reference date
    :param granularity: Type of period in string, can be year, quarter, month, week, day or hour (for datetimes only).
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
        result = value + relativedelta(days=6-calendar.weekday(value.year, value.month, value.day))
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


def add(value: Dateish, *args, **kwargs) -> Dateish:
    """ Convenience to get the offset of ``value`` by a :class:`relativedelta`.

    :param value: the reference date
    :param args: positional args to pass directly to :class:`relativedelta`.
    :param kwargs: keyword args to pass directly to :class:`relativedelta`.
    """
    return value + relativedelta(*args, **kwargs)


def subtract(value: Dateish, *args, **kwargs) -> Dateish:
    """ Convenience to get the negative offset of a ``value`` by a :class:`relativedelta`.

    :param value: the reference date
    :param args: positional args to pass directly to :class:`relativedelta`.
    :param kwargs: keyword args to pass directly to :class:`relativedelta`.
    """
    return value - relativedelta(*args, **kwargs)

def json_default(obj):
    """
    Properly serializes date and datetime objects.
    """
    from odoo import fields
    if isinstance(obj, datetime):
        return fields.Datetime.to_string(obj)
    if isinstance(obj, date):
        return fields.Date.to_string(obj)
    if isinstance(obj, lazy):
        return obj._value
    return ustr(obj)


def date_range(start: Dateish, end: Dateish, step: relativedelta = relativedelta(months=1)) -> Iterator[Dateish]:
    """Date range generator with a step interval.

    :param start: beginning date of the range.
    :param end: ending date of the range.
    :param step: interval of the range.
    :return: a range of datetime from start to end.
    """
    if isinstance(start, datetime) and isinstance(end, datetime):
        are_naive = start.tzinfo is None and end.tzinfo is None
        are_utc = start.tzinfo == pytz.utc and end.tzinfo == pytz.utc

        # Cases with miscellenous timezone are more complexe because of DST.
        are_others = start.tzinfo and end.tzinfo and not are_utc

        if are_others and start.tzinfo.zone != end.tzinfo.zone:
            raise ValueError("Timezones of start argument and end argument seem inconsistent")

        if not are_naive and not are_utc and not are_others:
            raise ValueError("Timezones of start argument and end argument mismatch")

        dt = start.replace(tzinfo=None)
        end_dt = end.replace(tzinfo=None)
        post_process = start.tzinfo.localize if start.tzinfo else lambda dt: dt

    elif isinstance(start, date) and isinstance(end, date):
        dt, end_dt = start, end
        post_process = lambda dt: dt

    else:
        raise ValueError("start/end should be both date or both datetime type")

    if start > end:
        raise ValueError("start > end, start date must be before end")

    if start == start + step:
        raise ValueError(f"the range step must be non-zero (got {step})")

    while dt <= end_dt:
        yield post_process(dt)
        dt = dt + step
