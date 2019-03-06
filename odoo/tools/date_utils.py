# -*- coding: utf-8 -*-
import math
import calendar
from datetime import date, datetime, time
import pytz
from dateutil.relativedelta import relativedelta
from . import ustr


def get_month(date):
    ''' Compute the month dates range on which the 'date' parameter belongs to.

    :param date: A datetime.datetime or datetime.date object.
    :return: A tuple (date_from, date_to) having the same object type as the 'date' parameter.
    '''
    date_from = type(date)(date.year, date.month, 1)
    date_to = type(date)(date.year, date.month, calendar.monthrange(date.year, date.month)[1])
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
    date_from = type(date)(date.year, month_from, 1)
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
    max_day = calendar.monthrange(date.year, month)[1]
    date_to = type(date)(date.year, month, min(day, max_day))

    # Force at 29 February instead of 28 in case of leap year.
    if date_to.month == 2 and date_to.day == 28 and max_day == 29:
        date_to = type(date)(date.year, 2, 29)

    if date <= date_to:
        date_from = date_to - relativedelta(years=1)
        max_day = calendar.monthrange(date_from.year, date_from.month)[1]

        # Force at 29 February instead of 28 in case of leap year.
        if date_from.month == 2 and date_from.day == 28 and max_day == 29:
            date_from = type(date)(date_from.year, 2, 29)

        date_from += relativedelta(days=1)
    else:
        date_from = date_to + relativedelta(days=1)
        max_day = calendar.monthrange(date_to.year + 1, date_to.month)[1]
        date_to = type(date)(date.year + 1, month, min(day, max_day))
    return date_from, date_to


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
    if isinstance(obj, date):
        if isinstance(obj, datetime):
            return fields.Datetime.to_string(obj)
        return fields.Date.to_string(obj)
    return ustr(obj)

def date_range(start, end, step=relativedelta(months=1)):
    """Date range generator with a step interval.

    :param start datetime: begining date of the range.
    :param end datetime: ending date of the range.
    :param step relativedelta: interval of the range.
    :return: a range of datetime from start to end.
    :rtype: Iterator[datetime]
    """

    are_naive = start.tzinfo is None and end.tzinfo is None
    are_utc = start.tzinfo == pytz.utc and end.tzinfo == pytz.utc

    # Cases with miscellenous timezone are more complexe because of DST.
    are_others = start.tzinfo and end.tzinfo and not are_utc

    if are_others:
        if start.tzinfo.zone != end.tzinfo.zone:
            raise ValueError("Timezones of start argument and end argument seem inconsistent")

    if not are_naive and not are_utc and not are_others:
        raise ValueError("Timezones of start argument and end argument mismatch")

    if start > end:
        raise ValueError("start > end, start date must be before end")

    if start == start + step:
        raise ValueError("Looks like step is null")

    if start.tzinfo:
        localize = start.tzinfo.localize
    else:
        localize = lambda dt: dt

    dt = start.replace(tzinfo=None)
    end = end.replace(tzinfo=None)
    while dt <= end:
        yield localize(dt)
        dt = dt + step
