# nid.py - functions for handling Mauritian national ID numbers
# coding: utf-8
#
# Copyright (C) 2018 Arthur de Jong
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

"""ID number (Mauritian national identifier).

The Mauritian national ID number is a unique 14 alphanumeric identifier
assigned at birth to identify individuals. It is displayed on the National
Identity Card.

The number consists of one alphabetic character and thirteen digits:

* the first character of the person's surname at birth
* 2 digits for day of birth
* 2 digits for month of birth
* 2 digits for year of birth
* 6 digit unique id
* a check digit

More information:

* https://mnis.govmu.org/English/ID%20Card/Pages/default.aspx
"""

import datetime
import re

from stdnum.exceptions import *
from stdnum.util import clean


_nid_re = re.compile('^[A-Z][0-9]+[0-9A-Z]$')


# characters used for checksum calculation
_alphabet = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'


def compact(number):
    """Convert the number to the minimal representation. This strips
    surrounding whitespace and separation dash."""
    return clean(number, ' ').upper().strip()


def calc_check_digit(number):
    """Calculate the check digit for the number."""
    check = sum((14 - i) * _alphabet.index(n)
                for i, n in enumerate(number[:13]))
    return _alphabet[(17 - check) % 17]


def _get_date(number):
    """Convert the part of the number that represents a date into a
    datetime. Note that the century may be incorrect."""
    day = int(number[1:3])
    month = int(number[3:5])
    year = int(number[5:7])
    try:
        return datetime.date(year + 2000, month, day)
    except ValueError:
        raise InvalidComponent()


def validate(number):
    """Check if the number is a valid ID number."""
    number = compact(number)
    if len(number) != 14:
        raise InvalidLength()
    if not _nid_re.match(number):
        raise InvalidFormat()
    if calc_check_digit(number) != number[-1]:
        raise InvalidChecksum()
    _get_date(number)
    return number


def is_valid(number):
    """Check if the number provided is a valid RFC."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False
