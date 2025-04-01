# ruc.py - functions for handling Ecuadorian fiscal numbers
# coding: utf-8
#
# Copyright (C) 2014 Jonathan Finlay
# Copyright (C) 2014-2015 Arthur de Jong
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

"""RUC (Registro Único de Contribuyentes, Ecuadorian company tax number).

The RUC is a tax identification number for legal entities. It has 13 digits
where the third digit is a number denoting the type of entity.

>>> validate('1792060346-001')
'1792060346001'
>>> validate('1763154690001')  # invalid check digit
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> validate('179206034601')  # too short
Traceback (most recent call last):
    ...
InvalidLength: ...
"""

from stdnum.ec import ci
from stdnum.exceptions import *
from stdnum.util import isdigits


__all__ = ['compact', 'validate', 'is_valid']


# use the same compact function as CI
compact = ci.compact


def _checksum(number, weights):
    """Calculate a checksum over the number given the weights."""
    return sum(w * int(n) for w, n in zip(weights, number)) % 11


def validate(number):
    """Check if the number provided is a valid RUC number. This checks the
    length, formatting, check digit and check sum."""
    number = compact(number)
    if len(number) != 13:
        raise InvalidLength()
    if not isdigits(number):
        raise InvalidFormat()
    if (number[:2] < '01' or number[:2] > '24') and (number[:2] not in ('30', '50')):
        raise InvalidComponent()  # invalid province code
    if number[2] < '6':
        # 0..5 = natural RUC: CI plus establishment number
        if number[-3:] == '000':
            raise InvalidComponent()  # establishment number wrong
        ci.validate(number[:10])
    elif number[2] == '6':
        # 6 = public RUC
        if number[-4:] == '0000':
            raise InvalidComponent()  # establishment number wrong
        if _checksum(number[:9], (3, 2, 7, 6, 5, 4, 3, 2, 1)) != 0:
            raise InvalidChecksum()
    elif number[2] == '9':
        # 9 = juridical RUC
        if number[-3:] == '000':
            raise InvalidComponent()  # establishment number wrong
        if _checksum(number[:10], (4, 3, 2, 7, 6, 5, 4, 3, 2, 1)) != 0:
            raise InvalidChecksum()
    else:
        raise InvalidComponent()  # third digit wrong
    return number


def is_valid(number):
    """Check if the number provided is a valid RUC number. This checks the
    length, formatting and check digit."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False
