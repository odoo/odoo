# registrikood.py - functions for handling the Estonian Registrikood
# coding: utf-8
#
# Copyright (C) 2017 Holvi Payment Services
# Copyright (C) 2017 Arthur de Jong
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

"""Registrikood (Estonian organisation registration code).

All organisations are assigned a unique tax identification code from the
commercial register, from the state register or from the non-profit
associations and foundations register. The code consists of 8 digits.

Commercial company numbers start with a 1, schools and government numbers
with a 7, non-profit organisations with an 8 and foundations with a 9. The
number uses the same check digit algorithm as the Isikukood although that
fact is undocumented.

More information:

* https://ariregister.rik.ee/
* https://mtr.mkm.ee/

>>> validate('12345678')
'12345678'
>>> validate('12345679')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> validate('32345674')
Traceback (most recent call last):
    ...
InvalidComponent: ...
"""

from stdnum.ee.ik import calc_check_digit
from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, ' ').strip()


def validate(number):
    """Check if the number provided is valid. This checks the length and
    check digit."""
    number = compact(number)
    if not isdigits(number):
        raise InvalidFormat()
    if len(number) != 8:
        raise InvalidLength()
    if number[0] not in '1789':
        raise InvalidComponent()
    if number[-1] != calc_check_digit(number):
        raise InvalidChecksum()
    return number


def is_valid(number):
    """Check if the number provided is valid. This checks the length and
    check digit."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False
