# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#    Copyright (C) 2010 OpenERP s.a. (<http://openerp.com>).
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

import datetime

DEFAULT_SERVER_DATE_FORMAT = "%Y-%m-%d"
DEFAULT_SERVER_TIME_FORMAT = "%H:%M:%S"
DEFAULT_SERVER_DATETIME_FORMAT = "%s %s" % (
    DEFAULT_SERVER_DATE_FORMAT,
    DEFAULT_SERVER_TIME_FORMAT)

def str_to_datetime(str):
    """
    Converts a string to a datetime object using OpenERP's
    datetime string format (exemple: '2011-12-01 15:12:35').
    
    No timezone information is added, the datetime is a naive instance, but
    according to OpenERP 6.1 specification the timezone is always UTC.
    """
    if not str:
        return str
    return datetime.datetime.strptime(str, DEFAULT_SERVER_DATETIME_FORMAT)

def str_to_date(str):
    """
    Converts a string to a date object using OpenERP's
    date string format (exemple: '2011-12-01').
    """
    if not str:
        return str
    return datetime.datetime.strptime(str, DEFAULT_SERVER_DATE_FORMAT).date()

def str_to_time(str):
    """
    Converts a string to a time object using OpenERP's
    time string format (exemple: '15:12:35').
    """
    if not str:
        return str
    return datetime.datetime.strptime(str, DEFAULT_SERVER_TIME_FORMAT).time()

def datetime_to_str(obj):
    """
    Converts a datetime object to a string using OpenERP's
    datetime string format (exemple: '2011-12-01 15:12:35').
    
    The datetime instance should not have an attached timezone and be in UTC.
    """
    if not obj:
        return False
    return obj.strftime(DEFAULT_SERVER_DATETIME_FORMAT)

def date_to_str(obj):
    """
    Converts a date object to a string using OpenERP's
    date string format (exemple: '2011-12-01').
    """
    if not obj:
        return False
    return obj.strftime(DEFAULT_SERVER_DATE_FORMAT)

def time_to_str(obj):
    """
    Converts a time object to a string using OpenERP's
    time string format (exemple: '15:12:35').
    """
    if not obj:
        return False
    return obj.strftime(DEFAULT_SERVER_TIME_FORMAT)
