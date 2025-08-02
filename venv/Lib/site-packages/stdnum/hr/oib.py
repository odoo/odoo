# cnp.py - functions for handling Croatian OIB numbers
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

"""OIB (Osobni identifikacijski broj, Croatian identification number).

The personal identification number is used to identify persons and legal
entities in Croatia. It has 11 digits (sometimes prefixed by HR), contains
no personal information and uses the ISO 7064 Mod 11, 10 checksum algorithm.

>>> validate('HR 33392005961')
'33392005961'
>>> validate('33392005962')  # invalid check digit
Traceback (most recent call last):
    ...
InvalidChecksum: ...
"""

from stdnum.exceptions import *
from stdnum.iso7064 import mod_11_10
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    number = clean(number, ' -').upper().strip()
    if number.startswith('HR'):
        number = number[2:]
    return number


def validate(number):
    """Check if the number is a valid OIB number. This checks the length,
    formatting and check digit."""
    number = compact(number)
    if not isdigits(number):
        raise InvalidFormat()
    if len(number) != 11:
        raise InvalidLength()
    mod_11_10.validate(number)
    return number


def is_valid(number):
    """Check if the number is a valid OIB number."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False
