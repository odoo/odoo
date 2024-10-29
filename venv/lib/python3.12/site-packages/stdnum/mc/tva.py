# tva.py - functions for handling Monacan TVA numbers
# coding: utf-8
#
# Copyright (C) 2017 Arthur de Jong
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

"""n° TVA (taxe sur la valeur ajoutée, Monacan VAT number).

For VAT purposes Monaco is treated as territory of France. The number is
also validated the same as the French TVA, except that it is not based on
a French SIREN.

>>> compact('53 0000 04605')
'FR53000004605'
>>> validate('53 0000 04605')
'FR53000004605'
>>> validate('FR 61 954 506 077')  # French numbers are invalid
Traceback (most recent call last):
    ...
InvalidComponent: ...
"""

from stdnum.exceptions import *
from stdnum.fr import tva


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return 'FR' + tva.compact(number)


def validate(number):
    """Check if the number is a valid VAT number. This checks the length,
    formatting and check digit."""
    number = tva.validate(number)
    if number[2:5] != '000':
        raise InvalidComponent()
    return 'FR' + number


def is_valid(number):
    """Check if the number is a valid VAT number."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False
