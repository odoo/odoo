# nif.py - functions for handling Spanish NIF (VAT) numbers
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

"""NIF (Número de Identificación Fiscal, Spanish VAT number).

The Spanish VAT number is a 9-digit number where either the first, last
digits or both can be letters.

The number is either a DNI (Documento Nacional de Identidad, for
Spaniards), a NIE (Número de Identificación de Extranjero, for
foreigners) or a CIF (Código de Identificación Fiscal, for legal
entities and others).

>>> compact('ES B-58378431')
'B58378431'
>>> validate('B64717838')
'B64717838'
>>> validate('B64717839')  # invalid check digit
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> validate('54362315K')  # resident
'54362315K'
>>> validate('X-5253868-R')  # foreign person
'X5253868R'
>>> validate('M-1234567-L')  # foreign person without NIE
'M1234567L'
"""

from stdnum.es import cif, dni, nie
from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    number = clean(number, ' -').upper().strip()
    if number.startswith('ES'):
        number = number[2:]
    return number


def validate(number):
    """Check if the number provided is a valid VAT number. This checks the
    length, formatting and check digit."""
    number = compact(number)
    if not isdigits(number[1:-1]):
        raise InvalidFormat()
    if len(number) != 9:
        raise InvalidLength()
    if number[0] in 'KLM':
        # K: Spanish younger than 14 year old
        # L: Spanish living outside Spain without DNI
        # M: granted the tax to foreigners who have no NIE
        # these use the old checkdigit algorithm (the DNI one)
        if number[-1] != dni.calc_check_digit(number[1:-1]):
            raise InvalidChecksum()
    elif isdigits(number[0]):
        # natural resident
        dni.validate(number)
    elif number[0] in 'XYZ':
        # foreign natural person
        nie.validate(number)
    else:
        # otherwise it has to be a valid CIF
        cif.validate(number)
    return number


def is_valid(number):
    """Check if the number provided is a valid VAT number. This checks the
    length, formatting and check digit."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False
