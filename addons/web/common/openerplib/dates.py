# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (C) Stephane Wirtel
# Copyright (C) 2011 Nicolas Vanhoren
# Copyright (C) 2011 OpenERP s.a. (<http://openerp.com>).
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the <organization> nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
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

