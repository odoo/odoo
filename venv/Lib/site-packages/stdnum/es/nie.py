# nie.py - functions for handling Spanish foreigner identity codes
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

"""NIE (Número de Identificación de Extranjero, Spanish foreigner number).

The NIE is an identification number for foreigners. It is a 9 digit number
where the first digit is either X, Y or Z and last digit is a checksum
letter.

More information:

* https://es.wikipedia.org/wiki/N%C3%BAmero_de_identidad_de_extranjero

>>> validate('x-2482300w')
'X2482300W'
>>> validate('x-2482300a')  # invalid check digit
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> validate('X2482300')  # digit missing
Traceback (most recent call last):
    ...
InvalidLength: ...
"""

from stdnum.es import dni
from stdnum.exceptions import *
from stdnum.util import isdigits


__all__ = ['compact', 'calc_check_digit', 'validate', 'is_valid']


# use the same compact function as DNI
compact = dni.compact


def calc_check_digit(number):
    """Calculate the check digit. The number passed should not have the
    check digit included."""
    # replace XYZ with 012
    number = str('XYZ'.index(number[0])) + number[1:]
    return dni.calc_check_digit(number)


def validate(number):
    """Check if the number provided is a valid NIE. This checks the length,
    formatting and check digit."""
    number = compact(number)
    if not isdigits(number[1:-1]) or number[:1] not in 'XYZ':
        raise InvalidFormat()
    if len(number) != 9:
        raise InvalidLength()
    if calc_check_digit(number[:-1]) != number[-1]:
        raise InvalidChecksum()
    return number


def is_valid(number):
    """Check if the number provided is a valid NIE. This checks the length,
    formatting and check digit."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False
