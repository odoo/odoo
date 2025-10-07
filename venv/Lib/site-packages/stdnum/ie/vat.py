# vat.py - functions for handling Irish VAT numbers
#
# Copyright (C) 2012-2016 Arthur de Jong
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

"""VAT (Irish tax reference number).

The Irish VAT number consists of 8 or 9 digits. The number is either 7 digits
and 1 letter (optionally followed by a W for married women), 7 digits and 2
letters, or 6 digits and 2 letters or symbols (in second and last position).

>>> validate('IE 6433435F')  # pre-2013 format
'6433435F'
>>> validate('IE 6433435OA')  # 2013 format
'6433435OA'
>>> validate('6433435E')  # incorrect check digit
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> validate('8D79739I')  # old style number
'8D79739I'
>>> validate('8?79739J')  # incorrect old style
Traceback (most recent call last):
    ...
InvalidFormat: ...
>>> convert('1F23456T')
'0234561T'
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    number = clean(number, ' -').upper().strip()
    if number.startswith('IE'):
        number = number[2:]
    return number


_alphabet = 'WABCDEFGHIJKLMNOPQRSTUV'


def calc_check_digit(number):
    """Calculate the check digit. The number passed should not have the
    check digit included."""
    number = compact(number).zfill(7)
    return _alphabet[(
        sum((8 - i) * int(n) for i, n in enumerate(number[:7])) +
        9 * _alphabet.index(number[7:])) % 23]


def validate(number):
    """Check if the number provided is a valid VAT number. This checks the
    length, formatting and check digit."""
    number = compact(number)
    if not isdigits(number[:1]) or not isdigits(number[2:7]):
        raise InvalidFormat()
    if not all(x in _alphabet for x in number[7:]):
        raise InvalidFormat()
    if len(number) not in (8, 9):
        raise InvalidLength()
    if isdigits(number[:7]):
        # new system (7 digits followed by 1 or 2 letters)
        if number[7] != calc_check_digit(number[:7] + number[8:]):
            raise InvalidChecksum()
    elif number[1] in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ+*':
        # old system (second character is a letter or symbol)
        if number[7] != calc_check_digit(number[2:7] + number[0]):
            raise InvalidChecksum()
    else:
        raise InvalidFormat()
    return number


def is_valid(number):
    """Check if the number provided is a valid VAT number. This checks the
    length, formatting and check digit."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def convert(number):
    """Convert an "old" style 8-digit VAT number where the second character
    is a letter to the new 8-digit format where only the last digit is a
    character."""
    number = compact(number)
    if len(number) == 8 and not isdigits(number[1]):
        number = '0' + number[2:7] + number[0] + number[7:]
    return number
