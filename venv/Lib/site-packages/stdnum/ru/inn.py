# inn.py - functions for handling Russian VAT numbers
# coding: utf-8
#
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

"""ИНН (Идентификационный номер налогоплательщика, Russian tax identifier).

The Indentifikatzionny nomer nalogoplatel'shchika is a Russian tax
identification number that consists 10 digits for companies and 12 digits for
persons.

>>> validate('123456789047')
'123456789047'
>>> validate('1234567894')
'1234567894'
>>> validate('123456789037')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> validate('1234567895')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, ' ').strip()


def calc_company_check_digit(number):
    """Calculate the check digit for the 10-digit ИНН for organisations."""
    weights = (2, 4, 10, 3, 5, 9, 4, 6, 8)
    return str(sum(w * int(n) for w, n in zip(weights, number)) % 11 % 10)


def calc_personal_check_digits(number):
    """Calculate the check digits for the 12-digit personal ИНН."""
    weights = (7, 2, 4, 10, 3, 5, 9, 4, 6, 8)
    d1 = str(sum(w * int(n) for w, n in zip(weights, number)) % 11 % 10)
    weights = (3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8)
    d2 = str(sum(w * int(n) for w, n in zip(weights, number[:10] + d1)) % 11 % 10)
    return d1 + d2


def validate(number):
    """Check if the number is a valid ИНН. This checks the length, formatting
    and check digit."""
    number = compact(number)
    if not isdigits(number):
        raise InvalidFormat()
    if len(number) == 10:
        if calc_company_check_digit(number) != number[-1]:
            raise InvalidChecksum()
    elif len(number) == 12:
        # persons
        if calc_personal_check_digits(number) != number[-2:]:
            raise InvalidChecksum()
    else:
        raise InvalidLength()
    return number


def is_valid(number):
    """Check if the number is a valid ИНН."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False
