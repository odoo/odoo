# cif.py - functions for handling Spanish fiscal numbers
# coding: utf-8
#
# Copyright (C) 2012, 2013 Arthur de Jong
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

"""CIF (Código de Identificación Fiscal, Spanish company tax number).

The CIF is a tax identification number for legal entities. It has 9 digits
where the first digit is a letter (denoting the type of entity) and the
last is a check digit (which may also be a letter).

More information

* https://es.wikipedia.org/wiki/Código_de_identificación_fiscal

>>> validate('J99216582')
'J99216582'
>>> validate('J99216583')  # invalid check digit
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> validate('J992165831')  # too long
Traceback (most recent call last):
    ...
InvalidLength: ...
>>> validate('M-1234567-L')  # valid NIF but not valid CIF
Traceback (most recent call last):
    ...
InvalidFormat: ...
>>> validate('O-1234567-L')  # invalid first character
Traceback (most recent call last):
    ...
InvalidFormat: ...
>>> split('A13 585 625')
('A', '13', '58562', '5')
"""

from stdnum import luhn
from stdnum.es import dni
from stdnum.exceptions import *
from stdnum.util import isdigits


__all__ = ['compact', 'validate', 'is_valid', 'split']


# use the same compact function as DNI
compact = dni.compact


def calc_check_digits(number):
    """Calculate the check digits for the specified number. The number
    passed should not have the check digit included. This function returns
    both the number and character check digit candidates."""
    check = luhn.calc_check_digit(number[1:])
    return check + 'JABCDEFGHI'[int(check)]


def validate(number):
    """Check if the number provided is a valid DNI number. This checks the
    length, formatting and check digit."""
    number = compact(number)
    if not isdigits(number[1:-1]):
        raise InvalidFormat()
    if len(number) != 9:
        raise InvalidLength()
    if number[0] in 'ABCDEFGHJNPQRSUVW':
        # there seems to be conflicting information on which organisation types
        # should have which type of check digit (alphabetic or numeric) so
        # we support either here
        if number[-1] not in calc_check_digits(number[:-1]):
            raise InvalidChecksum()
    else:
        # anything else is invalid
        raise InvalidFormat()
    return number


def is_valid(number):
    """Check if the number provided is a valid DNI number. This checks the
    length, formatting and check digit."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def split(number):
    """Split the provided number into a letter to define the type of
    organisation, two digits that specify a province, a 5 digit sequence
    number within the province and a check digit."""
    number = compact(number)
    return number[0], number[1:3], number[3:8], number[8:]
