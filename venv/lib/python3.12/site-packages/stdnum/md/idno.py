# idno.py - functions for handling Moldavian company identification numbers
# coding: utf-8
#
# Copyright (C) 2019 Arthur de Jong
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

"""IDNO (Moldavian company identification number).

The IDNO is used in Moldavia as unique identifier for legal entities. The
number consists of 13 digits. The first digit identifies the registry,
followed by three digits for the year the code was assigned. The number ends
with five identifier digits and a check digit.

More information:

* https://www.idno.md

>>> validate('1008600038413')
'1008600038413'
>>> validate('1008600038412')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, ' ').strip()


def calc_check_digit(number):
    """Calculate the check digit."""
    weights = (7, 3, 1, 7, 3, 1, 7, 3, 1, 7, 3, 1)
    return str(sum(w * int(n) for w, n in zip(weights, number)) % 10)


def validate(number):
    """Check if the number provided is valid. This checks the length,
    formatting and check digit."""
    number = compact(number)
    if not isdigits(number):
        raise InvalidFormat()
    if len(number) != 13:
        raise InvalidLength()
    if number[-1] != calc_check_digit(number):
        raise InvalidChecksum()
    return number


def is_valid(number):
    """Check if the number provided is valid. This checks the length,
    formatting and check digit."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False
