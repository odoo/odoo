# pesel.py - functions for handling Polish national identification numbers
# coding: utf-8
#
# Copyright (C) 2015 Dariusz Choruzy
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

"""PESEL (Polish national identification number).

The Powszechny Elektroniczny System Ewidencji Ludności (PESEL, Universal
Electronic System for Registration of the Population) is a 11-digit Polish
national identification number. The number consists of the date of birth,
a serial number, the person's gender and a check digit.


>>> validate('44051401359')
'44051401359'
>>> validate('44051401358')  # incorrect check digit
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> validate('02381307589')  # invalid birth date
Traceback (most recent call last):
    ...
InvalidComponent: ...
>>> get_birth_date('02122401358')
datetime.date(1902, 12, 24)
>>> get_gender('02122401358')
'M'
>>> get_birth_date('02211307589')
datetime.date(2002, 1, 13)
>>> get_gender('02211307589')
'F'
"""

import datetime

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, ' -').upper().strip()


def get_birth_date(number):
    """Split the date parts from the number and return the birth date."""
    number = compact(number)
    year = int(number[0:2])
    month = int(number[2:4])
    day = int(number[4:6])
    year += {
        0: 1900,
        1: 2000,
        2: 2100,
        3: 2200,
        4: 1800,
    }[month // 20]
    month = month % 20
    try:
        return datetime.date(year, month, day)
    except ValueError:
        raise InvalidComponent()


def get_gender(number):
    """Get the person's birth gender ('M' or 'F')."""
    number = compact(number)
    if number[9] in '02468':  # even
        return 'F'
    else:  # odd: 13579
        return 'M'


def calc_check_digit(number):
    """Calculate the check digit for organisations. The number passed
    should not have the check digit included."""
    weights = (1, 3, 7, 9, 1, 3, 7, 9, 1, 3)
    check = sum(w * int(n) for w, n in zip(weights, number))
    return str((10 - check) % 10)


def validate(number):
    """Check if the number is a valid national identification number. This
    checks the length, formatting and check digit."""
    number = compact(number)
    if not isdigits(number):
        raise InvalidFormat()
    if len(number) != 11:
        raise InvalidLength()
    if number[-1] != calc_check_digit(number[:-1]):
        raise InvalidChecksum()
    get_birth_date(number)
    return number


def is_valid(number):
    """Check if the number is a valid national identification number."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False
