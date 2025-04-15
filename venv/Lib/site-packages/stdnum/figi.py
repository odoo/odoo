# figi.py - functions for handling FIGI numbers
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

"""FIGI (Financial Instrument Global Identifier).

The Financial Instrument Global Identifier (FIGI) is a 12-character
alpha-numerical unique identifier of financial instruments such as common
stock, options, derivatives, futures, corporate and government bonds,
municipals, currencies, and mortgage products.

More information:

* https://openfigi.com/
* https://en.wikipedia.org/wiki/Financial_Instrument_Global_Identifier

>>> validate('BBG000BLNQ16')
'BBG000BLNQ16'
>>> validate('BBG000BLNQ14')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, ' ').strip().upper()


def calc_check_digit(number):
    """Calculate the check digits for the number."""
    # we use the full alphabet for the check digit calculation
    alphabet = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    # convert to numeric first, then double some, then sum individual digits
    number = ''.join(
        str(alphabet.index(n) * (1, 2)[i % 2])
        for i, n in enumerate(number[:11]))
    return str((10 - sum(int(n) for n in number)) % 10)


def validate(number):
    """Check if the number provided is a valid FIGI."""
    number = compact(number)
    if not all(x in '0123456789BCDFGHJKLMNPQRSTVWXYZ' for x in number):
        raise InvalidFormat()
    if len(number) != 12:
        raise InvalidLength()
    if isdigits(number[0]) or isdigits(number[1]):
        raise InvalidFormat()
    if number[:2] in ('BS', 'BM', 'GG', 'GB', 'VG'):
        raise InvalidComponent()
    if number[2] != 'G':
        raise InvalidComponent()
    if calc_check_digit(number[:-1]) != number[-1]:
        raise InvalidChecksum()
    return number


def is_valid(number):
    """Check if the number provided is a valid FIGI."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False
