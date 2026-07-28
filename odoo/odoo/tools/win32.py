# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import locale
import time
import datetime

if not hasattr(locale, 'D_FMT'):
    locale.D_FMT = 1

if not hasattr(locale, 'T_FMT'):
    locale.T_FMT = 2

if not hasattr(locale, 'nl_langinfo'):
    def nl_langinfo(param):
        if param == locale.D_FMT:
            val = time.strptime('30/12/2004', '%d/%m/%Y')
            dt = datetime.datetime(*val[:-2])
            format_date = dt.strftime('%x')
            for x, y in [('30', '%d'),('12', '%m'),('2004','%Y'),('04', '%Y')]:
                format_date = format_date.replace(x, y)
            return format_date
        if param == locale.T_FMT:
            val = time.strptime('13:24:56', '%H:%M:%S')
            dt = datetime.datetime(*val[:-2])
            format_time = dt.strftime('%X')
            for x, y in [('13', '%H'),('24', '%M'),('56','%S')]:
                format_time = format_time.replace(x, y)
            return format_time
    locale.nl_langinfo = nl_langinfo
