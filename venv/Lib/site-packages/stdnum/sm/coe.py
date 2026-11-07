# coe.py - functions for handling San Marino tax numbers
# coding: utf-8
#
# Copyright (C) 2008-2011 Cédric Krier
# Copyright (C) 2008-2011 B2CK
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

"""COE (Codice operatore economico, San Marino national tax number).

The COE is a tax identification number of up to 5-digits used in San Marino.
Leading zeroes are commonly dropped.

>>> validate('51')
'51'
>>> validate('024165')
'24165'
>>> validate('2416A')
Traceback (most recent call last):
    ...
InvalidFormat: ...
>>> validate('1124165')
Traceback (most recent call last):
    ...
InvalidLength: ...
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


# a collection of all registered numbers with 2 or less digits
_lownumbers = set((
    2, 4, 6, 7, 8, 9, 10, 11, 13, 16, 18, 19, 20, 21, 25, 26, 30, 32, 33, 35,
    36, 37, 38, 39, 40, 42, 45, 47, 49, 51, 52, 55, 56, 57, 58, 59, 61, 62,
    64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 79, 80, 81, 84, 85,
    87, 88, 91, 92, 94, 95, 96, 97, 99))


def compact(number):
    """Convert the number to the minimal representation. This strips
    surrounding whitespace and separation dash."""
    return clean(number, '.').strip().lstrip('0')


def validate(number):
    """Check if the number is a valid COE. This checks the length and
    formatting."""
    number = compact(number)
    if len(number) > 5 or len(number) == 0:
        raise InvalidLength()
    if not isdigits(number):
        raise InvalidFormat()
    if len(number) < 3 and int(number) not in _lownumbers:
        raise InvalidComponent()
    return number


def is_valid(number):
    """Check if the number is a valid COE."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False
