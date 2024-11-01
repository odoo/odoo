# nif.py - functions for handling Portuguese VAT numbers
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

"""NIF (Número de identificação fiscal, Portuguese VAT number).

The NIF (Número de identificação fiscal, NIPC, Número de Identificação de
Pessoa Colectiva) is used for VAT purposes. It is a 9-digit number with a
simple checksum.

>>> validate('PT 501 964 843')
'501964843'
>>> validate('PT 501 964 842')  # invalid check digits
Traceback (most recent call last):
    ...
InvalidChecksum: ...
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    number = clean(number, ' -.').upper().strip()
    if number.startswith('PT'):
        number = number[2:]
    return number


def calc_check_digit(number):
    """Calculate the check digit. The number passed should not have the
    check digit included."""
    s = sum((9 - i) * int(n) for i, n in enumerate(number))
    return str((11 - s) % 11 % 10)


def validate(number):
    """Check if the number is a valid VAT number. This checks the length,
    formatting and check digit."""
    number = compact(number)
    if not isdigits(number) or number[0] == '0':
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
