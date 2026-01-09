# cui.py - functions for handling Peruvian personal numbers
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

"""CUI (Cédula Única de Identidad, Peruvian identity number).

The Cédula Única de Identidad (CUI) is the unique identifier for persons that
appears on the Documento Nacional de Identidad (DNI), the national identity
document of Peru. The number consists of 8 digits and an optional extra check
digit.

More information:

* https://www.gob.pe/235-documento-nacional-de-identidad-dni
* https://es.wikipedia.org/wiki/Documento_Nacional_de_Identidad_(Perú)

>>> validate('10117410')
'10117410'
>>> validate('10117410-2')
'101174102'
>>> validate('10117410-3')  # invalid check digit
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> to_ruc('10117410-2')
'10101174102'
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, ' -').strip().upper()


def calc_check_digits(number):
    """Calculate the possible check digits for the CUI."""
    number = compact(number)
    weights = (3, 2, 7, 6, 5, 4, 3, 2)
    c = sum(w * int(n) for w, n in zip(weights, number)) % 11
    return '65432110987'[c] + 'KJIHGFEDCBA'[c]


def to_ruc(number):
    """Convert the number to a valid RUC."""
    from stdnum.pe import ruc
    number = '10' + compact(number)[:8]
    return number + ruc.calc_check_digit(number)


def validate(number):
    """Check if the number provided is a valid CUI. This checks the length,
    formatting and check digit."""
    number = compact(number)
    if len(number) not in (8, 9):
        raise InvalidLength()
    if not isdigits(number[:8]):
        raise InvalidFormat()
    if len(number) > 8 and number[-1] not in calc_check_digits(number):
        raise InvalidChecksum()
    return number


def is_valid(number):
    """Check if the number provided is a valid CUI. This checks the length,
    formatting and check digit."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False
