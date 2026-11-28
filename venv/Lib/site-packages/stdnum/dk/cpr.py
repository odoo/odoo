# cpr.py - functions for handling Danish CPR numbers
# coding: utf-8
#
# Copyright (C) 2012-2019 Arthur de Jong
# Copyright (C) 2020 Leon Sandøy
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

"""CPR (personnummer, the Danish citizen number).

The CPR is the national number to identify Danish citizens and is stored in
the Det Centrale Personregister (Civil Registration System). The number
consists of 10 digits in the format DDMMYY-SSSS where the first part
represents the birth date and the second a sequence number. The first digit
of the sequence number indicates the century.

The numbers used to validate using a checksum but since the sequence numbers
ran out this was abandoned in 2007. It is also not possible to use the
checksum only for numbers that have a birth date before that because the
numbers are also assigned to immigrants.

More information:

* https://en.wikipedia.org/wiki/Personal_identification_number_(Denmark)
* https://da.wikipedia.org/wiki/CPR-nummer
* https://cpr.dk/

>>> validate('211062-5629')
'2110625629'
>>> checksum('2110625629')
0
>>> validate('511062-5629')  # invalid date
Traceback (most recent call last):
    ...
InvalidComponent: ...
>>> validate('2110525629')
Traceback (most recent call last):
  ...
InvalidComponent: The birth date information is valid, but this person has not been born yet.
>>> get_birth_date('2110620629')
datetime.date(1962, 10, 21)
>>> format('2110625629')
'211062-5629'
"""

import datetime

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, ' -').strip()


def checksum(number):
    """Calculate the checksum. Note that the checksum isn't actually used
    any more. Valid numbers used to have a checksum of 0."""
    weights = (4, 3, 2, 7, 6, 5, 4, 3, 2, 1)
    return sum(w * int(n) for w, n in zip(weights, number)) % 11


def get_birth_date(number):
    """Split the date parts from the number and return the birth date."""
    number = compact(number)
    day = int(number[0:2])
    month = int(number[2:4])
    year = int(number[4:6])
    if number[6] in '5678' and year >= 58:
        year += 1800
    elif number[6] in '0123' or (number[6] in '49' and year >= 37):
        year += 1900
    else:
        year += 2000
    try:
        return datetime.date(year, month, day)
    except ValueError:
        raise InvalidComponent('The number does not contain valid birth date information.')


def validate(number):
    """Check if the number provided is a valid CPR number. This checks the
    length, formatting, embedded date and check digit."""
    number = compact(number)
    if not isdigits(number):
        raise InvalidFormat()
    if len(number) != 10:
        raise InvalidLength()
    if get_birth_date(number) > datetime.date.today():
        raise InvalidComponent(
            'The birth date information is valid, but this person has not been born yet.')
    return number


def is_valid(number):
    """Check if the number provided is a valid CPR number. This checks the
    length, formatting, embedded date and check digit."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    number = compact(number)
    return '-'.join((number[:6], number[6:]))
