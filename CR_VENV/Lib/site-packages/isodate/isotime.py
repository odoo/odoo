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
This modules provides a method to parse an ISO 8601:2004 time string to a
Python datetime.time instance.

It supports all basic and extended formats including time zone specifications
as described in the ISO standard.
'''
import re
from decimal import Decimal
from datetime import time

from isodate.isostrf import strftime, TIME_EXT_COMPLETE, TZ_EXT
from isodate.isoerror import ISO8601Error
from isodate.isotzinfo import TZ_REGEX, build_tzinfo

TIME_REGEX_CACHE = []
# used to cache regular expressions to parse ISO time strings.


def build_time_regexps():
    '''
    Build regular expressions to parse ISO time string.

    The regular expressions are compiled and stored in TIME_REGEX_CACHE
    for later reuse.
    '''
    if not TIME_REGEX_CACHE:
        # ISO 8601 time representations allow decimal fractions on least
        #    significant time component. Command and Full Stop are both valid
        #    fraction separators.
        #    The letter 'T' is allowed as time designator in front of a time
        #    expression.
        #    Immediately after a time expression, a time zone definition is
        #      allowed.
        #    a TZ may be missing (local time), be a 'Z' for UTC or a string of
        #    +-hh:mm where the ':mm' part can be skipped.
        # TZ information patterns:
        #    ''
        #    Z
        #    +-hh:mm
        #    +-hhmm
        #    +-hh =>
        #    isotzinfo.TZ_REGEX
        # 1. complete time:
        #    hh:mm:ss.ss ... extended format
        TIME_REGEX_CACHE.append(re.compile(r"T?(?P<hour>[0-9]{2}):"
                                           r"(?P<minute>[0-9]{2}):"
                                           r"(?P<second>[0-9]{2}"
                                           r"([,.][0-9]+)?)" + TZ_REGEX))
        #    hhmmss.ss ... basic format
        TIME_REGEX_CACHE.append(re.compile(r"T?(?P<hour>[0-9]{2})"
                                           r"(?P<minute>[0-9]{2})"
                                           r"(?P<second>[0-9]{2}"
                                           r"([,.][0-9]+)?)" + TZ_REGEX))
        # 2. reduced accuracy:
        #    hh:mm.mm ... extended format
        TIME_REGEX_CACHE.append(re.compile(r"T?(?P<hour>[0-9]{2}):"
                                           r"(?P<minute>[0-9]{2}"
                                           r"([,.][0-9]+)?)" + TZ_REGEX))
        #    hhmm.mm ... basic format
        TIME_REGEX_CACHE.append(re.compile(r"T?(?P<hour>[0-9]{2})"
                                           r"(?P<minute>[0-9]{2}"
                                           r"([,.][0-9]+)?)" + TZ_REGEX))
        #    hh.hh ... basic format
        TIME_REGEX_CACHE.append(re.compile(r"T?(?P<hour>[0-9]{2}"
                                           r"([,.][0-9]+)?)" + TZ_REGEX))
    return TIME_REGEX_CACHE


def parse_time(timestring):
    '''
    Parses ISO 8601 times into datetime.time objects.

    Following ISO 8601 formats are supported:
      (as decimal separator a ',' or a '.' is allowed)
      hhmmss.ssTZD    basic complete time
      hh:mm:ss.ssTZD  extended compelte time
      hhmm.mmTZD      basic reduced accuracy time
      hh:mm.mmTZD     extended reduced accuracy time
      hh.hhTZD        basic reduced accuracy time
    TZD is the time zone designator which can be in the following format:
              no designator indicates local time zone
      Z       UTC
      +-hhmm  basic hours and minutes
      +-hh:mm extended hours and minutes
      +-hh    hours
    '''
    isotimes = build_time_regexps()
    for pattern in isotimes:
        match = pattern.match(timestring)
        if match:
            groups = match.groupdict()
            for key, value in groups.items():
                if value is not None:
                    groups[key] = value.replace(',', '.')
            tzinfo = build_tzinfo(groups['tzname'], groups['tzsign'],
                                  int(groups['tzhour'] or 0),
                                  int(groups['tzmin'] or 0))
            if 'second' in groups:
                # round to microseconds if fractional seconds are more precise
                second = Decimal(groups['second']).quantize(Decimal('.000001'))
                microsecond = (second - int(second)) * int(1e6)
                # int(...) ... no rounding
                # to_integral() ... rounding
                return time(int(groups['hour']), int(groups['minute']),
                            int(second), int(microsecond.to_integral()),
                            tzinfo)
            if 'minute' in groups:
                minute = Decimal(groups['minute'])
                second = (minute - int(minute)) * 60
                microsecond = (second - int(second)) * int(1e6)
                return time(int(groups['hour']), int(minute), int(second),
                            int(microsecond.to_integral()), tzinfo)
            else:
                microsecond, second, minute = 0, 0, 0
            hour = Decimal(groups['hour'])
            minute = (hour - int(hour)) * 60
            second = (minute - int(minute)) * 60
            microsecond = (second - int(second)) * int(1e6)
            return time(int(hour), int(minute), int(second),
                        int(microsecond.to_integral()), tzinfo)
    raise ISO8601Error('Unrecognised ISO 8601 time format: %r' % timestring)


def time_isoformat(ttime, format=TIME_EXT_COMPLETE + TZ_EXT):
    '''
    Format time strings.

    This method is just a wrapper around isodate.isostrf.strftime and uses
    Time-Extended-Complete with extended time zone as default format.
    '''
    return strftime(ttime, format)
