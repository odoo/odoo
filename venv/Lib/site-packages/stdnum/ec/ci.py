# ci.py - functions for handling Ecuadorian personal identity codes
# coding: utf-8
#
# Copyright (C) 2014 Jonathan Finlay
# Copyright (C) 2014-2017 Arthur de Jong
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

"""CI (Cédula de identidad, Ecuadorian personal identity code).

The CI is a 10 digit number used to identify Ecuadorian citizens.

>>> validate('171430710-3')
'1714307103'
>>> validate('1714307104')  # invalid check digit
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> validate('171430710')  # digit missing
Traceback (most recent call last):
    ...
InvalidLength: ...
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, ' -').upper().strip()


def _checksum(number):
    """Calculate a checksum over the number."""
    fold = lambda x: x - 9 if x > 9 else x
    return sum(fold((2, 1)[i % 2] * int(n))
               for i, n in enumerate(number)) % 10


def validate(number):
    """Check if the number provided is a valid CI number. This checks the
    length, formatting and check digit."""
    number = compact(number)
    if len(number) != 10:
        raise InvalidLength()
    if not isdigits(number):
        raise InvalidFormat()
    if (number[:2] < '01' or number[:2] > '24') and (number[:2] not in ('30', '50')):
        raise InvalidComponent()  # invalid province code
    if number[2] > '6':
        raise InvalidComponent()  # third digit wrong
    if _checksum(number) != 0:
        raise InvalidChecksum()
    return number


def is_valid(number):
    """Check if the number provided is a valid CI number. This checks the
    length, formatting and check digit."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False
