# vkn.py - functions for handling the Turkish tax identification number
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

"""VKN (Vergi Kimlik Numarası, Turkish tax identification number).

The Vergi Kimlik Numarası is the Turkish tax identification number used for
businesses. The number consists of 10 digits where the first digit is derived
from the company name.

More information:

* https://www.turkiye.gov.tr/gib-intvrg-vergi-kimlik-numarasi-dogrulama

>>> validate('4540536920')
'4540536920'
>>> validate('4540536921')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> validate('454053692')
Traceback (most recent call last):
    ...
InvalidLength: ...
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number).strip()


def calc_check_digit(number):
    """Calculate the check digit for the specified number."""
    s = 0
    for i, n in enumerate(reversed(number[:9]), 1):
        c1 = (int(n) + i) % 10
        if c1:
            c2 = (c1 * (2 ** i)) % 9 or 9
            s += c2
    return str((10 - s) % 10)


def validate(number):
    """Check if the number is a valid Vergi Kimlik Numarası. This checks the
    length and check digits."""
    number = compact(number)
    if not isdigits(number):
        raise InvalidFormat()
    if len(number) != 10:
        raise InvalidLength()
    if calc_check_digit(number) != number[-1]:
        raise InvalidChecksum()
    return number


def is_valid(number):
    """Check if the number is a valid Vergi Kimlik Numarası. This checks the
    length and check digits."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False
