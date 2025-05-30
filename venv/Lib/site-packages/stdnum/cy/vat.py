# vat.py - functions for handling Cypriot VAT numbers
# coding: utf-8
#
# Copyright (C) 2012, 2013 Arthur de Jong
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

"""Αριθμός Εγγραφής Φ.Π.Α. (Cypriot VAT number).

The Cypriot Αριθμός Εγγραφής Φ.Π.Α. (VAT) number consists of 9 digits
where the last one is a is a letter and functions as a check digit.

>>> compact('CY-10259033P')
'10259033P'
>>> validate('CY-10259033P ')
'10259033P'
>>> validate('CY-10259033Z')  # invalid check digit
Traceback (most recent call last):
    ...
InvalidChecksum: ...
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    number = clean(number, ' -').upper().strip()
    if number.startswith('CY'):
        number = number[2:]
    return number


def calc_check_digit(number):
    """Calculate the check digit. The number passed should not have the
    check digit included."""
    translation = {
        '0': 1, '1': 0, '2': 5, '3': 7, '4': 9,
        '5': 13, '6': 15, '7': 17, '8': 19, '9': 21,
    }
    return 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'[(
        sum(translation[x] for x in number[::2]) +
        sum(int(x) for x in number[1::2])
    ) % 26]


def validate(number):
    """Check if the number is a valid VAT number. This checks the length,
    formatting and check digit."""
    number = compact(number)
    if not isdigits(number[:-1]):
        raise InvalidFormat()
    if len(number) != 9:
        raise InvalidLength()
    if number[0:2] == '12':
        raise InvalidComponent()
    if number[-1] != calc_check_digit(number[:-1]):
        raise InvalidChecksum()
    return number


def is_valid(number):
    """Check if the number is a valid VAT number."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False
