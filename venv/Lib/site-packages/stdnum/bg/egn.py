# egn.py - functions for handling Bulgarian national identification numbers
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

"""EGN (ЕГН, Единен граждански номер, Bulgarian personal identity codes).

It is a 10-digit number of which the first 6 digits denote the person's
birth date, the next three digits represent a birth order number from
which the person's gender can be determined and the last digit is a check
digit.

>>> compact('752316 926 3')
'7523169263'
>>> validate('8032056031')
'8032056031'
>>> get_birth_date('7542011030')
datetime.date(2075, 2, 1)
>>> validate('7552A10004')  # invalid digit
Traceback (most recent call last):
    ...
InvalidFormat: ...
>>> validate('8019010008')  # invalid date
Traceback (most recent call last):
    ...
InvalidComponent: ...
"""

import datetime

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, ' -.').upper().strip()


def calc_check_digit(number):
    """Calculate the check digit. The number passed should not have the
    check digit included."""
    weights = (2, 4, 8, 5, 10, 9, 7, 3, 6)
    return str(sum(w * int(n) for w, n in zip(weights, number)) % 11 % 10)


def get_birth_date(number):
    """Split the date parts from the number and return the birth date."""
    number = compact(number)
    year = int(number[0:2]) + 1900
    month = int(number[2:4])
    day = int(number[4:6])
    if month > 40:
        year += 100
        month -= 40
    elif month > 20:
        year -= 100
        month -= 20
    try:
        return datetime.date(year, month, day)
    except ValueError:
        raise InvalidComponent()


def validate(number):
    """Check if the number is a valid national identification number. This
    checks the length, formatting, embedded date and check digit."""
    number = compact(number)
    if not isdigits(number):
        raise InvalidFormat()
    if len(number) != 10:
        raise InvalidLength()
    # check if birth date is valid
    get_birth_date(number)
    # TODO: check that the birth date is not in the future
    # check the check digit
    if calc_check_digit(number[:-1]) != number[-1]:
        raise InvalidChecksum()
    return number


def is_valid(number):
    """Check if the number is a valid national identification number."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False
