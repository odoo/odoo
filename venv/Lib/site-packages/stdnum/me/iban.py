# iban.py - functions for handling Montenegro IBANs
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

"""Montenegro IBAN (International Bank Account Number).

The IBAN is used to identify bank accounts across national borders. The
Montenegro IBAN is built up of the IBAN prefix (ME) and check digits,
followed by a 3 digit bank identifier, a 13 digit account number and 2 more
check digits.

>>> validate('ME 2551 0000 0000 0623 4133')
'ME25510000000006234133'
>>> validate('ME52510000000006234132')  # incorrect national check digits
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> validate('GR1601101050000010547023795')  # not a Montenegro IBAN
Traceback (most recent call last):
    ...
InvalidComponent: ...
"""

from stdnum import iban
from stdnum.exceptions import *


__all__ = ['compact', 'format', 'validate', 'is_valid']


compact = iban.compact
format = iban.format


def _checksum(number):
    """Calculate the check digits over the provided part of the number."""
    return int(number) % 97


def validate(number):
    """Check if the number provided is a valid Montenegro IBAN."""
    number = iban.validate(number, check_country=False)
    if not number.startswith('ME'):
        raise InvalidComponent()
    if _checksum(number[4:]) != 1:
        raise InvalidChecksum()
    return number


def is_valid(number):
    """Check if the number provided is a valid Montenegro IBAN."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False
