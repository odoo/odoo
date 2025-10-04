# iban.py - functions for handling Norwegian IBANs
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

"""Norwegian IBAN (International Bank Account Number).

The IBAN is used to identify bank accounts across national borders. The
Norwegian IBAN is built up of the IBAN prefix (NO) and check digits, followed
by the 11 digit Konto nr. (bank account number).

>>> validate('NO93 8601 1117 947')
'NO9386011117947'
>>> to_kontonr('NO93 8601 1117 947')
'86011117947'
>>> format('NO9386011117947')
'NO93 8601 1117 947'
>>> validate('GR1601101050000010547023795')  # different country
Traceback (most recent call last):
    ...
InvalidComponent: ...
>>> validate('NO92 8601 1117 947')  # invalid IBAN check digit
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> validate('NO23 8601 1117 946')  # invalid Konto nr. check digit
Traceback (most recent call last):
    ...
InvalidChecksum: ...
"""

from stdnum import iban
from stdnum.exceptions import *
from stdnum.no import kontonr


__all__ = ['compact', 'format', 'to_kontonr', 'validate', 'is_valid']


compact = iban.compact
format = iban.format


def to_kontonr(number):
    """Return the Norwegian bank account number part of the number."""
    number = compact(number)
    if not number.startswith('NO'):
        raise InvalidComponent()
    return number[4:]


def validate(number):
    """Check if the number provided is a valid Norwegian IBAN."""
    number = iban.validate(number, check_country=False)
    kontonr.validate(to_kontonr(number))
    return number


def is_valid(number):
    """Check if the number provided is a valid Norwegian IBAN."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False
