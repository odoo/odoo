# tva.py - functions for handling Luxembourgian VAT numbers
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

"""TVA (taxe sur la valeur ajoutée, Luxembourgian VAT number).

The n° TVA (Numéro d'identification à la taxe sur la valeur ajoutée) is
used for tax purposes in Luxembourg. The number consists of 8 digits of
which the last two are check digits.

>>> validate('LU 150 274 42')
'15027442'
>>> validate('150 274 43')  # invalid check digits
Traceback (most recent call last):
    ...
InvalidChecksum: ...
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    number = clean(number, ' :.-').upper().strip()
    if number.startswith('LU'):
        number = number[2:]
    return number


def calc_check_digits(number):
    """Calculate the check digits for the number."""
    return '%02d' % (int(number) % 89)


def validate(number):
    """Check if the number is a valid VAT number. This checks the length,
    formatting and check digit."""
    number = compact(number)
    if not isdigits(number):
        raise InvalidFormat()
    if len(number) != 8:
        raise InvalidLength()
    if calc_check_digits(number[:6]) != number[-2:]:
        raise InvalidChecksum()
    return number


def is_valid(number):
    """Check if the number is a valid VAT number."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False
