# kontonr.py - functions for handling Norwegian bank account numbers
# coding: utf-8
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

"""Konto nr. (Norwegian bank account number)

Konto nr. is the country-specific part in Norwegian IBAN codes. The number
consists of 11 digits, the first 4 are the bank identifier and the last is a
check digit. This module does not check if the bank identifier exists.

More information:

* https://www.ecbs.org/iban/norway-bank-account-number.html

>>> validate('8601 11 17947')
'86011117947'
>>> validate('0000.4090403')  # postgiro bank code
'4090403'
>>> validate('8601 11 17949')  # invalid check digits
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> format('86011117947')
'8601.11.17947'
>>> to_iban('8601 11 17947')
'NO93 8601 11 17947'
"""

from stdnum import luhn
from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    number = clean(number, ' .-').strip()
    if number.startswith('0000'):
        number = number[4:]  # strip leading 0000 postgiro bank code
    return number


def _calc_check_digit(number):
    """Calculate the check digit for the 11-digit number."""
    weights = (6, 7, 8, 9, 4, 5, 6, 7, 8, 9)
    return str(sum(w * int(n) for w, n in zip(weights, number)) % 11)


def validate(number):
    """Check if the number provided is a valid bank account number."""
    number = compact(number)
    if not isdigits(number):
        raise InvalidFormat()
    if len(number) == 7:
        luhn.validate(number)
    elif len(number) == 11:
        if _calc_check_digit(number) != number[-1]:
            raise InvalidChecksum()
    else:
        raise InvalidLength()
    return number


def is_valid(number):
    """Check if the number provided is a valid bank account number."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def to_iban(number):
    """Convert the number to an IBAN."""
    from stdnum import iban
    separator = ' ' if ' ' in number else ''
    return separator.join((
        'NO' + iban.calc_check_digits('NO00' + number),
        number))


def format(number):
    """Reformat the number to the standard presentation format."""
    number = compact(number)
    number = (11 - len(number)) * '0' + number
    return '.'.join([
        number[:4],
        number[4:6],
        number[6:],
    ])
