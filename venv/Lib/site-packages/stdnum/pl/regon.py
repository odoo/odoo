# regon.py - functions for handling REGON numbers
# coding: utf-8
#
# Copyright (C) 2015 Dariusz Choruzy
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

"""REGON (Rejestr Gospodarki Narodowej, Polish register of economic units).

The REGON (Rejestr Gospodarki Narodowej) is a statistical identification
number for businesses. National entities are assigned a 9-digit number, while
local units append 5 digits to form a 14-digit number.

More information:

* https://bip.stat.gov.pl/en/regon/
* https://wyszukiwarkaregon.stat.gov.pl/appBIR/index.aspx

>>> validate('192598184')
'192598184'
>>> validate('123456785')
'123456785'
>>> validate('192598183')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> validate('12345678512347')
'12345678512347'
>>> validate('12345678612342')  # first check digit invalid
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> validate('12345678512348')  # last check digit invalid
Traceback (most recent call last):
    ...
InvalidChecksum: ...
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, ' -').upper().strip()


def calc_check_digit(number):
    """Calculate the check digit for organisations. The number passed
    should not have the check digit included."""
    if len(number) == 8:
        weights = (8, 9, 2, 3, 4, 5, 6, 7)
    else:
        weights = (2, 4, 8, 5, 0, 9, 7, 3, 6, 1, 2, 4, 8)
    check = sum(w * int(n) for w, n in zip(weights, number))
    return str(check % 11 % 10)


def validate(number):
    """Check if the number is a valid REGON number. This checks the length,
    formatting and check digit."""
    number = compact(number)
    if not isdigits(number):
        raise InvalidFormat()
    if len(number) not in (9, 14):
        raise InvalidLength()
    if number[-1] != calc_check_digit(number[:-1]):
        raise InvalidChecksum()
    if len(number) == 14 and number[8] != calc_check_digit(number[:8]):
        raise InvalidChecksum()
    return number


def is_valid(number):
    """Check if the number is a valid REGON number."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False
