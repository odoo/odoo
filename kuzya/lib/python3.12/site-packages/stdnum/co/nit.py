# nit.py - functions for handling Colombian identity codes
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

"""NIT (Número De Identificación Tributaria, Colombian identity code).

This number, also referred to as RUT (Registro Unico Tributario) is the
Colombian business tax number.

>>> validate('213.123.432-1')
'2131234321'
>>> validate('2131234325')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> format('2131234321')
'213.123.432-1'
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips
    surrounding whitespace and separation dash."""
    return clean(number, '.,- ').upper().strip()


def calc_check_digit(number):
    """Calculate the check digit. The number passed should not have the
    check digit included."""
    weights = (3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71)
    s = sum(w * int(n) for w, n in zip(weights, reversed(number))) % 11
    return '01987654321'[s]


def validate(number):
    """Check if the number is a valid NIT. This checks the length, formatting
    and check digit."""
    number = compact(number)
    if not 8 <= len(number) <= 16:
        raise InvalidLength()
    if not isdigits(number):
        raise InvalidFormat()
    if calc_check_digit(number[:-1]) != number[-1]:
        raise InvalidChecksum()
    return number


def is_valid(number):
    """Check if the number is a valid NIT."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    number = compact(number)
    return '.'.join(
        number[i - 3:i] for i in reversed(range(-1, -len(number), -3))
    ) + '-' + number[-1]
