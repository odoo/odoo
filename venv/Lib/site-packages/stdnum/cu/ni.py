# ni.py - functions for handling Cuban identity card numbers
# coding: utf-8
#
# Copyright (C) 2019 Arthur de Jong
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

"""NI (Número de identidad, Cuban identity card numbers).

Número de carnet de identidad is the Cuban national identifier that is
assigned to residents. The number consists of 11 digits and include the date
of birth of the person and gender.

More information:

* https://www.postdata.club/issues/201609/es-usted-unico-en-cuba.html

>>> validate('91021027775')
'91021027775'
>>> validate('9102102777A')
Traceback (most recent call last):
    ...
InvalidFormat: ...
>>> get_birth_date('91021027775')
datetime.date(1991, 2, 10)
>>> get_gender('91021027775')
'F'
>>> get_birth_date('72062506561')
datetime.date(1972, 6, 25)
>>> get_gender('72062506561')
'M'
>>> get_birth_date('85020291531')
datetime.date(1885, 2, 2)
>>> get_birth_date('02023061531')
Traceback (most recent call last):
    ...
InvalidComponent: ...
"""

import datetime

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips
    surrounding whitespace and separation dash."""
    return clean(number, ' ').strip()


def get_birth_date(number):
    """Split the date parts from the number and return the date of birth."""
    number = compact(number)
    year = int(number[0:2])
    month = int(number[2:4])
    day = int(number[4:6])
    if number[6] == '9':
        year += 1800
    elif '0' <= number[6] <= '5':
        year += 1900
    else:
        year += 2000
    try:
        return datetime.date(year, month, day)
    except ValueError:
        raise InvalidComponent()


def get_gender(number):
    """Get the gender (M/F) from the person's NI."""
    number = compact(number)
    if int(number[9]) % 2:
        return 'F'
    else:
        return 'M'


def validate(number):
    """Check if the number is a valid NI. This checks the length, formatting
    and check digit."""
    number = compact(number)
    if len(number) != 11:
        raise InvalidLength()
    if not isdigits(number):
        raise InvalidFormat()
    get_birth_date(number)
    return number


def is_valid(number):
    """Check if the number is a valid NI."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False
