# -*- coding: utf-8 -*-

import math
import calendar
import json
from datetime import date, datetime, time

from dateutil.relativedelta import relativedelta
from odoo.tools.func import monkey_patch


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
    if date <= date_to:
        date_from = date_to - relativedelta(years=1)
        date_from += relativedelta(days=1)
    else:
        date_from = date_to + relativedelta(days=1)
        max_day = calendar.monthrange(date_to.year + 1, date_to.month)[1]
        date_to = type(date)(date.year + 1, month, min(day, max_day))
    return date_from, date_to


def start_of(self, value, granularity):
    """
    Get start of a time period from a date or a datetime.

    :param value: Initial date or datetime
    :param granularity: Type of period in string, can be year, quarter, month, day ou hour
    """
    is_datetime = isinstance(value, datetime)
    if granularity == "year":
        result = value.replace(month=1, day=1)
    elif granularity == "quarter":
        month = int((value.month - 1)/3) * 3 + 1
        result = value.replace(month=month, day=1)
    elif granularity == "month":
        result = value.replace(day=1)
    elif granularity == "day":
        result = value
    elif granularity == "hour" and is_datetime:
        return datetime.combine(value, time.min).replace(hour=value.hour)
    elif is_datetime:
        raise ValueError("Granularity must be year, quarter, month, day or hour for value %s" % value)
    else:
        raise ValueError("Granularity must be year, quarter, month or day for value %s" % value)

    return datetime.combine(result, time.min) if is_datetime else result

def end_of(self, value, granularity):
    """
    Get end of a time period from a date or a datetime.

    :param value: Initial date or datetime
    :param granularity: Type of period in string, can be year, quarter, month, day ou hour
    """
    is_datetime = isinstance(value, datetime)
    if granularity == "year":
        result = value.replace(month=12, day=31)
    elif granularity == "quarter":
        result = value.replace(month=int((value.month - 1)/3 + 1)*3)
        result = value + relativedelta(day=1, months=1, days=-1)
    elif granularity == "month":
        result = value + relativedelta(day=1, months=1, days=-1)
    elif granularity == "day":
        result = value
    elif granularity == "hour" and is_datetime:
        return datetime.combine(value, time.max).replace(hour=value.hour)
    elif is_datetime:
        raise ValueError("Granularity must be year, quarter, month, day or hour for value %s" % value)
    else:
        raise ValueError("Granularity must be year, quarter, month or day for value %s" % value)

    return datetime.combine(result, time.max) if is_datetime else result

@monkey_patch(json.JSONEncoder)
def default(self, o):
    if isinstance(o, date):
        return str(o)
    return default.super(self, o)
