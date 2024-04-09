# tin.py - functions for handling South Africa Tax Reference Number
# coding: utf-8
#
# Copyright (C) 2019 Leandro Regueiro
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

"""TIN (South African Tax Identification Number).

The South African Tax Identification Number (TIN or Tax Reference Number) is
issued to individuals and legal entities for tax purposes. The number
consists of 10 digits.

More information:

* https://www.oecd.org/tax/automatic-exchange/crs-implementation-and-assistance/tax-identification-numbers/South-Africa-TIN.pdf
* https://www.sars.gov.za/

>>> validate('0001339050')
'0001339050'
>>> validate('2449/494/16/0')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> validate('9125568')
Traceback (most recent call last):
    ...
InvalidLength: ...
>>> format('084308984-8')
'0843089848'
"""

from stdnum import luhn
from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation.

    This strips the number of any valid separators and removes surrounding
    whitespace.
    """
    return clean(number, ' -/').upper().strip()


def validate(number):
    """Check if the number is a valid South Africa Tax Reference Number.

    This checks the length, formatting and check digit.
    """
    number = compact(number)
    if len(number) != 10:
        raise InvalidLength()
    if not isdigits(number):
        raise InvalidFormat()
    if number[0] not in '01239':
        raise InvalidComponent()
    return luhn.validate(number)


def is_valid(number):
    """Check if the number is a valid South Africa Tax Reference Number."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    return compact(number)
