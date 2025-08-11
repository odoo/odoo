# associationid.py - functions for handling Finnish association registry id
# coding: utf-8
#
# Copyright (C) 2015 Holvi Payment Services Oy
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

"""Finnish Association Identifier.

The number consists of 1 to 6 digits that are normally separated with a dot
in groups of 0-3 and 0-3 numbers. E.g. 123.123, 12.123, 1.123, 123 or 1.

>>> validate('123.123')
'123123'
>>> validate('1123')
'1123'
>>> validate('123123123')
Traceback (most recent call last):
  ...
InvalidLength: The number has an invalid length.
>>> validate('12df')
Traceback (most recent call last):
  ...
InvalidFormat: The number has an invalid format.
>>> format('123')
'123'
>>> format('1234')
'1.234'
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


# a collection of all registered numbers with 2 or less digits
_lownumbers = set((
    1, 6, 7, 9, 12, 14, 15, 16, 18, 22, 23, 24, 27, 28, 29, 35, 36, 38, 40,
    41, 42, 43, 45, 46, 50, 52, 55, 58, 60, 64, 65, 68, 72, 75, 76, 77, 78,
    83, 84, 85, 89, 92))


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, ' -._+').strip()


def validate(number):
    """Check if the number is a valid Finnish association register number.
    This checks the length and format."""
    number = compact(number)
    if not isdigits(number):
        raise InvalidFormat()
    if len(number) < 1 or len(number) > 6:
        raise InvalidLength()
    if len(number) < 3 and int(number) not in _lownumbers:
        raise InvalidComponent()
    return number


def is_valid(number):
    """Check if the number is a valid association register number."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    number = compact(number)
    if len(number) <= 3:
        return number
    else:
        return number[:-3] + '.' + number[-3:]
