# nric.py - functions for handling  NRIC numbers
#
# Copyright (C) 2013, 2014 Arthur de Jong
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

"""NRIC No. (Malaysian National Registration Identity Card Number).

The NRIC No. is the unique identifier for issued to Malaysian citizens and
permanent residents.

The number consist of 12 digits in three sections. The first 6 digits
represent the birth date, followed by two digits representing the birth
place and finally four digits. The gender of a person can be derived from
the last digit: odd numbers for males and even numbers for females.

>>> validate('770305-02-1234')
'770305021234'
>>> validate('771305-02-1234')  # invalid date
Traceback (most recent call last):
    ...
InvalidComponent: ...
>>> validate('770305-17-1234')  # unknown birth place code
Traceback (most recent call last):
    ...
InvalidComponent: ...
>>> format('770305021234')
'770305-02-1234'
"""

import datetime

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, ' -*').strip()


def get_birth_date(number):
    """Split the date parts from the number and return the birth date.
    Note that in some cases it may return the registration date instead of
    the birth date and it may be a century off."""
    number = compact(number)
    year = int(number[0:2])
    month = int(number[2:4])
    day = int(number[4:6])
    # this is a bit broken but it's easy
    try:
        return datetime.date(year + 1900, month, day)
    except ValueError:
        pass
    try:
        return datetime.date(year + 2000, month, day)
    except ValueError:
        raise InvalidComponent()


def get_birth_place(number):
    """Use the number to look up the place of birth of the person. This can
    either be a state or federal territory within Malaysia or a country
    outside of Malaysia."""
    from stdnum import numdb
    number = compact(number)
    results = numdb.get('my/bp').info(number[6:8])[0][1]
    if not results:
        raise InvalidComponent()
    return results


def validate(number):
    """Check if the number is a valid NRIC number. This checks the length,
    formatting and birth date and place."""
    number = compact(number)
    if len(number) != 12:
        raise InvalidLength()
    if not isdigits(number):
        raise InvalidFormat()
    get_birth_date(number)
    get_birth_place(number)
    return number


def is_valid(number):
    """Check if the number is a valid NRIC number."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    number = compact(number)
    return number[:6] + '-' + number[6:8] + '-' + number[8:]
