# ruc.py - functions for handling Peruvian fiscal numbers
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

"""RUC (Registro Único de Contribuyentes, Peruvian company tax number).

The RUC (Registro Único de Contribuyentes) is the tax number of Peru assigned
to legal and natural persons. The number consists of 11 digits, the first two
indicate the kind of number, for personal numbers it is followed by the DNI
and a check digit.

More information:

* https://www.sunat.gob.pe/legislacion/ruc/
* https://consultarelruc.pe/

>>> validate('20512333797')
'20512333797'
>>> validate('20512333798')  # invalid check digit
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> to_dni('10054148289')
'05414828'
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, ' ').strip()


def calc_check_digit(number):
    """Calculate the check digit."""
    weights = (5, 4, 3, 2, 7, 6, 5, 4, 3, 2)
    return str((11 - sum(w * int(n) for w, n in zip(weights, number)) % 11) % 10)


def to_dni(number):
    """Return the DNI (CUI) part of the number for natural persons."""
    number = validate(number)
    if not number.startswith('10'):
        raise InvalidComponent()  # only for persons
    return number[2:10]


def validate(number):
    """Check if the number provided is a valid RUC. This checks the length,
    formatting and check digit."""
    number = compact(number)
    if len(number) != 11:
        raise InvalidLength()
    if not isdigits(number):
        raise InvalidFormat()
    if number[:2] not in ('10', '15', '17', '20'):
        raise InvalidComponent()  # not person or company
    if not number.endswith(calc_check_digit(number)):
        raise InvalidChecksum()
    return number


def is_valid(number):
    """Check if the number provided is a valid RUC. This checks the length,
    formatting and check digit."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False
