# rif.py - functions for handling Venezuelan VAT numbers
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

"""RIF (Registro de Identificación Fiscal, Venezuelan VAT number).

The Registro de Identificación Fiscal (RIF) is the Venezuelan fiscal
registration number. The number consists of 10 digits where the first digit
denotes the type of number (person, company or government) and the last digit
is a check digit.

>>> validate('V-11470283-4')
'V114702834'
>>> validate('V-11470283-3')  # invalid check digit
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


# Known number types and their corresponding value in the check
# digit calculation
_company_types = {
    'V': 4,   # natural person born in Venezuela
    'E': 8,   # foreign natural person
    'J': 12,  # company
    'P': 16,  # passport
    'G': 20,  # government
}


def calc_check_digit(number):
    """Calculate the check digit for the RIF."""
    number = compact(number)
    weights = (3, 2, 7, 6, 5, 4, 3, 2)
    c = _company_types[number[0]]
    c += sum(w * int(n) for w, n in zip(weights, number[1:9]))
    return '00987654321'[c % 11]


def validate(number):
    """Check if the number provided is a valid RIF. This checks the length,
    formatting and check digit."""
    number = compact(number)
    if len(number) != 10:
        raise InvalidLength()
    if number[0] not in _company_types:
        raise InvalidComponent()
    if not isdigits(number[1:]):
        raise InvalidFormat()
    if number[-1] != calc_check_digit(number):
        raise InvalidChecksum()
    return number


def is_valid(number):
    """Check if the number provided is a valid RIF. This checks the length,
    formatting and check digit."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False
