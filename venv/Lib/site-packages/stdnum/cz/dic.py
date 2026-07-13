# dic.py - functions for handling Czech VAT numbers
# coding: utf-8
#
# Copyright (C) 2012-2017 Arthur de Jong
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

"""DIČ (Daňové identifikační číslo, Czech VAT number).

The number is an 8, 9 or 10 digit code that includes a check digit and is
used to uniquely identify taxpayers for VAT (DPH in Czech). The number can
refer to legal entities (8 digit numbers), individuals with a RČ (the 9 or
10 digit Czech birth number) or individuals without a RČ (9 digit numbers
that begin with a 6).

>>> compact('CZ 25123891')
'25123891'
>>> validate('25123891')  # legal entity
'25123891'
>>> validate('25123890')  # incorrect check digit
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> validate('7103192745')  # RČ
'7103192745'
>>> validate('640903926')  # special case
'640903926'
"""

from stdnum.cz import rc
from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    number = clean(number, ' /').upper().strip()
    if number.startswith('CZ'):
        number = number[2:]
    return number


def calc_check_digit_legal(number):
    """Calculate the check digit for 8 digit legal entities. The number
    passed should not have the check digit included."""
    check = (11 - sum((8 - i) * int(n) for i, n in enumerate(number))) % 11
    return str((check or 1) % 10)


def calc_check_digit_special(number):
    """Calculate the check digit for special cases. The number passed
    should not have the first and last digits included."""
    check = sum((8 - i) * int(n) for i, n in enumerate(number)) % 11
    return str((8 - (10 - check) % 11) % 10)


def validate(number):
    """Check if the number is a valid VAT number. This checks the length,
    formatting and check digit."""
    number = compact(number)
    if not isdigits(number):
        raise InvalidFormat()
    if len(number) == 8:
        # legal entities
        if number.startswith('9'):
            raise InvalidComponent()
        if calc_check_digit_legal(number[:-1]) != number[-1]:
            raise InvalidChecksum()
    elif len(number) == 9 and number.startswith('6'):
        # special cases (skip first digit in calculation)
        if calc_check_digit_special(number[1:-1]) != number[-1]:
            raise InvalidChecksum()
    elif len(number) in (9, 10):
        # 9 or 10 digit individual
        rc.validate(number)
    else:
        raise InvalidLength()
    return number


def is_valid(number):
    """Check if the number is a valid VAT number."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False
