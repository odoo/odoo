##############################################################################
# Copyright 2009, Gerhard Weis
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#  * Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#  * Neither the name of the authors nor the names of its contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT
##############################################################################
'''
This module defines a method to parse an ISO 8601:2004 date time string.

For this job it uses the parse_date and parse_time methods defined in date
and time module.
'''
from datetime import datetime

from isodate.isostrf import strftime
from isodate.isostrf import DATE_EXT_COMPLETE, TIME_EXT_COMPLETE, TZ_EXT
from isodate.isodates import parse_date
from isodate.isoerror import ISO8601Error
from isodate.isotime import parse_time


def parse_datetime(datetimestring):
    '''
    Parses ISO 8601 date-times into datetime.datetime objects.

    This function uses parse_date and parse_time to do the job, so it allows
    more combinations of date and time representations, than the actual
    ISO 8601:2004 standard allows.
    '''
    try:
        datestring, timestring = datetimestring.split('T')
    except ValueError:
        raise ISO8601Error("ISO 8601 time designator 'T' missing. Unable to"
                           " parse datetime string %r" % datetimestring)
    tmpdate = parse_date(datestring)
    tmptime = parse_time(timestring)
    return datetime.combine(tmpdate, tmptime)


def datetime_isoformat(tdt, format=DATE_EXT_COMPLETE + 'T' +
                       TIME_EXT_COMPLETE + TZ_EXT):
    '''
    Format datetime strings.

    This method is just a wrapper around isodate.isostrf.strftime and uses
    Extended-Complete as default format.
    '''
    return strftime(tdt, format)
