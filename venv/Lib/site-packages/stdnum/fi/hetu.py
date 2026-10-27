# hetu.py - functions for handling Finnish personal identity codes
# coding: utf-8
#
# Copyright (C) 2011 Jussi Judin
# Copyright (C) 2012, 2013 Arthur de Jong
# Copyright (C) 2020 Aleksi Hoffman
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301 USA

"""HETU (Henkilötunnus, Finnish personal identity code).

Module for handling Finnish personal identity codes (HETU, Henkilötunnus).
See https://www.vaestorekisterikeskus.fi/default.aspx?id=45 for checksum
calculation details and https://tarkistusmerkit.teppovuori.fi/tarkmerk.htm#hetu1
for historical details.

>>> validate('131052-308T')
'131052-308T'
>>> validate('131052-308U')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> validate('310252-308Y')
Traceback (most recent call last):
    ...
InvalidComponent: ...
>>> compact('131052a308t')
'131052A308T'
"""

import datetime
import re

from stdnum.exceptions import *
from stdnum.util import clean


_century_codes = {
    '+': 1800,
    '-': 1900,
    'A': 2000,
}

# Finnish personal identity codes are composed of date part, century
# indicating sign, individual number and control character.
# ddmmyyciiiC
_hetu_re = re.compile(r'^(?P<day>[0123]\d)(?P<month>[01]\d)(?P<year>\d\d)'
                      r'(?P<century>[-+A])(?P<individual>\d\d\d)'
                      r'(?P<control>[0-9ABCDEFHJKLMNPRSTUVWXY])$')


def compact(number):
    """Convert the HETU to the minimal representation. This strips
    surrounding whitespace and converts it to upper case."""
    return clean(number, '').upper().strip()


def _calc_checksum(number):
    return '0123456789ABCDEFHJKLMNPRSTUVWXY'[int(number) % 31]


def validate(number, allow_temporary=False):
    """Check if the number is a valid HETU. It checks the format, whether a
    valid date is given and whether the check digit is correct. Allows
    temporary identifier range for individuals (900-999) if allow_temporary
    is True.
    """
    number = compact(number)
    match = _hetu_re.search(number)
    if not match:
        raise InvalidFormat()
    day = int(match.group('day'))
    month = int(match.group('month'))
    year = int(match.group('year'))
    century = _century_codes[match.group('century')]
    individual = int(match.group('individual'))
    # check if birth date is valid
    try:
        datetime.date(century + year, month, day)
    except ValueError:
        raise InvalidComponent()
    # for historical reasons individual IDs start from 002
    if individual < 2:
        raise InvalidComponent()
    # this range is for temporary identifiers
    if 900 <= individual <= 999 and not allow_temporary:
        raise InvalidComponent()
    checkable_number = '%02d%02d%02d%03d' % (day, month, year, individual)
    if match.group('control') != _calc_checksum(checkable_number):
        raise InvalidChecksum()
    return number


def is_valid(number, allow_temporary=False):
    """Check if the number is a valid HETU."""
    try:
        return bool(validate(number, allow_temporary))
    except ValidationError:
        return False


# This is here just for completeness as there are no different length forms
# of Finnish personal identity codes:
format = compact
