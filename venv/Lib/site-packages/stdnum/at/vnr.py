# vnr.py - functions for handling Austrian social security numbers
# coding: utf-8
#
# Copyright (C) 2018 Arthur de Jong
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

"""VNR, SVNR, VSNR (Versicherungsnummer, Austrian social security number).

The Austian Versicherungsnummer is a personal identification number used for
social security. The number is 10 digits long and consists of a 3 digit
serial, a check digit and 6 digits that usually specify the person's birth
date.

More information:

* https://de.wikipedia.org/wiki/Sozialversicherungsnummer#Österreich

>>> validate('1237 010180')
'1237010180'
>>> validate('2237 010180')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, ' ')


def calc_check_digit(number):
    """Calculate the check digit. The fourth digit in the number is
    ignored."""
    weights = (3, 7, 9, 0, 5, 8, 4, 2, 1, 6)
    return str(sum(w * int(n) for w, n in zip(weights, number)) % 11)


def validate(number):
    """Check if the number is a valid VAT number. This checks the length,
    formatting and check digit."""
    number = compact(number)
    if not isdigits(number) or number.startswith('0'):
        raise InvalidFormat()
    if len(number) != 10:
        raise InvalidLength()
    if calc_check_digit(number) != number[3]:
        raise InvalidChecksum()
    return number


def is_valid(number):
    """Check if the number is a valid VAT number."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False
