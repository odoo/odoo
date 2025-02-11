# -*- coding: utf-8 -*-
import math
import calendar
from datetime import date, datetime, time
import pytz
from dateutil.relativedelta import relativedelta

from .func import lazy
from odoo.loglevels import ustr


def date_type(value):
    ''' Return either the datetime.datetime class or datetime.date type whether `value` is a datetime or a date.

    :param value: A datetime.datetime or datetime.date object.
    :return: datetime.datetime or datetime.date
    '''
    return datetime if isinstance(value, datetime) else date


def get_month(date):
    ''' Compute the month dates range on which the 'date' parameter belongs to.

    :param date: A datetime.datetime or datetime.date object.
    :return: A tuple (date_from, date_to) having the same object type as the 'date' parameter.
    '''
    date_from = date_type(date)(date.year, date.month, 1)
    date_to = date_type(date)(date.year, date.month, calendar.monthrange(date.year, date.month)[1])
    return date_from, date_to


def get_quarter_number(date):
    ''' Get the number of the quarter on which the 'date' parameter belongs to.

    :param date: A datetime.datetime or datetime.date object.
    :return: A [1-4] integer.
    '''
    return math.ceil(date.month / 3)


def get_quarter(date):
    ''' Compute the quarter dates range on which the 'date' parameter belongs to.

    :param date: A datetime.datetime or datetime.date object.
    :return: A tuple (date_from, date_to) having the same object type as the 'date' parameter.
    '''
    quarter_number = get_quarter_number(date)
    month_from = ((quarter_number - 1) * 3) + 1
    date_from = date_type(date)(date.year, month_from, 1)
    date_to = (date_from + relativedelta(months=2))
    date_to = date_to.replace(day=calendar.monthrange(date_to.year, date_to.month)[1])
    return date_from, date_to


def get_fiscal_year(date, day=31, month=12):
    ''' Compute the fiscal year dates range on which the 'date' parameter belongs to.
    A fiscal year is the period used by governments for accounting purposes and vary between countries.
    By default, calling this method with only one parameter gives the calendar year because the ending date of the
    fiscal year is set to the YYYY-12-31.
    :param date:    A datetime.datetime or datetime.date object.
    :param day:     The day of month the fiscal year ends.
    :param month:   The month of year the fiscal year ends.
    :return: A tuple (date_from, date_to) having the same object type as the 'date' parameter.
    '''

    def fix_day(year, month, day):
        max_day = calendar.monthrange(year, month)[1]
        if month == 2 and day in (28, max_day):
            return max_day
        return min(day, max_day)

    day = fix_day(date.year, month, day)
    date_to = date_type(date)(date.year, month, day)

    if date <= date_to:
        date_from = date_to - relativedelta(years=1)
        day = fix_day(date_from.year, date_from.month, date_from.day)
        date_from = date_type(date)(date_from.year, date_from.month, day)
        date_from += relativedelta(days=1)
    else:
        date_from = date_to + relativedelta(days=1)
        date_to = date_to + relativedelta(years=1)
        day = fix_day(date_to.year, date_to.month, date_to.day)
        date_to = date_type(date)(date_to.year, date_to.month, day)
    return date_from, date_to


def get_timedelta(qty, granularity):
    """
        Helper to get a `relativedelta` object for the given quantity and interval unit.
        :param qty: the number of unit to apply on the timedelta to return
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


def start_of(value, granularity):
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


def end_of(value, granularity):
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


def add(value, *args, **kwargs):
    """
    Return the sum of ``value`` and a :class:`relativedelta`.

    :param value: initial date or datetime.
    :param args: positional args to pass directly to :class:`relativedelta`.
    :param kwargs: keyword args to pass directly to :class:`relativedelta`.
    :return: the resulting date/datetime.
    """
    return value + relativedelta(*args, **kwargs)


def subtract(value, *args, **kwargs):
    """
    Return the difference between ``value`` and a :class:`relativedelta`.

    :param value: initial date or datetime.
    :param args: positional args to pass directly to :class:`relativedelta`.
    :param kwargs: keyword args to pass directly to :class:`relativedelta`.
    :return: the resulting date/datetime.
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


def date_range(start, end, step=relativedelta(months=1)):
    """Date range generator with a step interval.

    :param date | datetime start: beginning date of the range.
    :param date | datetime end: ending date of the range.
    :param relativedelta step: interval of the range.
    :return: a range of datetime from start to end.
    :rtype: Iterator[datetime]
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
        raise ValueError("Looks like step is null")

    while dt <= end_dt:
        yield post_process(dt)
        dt = dt + step
