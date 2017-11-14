# -*- coding: utf-8 -*-

import math
import calendar

from dateutil.relativedelta import relativedelta


def get_month(date):
    date_from = type(date)(date.year, date.month, 1)
    date_to = type(date)(date.year, date.month, calendar.monthrange(date.year, date.month)[1])
    return date_from, date_to


def get_quarter_number(date):
    return math.ceil(date.month / 3)


def get_quarter(date):
    quarter_number = get_quarter_number(date)
    month_from = ((quarter_number - 1) * 3) + 1
    date_from = type(date)(date.year, month_from, 1)
    date_to = (date_from + relativedelta(months=2))
    date_to = date_to.replace(day=calendar.monthrange(date_to.year, date_to.month)[1])
    return date_from, date_to


def get_year(date):
    date_from = type(date)(date.year, 1, 1)
    date_to = type(date)(date.year, 12, 31)
    return date_from, date_to


def get_fiscal_year(date, day, month):
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
