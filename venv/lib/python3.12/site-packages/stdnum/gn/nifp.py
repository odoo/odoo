# nifp.py - functions for handling Guinea NIFp numbers
# coding: utf-8
#
# Copyright (C) 2023 Leandro Regueiro
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

"""NIFp (Numéro d'Identification Fiscale Permanent, Guinea tax number).

This number consists of 9 digits, usually separated into three groups using
hyphens to make it easier to read. The first eight digits are assigned in a
pseudorandom manner. The last digit is the check digit.

More information:

* https://dgi.gov.gn/wp-content/uploads/2022/09/N%C2%B0-12-Cahier-de-Charges-NIF-p.pdf

>>> validate('693770885')
'693770885'
>>> validate('693-770-885')
'693770885'
>>> validate('12345')
Traceback (most recent call last):
    ...
InvalidLength: ...
>>> validate('693770880')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> format('693770885')
'693-770-885'
"""

from stdnum import luhn
from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation.

    This strips the number of any valid separators and removes surrounding
    whitespace.
    """
    return clean(number, ' -').strip()


def validate(number):
    """Check if the number is a valid Guinea NIFp number.

    This checks the length, formatting and check digit.
    """
    number = compact(number)
    if len(number) != 9:
        raise InvalidLength()
    if not isdigits(number):
        raise InvalidFormat()
    luhn.validate(number)
    return number


def is_valid(number):
    """Check if the number is a valid Guinea NIFp number."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    number = compact(number)
    return '-'.join([number[:3], number[3:-3], number[-3:]])
