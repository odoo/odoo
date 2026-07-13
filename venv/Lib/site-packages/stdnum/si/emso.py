# emso.py - functions for handling Slovenian Unique Master Citizen Numbers
# coding: utf-8
#
# Copyright (C) 2022 Blaž Bregar
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

"""Enotna matična številka občana (Unique Master Citizen Number).

The EMŠO is used for uniquely identify persons including foreign citizens
living in Slovenia, It is issued by Centralni Register Prebivalstva CRP
(Central Citizen Registry).

The number consists of 13 digits and includes the person's date of birth, a
political region of birth and a unique number that encodes a person's gender
followed by a check digit.

More information:

* https://en.wikipedia.org/wiki/Unique_Master_Citizen_Number
* https://sl.wikipedia.org/wiki/Enotna_matična_številka_občana

>>> validate('0101006500006')
'0101006500006'
>>> validate('0101006500007')  # invalid check digit
Traceback (most recent call last):
    ...
InvalidChecksum: ...
"""

import datetime

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, ' ').strip()


def calc_check_digit(number):
    """Calculate the check digit."""
    weights = (7, 6, 5, 4, 3, 2, 7, 6, 5, 4, 3, 2)
    total = sum(int(n) * w for n, w in zip(number, weights))
    return str(-total % 11 % 10)


def get_birth_date(number):
    """Return date of birth from valid EMŠO."""
    number = compact(number)
    day = int(number[:2])
    month = int(number[2:4])
    year = int(number[4:7])
    if year < 800:
        year += 2000
    else:
        year += 1000
    try:
        return datetime.date(year, month, day)
    except ValueError:
        raise InvalidComponent()


def get_gender(number):
    """Get the person's birth gender ('M' or 'F')."""
    number = compact(number)
    if int(number[9:12]) < 500:
        return 'M'
    else:
        return 'F'


def get_region(number):
    """Return (political) region from valid EMŠO."""
    return number[7:9]


def validate(number):
    """Check if the number is a valid EMŠO number. This checks the length,
    formatting and check digit."""
    number = compact(number)
    if len(number) != 13:
        raise InvalidLength()
    if not isdigits(number):
        raise InvalidFormat()
    get_birth_date(number)
    if calc_check_digit(number) != number[-1]:
        raise InvalidChecksum()
    return number


def is_valid(number):
    """Check if the number provided is a valid ID. This checks the length,
    formatting and check digit."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    return compact(number)
