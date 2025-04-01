# ik.py - functions for handling Estonian Personal ID numbers (IK)
# coding: utf-8
#
# Copyright (C) 2015 Tomas Karasek
# Copyright (C) 2015 Arthur de Jong
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

"""Isikukood (Estonian Personcal ID number).

The number consists of 11 digits: the first indicates the gender and century
the person was born in, the following 6 digits the birth date, followed by a
3 digit serial and a check digit.

More information:

* https://www.riigiteataja.ee/akt/106032012004

>>> validate('36805280109')
'36805280109'
>>> validate('36805280108')  # incorrect check digit
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> get_birth_date('36805280109')
datetime.date(1968, 5, 28)
"""

import datetime

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, ' ').strip()


def get_birth_date(number):
    """Split the date parts from the number and return the birth date."""
    number = compact(number)
    if number[0] in '12':
        century = 1800
    elif number[0] in '34':
        century = 1900
    elif number[0] in '56':
        century = 2000
    elif number[0] in '78':
        century = 2100
    else:
        raise InvalidComponent()
    year = century + int(number[1:3])
    month = int(number[3:5])
    day = int(number[5:7])
    try:
        return datetime.date(year, month, day)
    except ValueError:
        raise InvalidComponent()


def get_gender(number):
    """Get the person's birth gender ('M' or 'F')."""
    number = compact(number)
    if number[0] in '1357':
        return 'M'
    elif number[0] in '2468':
        return 'F'
    else:
        raise InvalidComponent()


def calc_check_digit(number):
    """Calculate the check digit."""
    check = sum(((i % 9) + 1) * int(n)
                for i, n in enumerate(number[:-1])) % 11
    if check == 10:
        check = sum((((i + 2) % 9) + 1) * int(n)
                    for i, n in enumerate(number[:-1])) % 11
    return str(check % 10)


def validate(number):
    """Check if the number provided is valid. This checks the length,
    formatting, embedded date and check digit."""
    number = compact(number)
    if not isdigits(number):
        raise InvalidFormat()
    if len(number) != 11:
        raise InvalidLength()
    get_birth_date(number)
    if number[-1] != calc_check_digit(number):
        raise InvalidChecksum()
    return number


def is_valid(number):
    """Check if the number provided is valid. This checks the length,
    formatting, embedded date and check digit."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False
