# asmens.py - functions for handling Lithuanian personal numbers
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

"""Asmens kodas (Lithuanian, personal numbers).

The Asmens kodas consists of 11 digits. The first digits denotes the gender
and birth century, the second through seventh denotes the birth date,
followed by a three-digit serial and a check digit.

More information:

* https://lt.wikipedia.org/wiki/Asmens_kodas
* https://en.wikipedia.org/wiki/National_identification_number#Lithuania

>>> validate('33309240064')
'33309240064'
>>> validate('33309240164')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
"""

from stdnum.ee.ik import calc_check_digit, get_birth_date
from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, ' ').strip()


def validate(number, validate_birth_date=True):
    """Check if the number provided is valid. This checks the length,
    formatting, embedded date and check digit."""
    number = compact(number)
    if not isdigits(number):
        raise InvalidFormat()
    if len(number) != 11:
        raise InvalidLength()
    if validate_birth_date and number[0] != '9':
        get_birth_date(number)
    if number[-1] != calc_check_digit(number):
        raise InvalidChecksum()
    return number


def is_valid(number, validate_birth_date=True):
    """Check if the number provided is valid. This checks the length,
    formatting, embedded date and check digit."""
    try:
        return bool(validate(number, validate_birth_date))
    except ValidationError:
        return False
