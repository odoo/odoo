# rc.py - functions for handling Czech birth numbers
# coding: utf-8
#
# Copyright (C) 2012-2019 Arthur de Jong
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

"""RČ (Rodné číslo, the Czech birth number).

The birth number (RČ, Rodné číslo) is the Czech national identifier. The
number can be 9 or 10 digits long. Numbers given out after January 1st
1954 should have 10 digits. The number includes the birth date of the
person and their gender.

This number is identical to the Slovak counterpart.

>>> validate('710319/2745')
'7103192745'
>>> validate('991231123')
'991231123'
>>> validate('7103192746')  # invalid check digit
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> validate('1103492745')  # invalid date
Traceback (most recent call last):
    ...
InvalidComponent: ...
>>> validate('590312/123')  # 9 digit number in 1959
Traceback (most recent call last):
    ...
InvalidLength: ...
>>> format('7103192745')
'710319/2745'
"""

import datetime

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, ' /').upper().strip()


def get_birth_date(number):
    """Split the date parts from the number and return the birth date."""
    number = compact(number)
    year = 1900 + int(number[0:2])
    # females have 50 added to the month value, 20 is added when the serial
    # overflows (since 2004)
    month = int(number[2:4]) % 50 % 20
    day = int(number[4:6])
    # 9 digit numbers were used until January 1st 1954
    if len(number) == 9:
        if year >= 1980:
            year -= 100
        if year > 1953:
            raise InvalidLength('No 9 digit birth numbers after 1953.')
    elif year < 1954:
        year += 100
    try:
        return datetime.date(year, month, day)
    except ValueError:
        raise InvalidComponent()


def validate(number):
    """Check if the number is a valid birth number. This checks the length,
    formatting, embedded date and check digit."""
    number = compact(number)
    if not isdigits(number):
        raise InvalidFormat()
    if len(number) not in (9, 10):
        raise InvalidLength()
    # check if birth date is valid
    birth_date = get_birth_date(number)
    # TODO: check that the birth date is not in the future
    # check the check digit (10 digit numbers only)
    if len(number) == 10:
        check = int(number[:-1]) % 11
        # before 1985 the checksum could be 0 or 10
        if birth_date < datetime.date(1985, 1, 1):
            check = check % 10
        if number[-1] != str(check):
            raise InvalidChecksum()
    return number


def is_valid(number):
    """Check if the number is a valid birth number."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    number = compact(number)
    return number[:6] + '/' + number[6:]
