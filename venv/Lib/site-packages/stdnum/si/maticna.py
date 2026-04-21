# maticna.py - functions for handling Slovenian Corporate Registration Numbers
# coding: utf-8
#
# Copyright (C) 2023 Blaž Bregar
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

"""Matična številka poslovnega registra (Corporate Registration Number)

The Corporate registration number represent a unique identification of
each unit of the business register, assigned by the registry administrator
at the time of entry in the business register, which shall not be changed.

The number consists of 7 or 10 digits and includes a check digit. The first 6
digits represent a unique number for each unit or company, followed by a
check digit. The last 3 digits represent an additional business unit of the
company, starting at 001. When a company consists of more than 1000 units, a
letter is used instead of the first digit in the business unit. Unit 000
always represents the main registered address.

More information:

* http://www.pisrs.si/Pis.web/pregledPredpisa?id=URED7599

>>> validate('9331310000')
'9331310'
>>> validate('9331320000')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
"""

import re

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    number = clean(number, '. ').strip().upper()
    if len(number) == 10 and number.endswith('000'):
        number = number[0:7]
    return number


def calc_check_digit(number):
    """Calculate the check digit."""
    weights = (7, 6, 5, 4, 3, 2)
    total = sum(int(n) * w for n, w in zip(number, weights))
    remainder = -total % 11
    if remainder == 0:
        return 'invalid'  # invalid remainder
    return str(remainder % 10)


def validate(number):
    """Check if the number is a valid Corporate Registration number. This
    checks the length and check digit."""
    number = compact(number)
    if len(number) not in (7, 10):
        raise InvalidLength()
    if not isdigits(number[:6]):
        raise InvalidFormat()
    if not re.match(r'^([A-Za-z0-9]\d{2})?$', number[7:]):
        raise InvalidFormat()
    if calc_check_digit(number) != number[6]:
        raise InvalidChecksum()
    return number


def is_valid(number):
    """Check if provided is valid ID. This checks the length,
    formatting and check digit."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False
