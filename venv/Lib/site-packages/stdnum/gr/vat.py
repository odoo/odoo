# vat.py - functions for handling Greek VAT numbers
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

"""FPA, ΦΠΑ, ΑΦΜ (Αριθμός Φορολογικού Μητρώου, the Greek VAT number).

The FPA is a 9-digit number with a simple checksum.

>>> compact('GR 23456783')
'023456783'
>>> validate('EL 094259216 ')
'094259216'
>>> validate('EL 123456781')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    number = clean(number, ' -./:').upper().strip()
    if number.startswith('EL') or number.startswith('GR'):
        number = number[2:]
    if len(number) == 8:
        number = '0' + number  # old format had 8 digits
    return number


def calc_check_digit(number):
    """Calculate the check digit. The number passed should not have the
    check digit included."""
    checksum = 0
    for n in number:
        checksum = checksum * 2 + int(n)
    return str(checksum * 2 % 11 % 10)


def validate(number):
    """Check if the number is a valid VAT number. This checks the length,
    formatting and check digit."""
    number = compact(number)
    if not isdigits(number):
        raise InvalidFormat()
    if len(number) != 9:
        raise InvalidLength()
    if calc_check_digit(number[:-1]) != number[-1]:
        raise InvalidChecksum()
    return number


def is_valid(number):
    """Check if the number is a valid VAT number."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False
