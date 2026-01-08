# iban.py - functions for handling Spanish IBANs
# coding: utf-8
#
# Copyright (C) 2016 Arthur de Jong
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

"""Spanish IBAN (International Bank Account Number).

The IBAN is used to identify bank accounts across national borders. The
Spanish IBAN is built up of the IBAN prefix (ES) and check digits, followed
by the 20 digit CCC (Código Cuenta Corriente).

>>> validate('ES77 1234-1234-16 1234567890')
'ES7712341234161234567890'
>>> to_ccc('ES77 1234-1234-16 1234567890')
'12341234161234567890'
>>> format('ES771234-1234-16 1234567890')
'ES77 1234 1234 1612 3456 7890'
>>> validate('GR1601101050000010547023795')  # different country
Traceback (most recent call last):
    ...
InvalidComponent: ...
>>> validate('ES12 1234-1234-16 1234567890')  # invalid IBAN check digit
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> validate('ES15 1234-1234-17 1234567890')  # invalid CCC check digit
Traceback (most recent call last):
    ...
InvalidChecksum: ...
"""

from stdnum import iban
from stdnum.es import ccc
from stdnum.exceptions import *


__all__ = ['compact', 'format', 'to_ccc', 'validate', 'is_valid']


compact = iban.compact
format = iban.format


def to_ccc(number):
    """Return the CCC (Código Cuenta Corriente) part of the number."""
    number = compact(number)
    if not number.startswith('ES'):
        raise InvalidComponent()
    return number[4:]


def validate(number):
    """Check if the number provided is a valid Spanish IBAN."""
    number = iban.validate(number, check_country=False)
    ccc.validate(to_ccc(number))
    return number


def is_valid(number):
    """Check if the number provided is a valid Spanish IBAN."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False
