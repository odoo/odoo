# -*- coding: utf-8 -*-
import calendar
import math
from datetime import date, datetime, time
from typing import Tuple, TypeVar, Literal, Iterator, Type

import babel
import pytz
from dateutil.relativedelta import relativedelta, weekdays

from .func import lazy

D = TypeVar('D', date, datetime)

__all__ = [
    'date_range',
    'get_fiscal_year',
    'get_month',
    'get_quarter',
    'get_quarter_number',
    'get_timedelta',
]

def date_type(value: D) -> Type[D]:
    ''' Return either the datetime.datetime class or datetime.date type whether `value` is a datetime or a date.

    :param value: A datetime.datetime or datetime.date object.
    :return: datetime.datetime or datetime.date
    '''
    return datetime if isinstance(value, datetime) else date


def get_month(date: D) -> Tuple[D, D]:
    ''' Compute the month dates range on which the 'date' parameter belongs to.
    '''
    return date.replace(day=1), date.replace(day=calendar.monthrange(date.year, date.month)[1])


def get_quarter_number(date: date) -> int:
    ''' Get the number of the quarter on which the 'date' parameter belongs to.
    '''
    return math.ceil(date.month / 3)


def get_quarter(date: D) -> Tuple[D, D]:
    ''' Compute the quarter dates range on which the 'date' parameter belongs to.
    '''
    quarter_number = get_quarter_number(date)
    month_from = ((quarter_number - 1) * 3) + 1
    date_from = date.replace(month=month_from, day=1)
    date_to = date_from + relativedelta(months=2)
    date_to = date_to.replace(day=calendar.monthrange(date_to.year, date_to.month)[1])
    return date_from, date_to


def get_fiscal_year(date: D, day: int = 31, month: int = 12) -> Tuple[D, D]:
    ''' Compute the fiscal year dates range on which the 'date' parameter belongs to.
    A fiscal year is the period used by governments for accounting purposes and vary between countries.
    By default, calling this method with only one parameter gives the calendar year because the ending date of the
    fiscal year is set to the YYYY-12-31.

    :param date: A date belonging to the fiscal year
    :param day:     The day of month the fiscal year ends.
    :param month:   The month of year the fiscal year ends.
    :return: The start and end dates of the fiscal year.
    '''

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


def get_timedelta(qty: int, granularity: Literal['hour', 'day', 'week', 'month', 'year']):
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


Granularity = Literal['year', 'quarter', 'month', 'week', 'day', 'hour']


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
        # FIXME: not correctly typed, and will break if the step is a fractional
        #        day: `relativedelta` will return a datetime, which can't be
        #        compared with a `date`
        dt, end_dt = start, end
        post_process = lambda dt: dt

    else:
        raise ValueError("start/end should be both date or both datetime type")

    if start > end:
        raise ValueError("start > end, start date must be before end")

    if start == start + step:
        raise ValueError("Looks like step is null")

    while dt <= end_dt:
        yield post_process(dt)
        dt = dt + step


def weeknumber(locale: babel.Locale, date: date) -> Tuple[int, int]:
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
