# -*- coding: utf-8 -*-

import math
import calendar

from dateutil.relativedelta import relativedelta


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
