# pib.py - functions for handling Montenegro PIB numbers
# coding: utf-8
#
# Copyright (C) 2022 Leandro Regueiro
# Copyright (C) 2022 Arthur de Jong
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

"""PIB (Poreski Identifikacioni Broj, Montenegro tax number).

This number consists of 8 digits.

More information:

* http://www.pretraga.crps.me:8083/
* https://www.vatify.eu/montenegro-vat-number.html

>>> validate('02655284')
'02655284'
>>> validate('02655283')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> format('02655284')
'02655284'
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation.

    This strips the number of any valid separators and removes surrounding
    whitespace.
    """
    return clean(number, ' ')


def calc_check_digit(number):
    """Calculate the check digit for the number."""
    weights = (8, 7, 6, 5, 4, 3, 2)
    return str((-sum(w * int(n) for w, n in zip(weights, number))) % 11 % 10)


def validate(number):
    """Check if the number is a valid Montenegro PIB number."""
    number = compact(number)
    if len(number) != 8:
        raise InvalidLength()
    if not isdigits(number):
        raise InvalidFormat()
    if number[-1] != calc_check_digit(number):
        raise InvalidChecksum()
    return number


def is_valid(number):
    """Check if the number is a valid Montenegro PIB number."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    return compact(number)
