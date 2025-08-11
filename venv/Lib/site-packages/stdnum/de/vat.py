# vat.py - functions for handling German VAT numbers
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

"""Ust ID Nr. (Umsatzsteur Identifikationnummer, German VAT number).

The number is 10 digits long and uses the ISO 7064 Mod 11, 10 check digit
algorithm.

>>> compact('DE 136,695 976')
'136695976'
>>> validate('DE136695976')
'136695976'
>>> validate('136695978')
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
    number = clean(number, ' -./,').upper().strip()
    if number.startswith('DE'):
        number = number[2:]
    return number


def validate(number):
    """Check if the number provided is a valid VAT number. This checks the
    length, formatting and check digit."""
    number = compact(number)
    if not isdigits(number) or number[0] == '0':
        raise InvalidFormat()
    if len(number) != 9:
        raise InvalidLength()
    mod_11_10.validate(number)
    return number


def is_valid(number):
    """Check if the number provided is a valid VAT number. This checks the
    length, formatting and check digit."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False
