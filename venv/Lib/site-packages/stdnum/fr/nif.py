# nif.py - functions for handling French tax identification numbers
# coding: utf-8
#
# Copyright (C) 2016-2021 Dimitri Papadopoulos
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

"""NIF (Numéro d'Immatriculation Fiscale, French tax identification number).

The NIF (Numéro d'Immatriculation Fiscale or Numéro d'Identification Fiscale)
also known as numéro fiscal de référence or SPI (Simplification des
Procédures d'Identification) is a 13-digit number issued by the French tax
authorities to people for tax reporting purposes.

More information:

* https://ec.europa.eu/taxation_customs/tin/tinByCountry.html
* https://fr.wikipedia.org/wiki/Numéro_d%27Immatriculation_Fiscale#France

>>> validate('0701987765432')
'0701987765432'
>>> validate('070198776543')
Traceback (most recent call last):
    ...
InvalidLength: ...
>>> validate('9701987765432')
Traceback (most recent call last):
    ...
InvalidComponent: ...
>>> format('0701987765432')
'07 01 987 765 432'
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, ' ').strip()


def validate(number):
    """Check if the number provided is a valid NIF."""
    number = compact(number)
    if not isdigits(number):
        raise InvalidFormat()
    if number[0] not in ('0', '1', '2', '3'):
        raise InvalidComponent()
    if len(number) != 13:
        raise InvalidLength()
    return number


def is_valid(number):
    """Check if the number provided is a valid NIF."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    number = compact(number)
    return ' '.join((number[:2], number[2:4], number[4:7],
                     number[7:10], number[10:]))
