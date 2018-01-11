# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.     
#
##############################################################################

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

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
