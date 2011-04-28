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

""" We assume that, just like the OpenERP server, the python part of the client
 doesn't need to handle timezone-aware datetimes, this could be changed in the future. """

import datetime

DEFAULT_SERVER_DATE_FORMAT = "%Y-%m-%d"
DEFAULT_SERVER_TIME_FORMAT = "%H:%M:%S"
DEFAULT_SERVER_DATETIME_FORMAT = "%s %s" % (
    DEFAULT_SERVER_DATE_FORMAT,
    DEFAULT_SERVER_TIME_FORMAT)

def parse_datetime(str):
    if not str:
        return str
    return datetime.datetime.strptime(str, DEFAULT_SERVER_DATETIME_FORMAT)

def parse_date(str):
    if not str:
        return str
    return datetime.datetime.strptime(str, DEFAULT_SERVER_DATE_FORMAT).date()

def parse_time(str):
    if not str:
        return str
    return datetime.datetime.strptime(str, DEFAULT_SERVER_TIME_FORMAT).time()

def format_datetime(obj):
    if not obj:
        return False
    return obj.strftime(DEFAULT_SERVER_DATETIME_FORMAT)

def format_date(obj):
    if not obj:
        return False
    return obj.strftime(DEFAULT_SERVER_DATE_FORMAT)

def format_time(obj):
    if not obj:
        return False
    return obj.strftime(DEFAULT_SERVER_TIME_FORMAT)
