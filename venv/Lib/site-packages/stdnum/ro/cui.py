# cui.py - functions for handling Romanian CUI and CIF numbers
# coding: utf-8
#
# Copyright (C) 2012-2020 Arthur de Jong
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

"""CUI or CIF (Codul Unic de Înregistrare, Romanian company identifier).

The CUI (Codul Unic de Înregistrare) is assigned to companies that are
required to register with the Romanian Trade Register. The CIF (Codul de
identificare fiscală) is identical but assigned to entities that have no such
requirement. The names seem to be used interchangeably and some sources
suggest that CIF is the new name for CUI.

This number can change under some conditions. The number can be prefixed with
RO to indicate that the entity has been registered for VAT.

More information:

* https://ro.wikipedia.org/wiki/Cod_de_identificare_fiscală

>>> validate('185 472 90')
'18547290'
>>> validate('185 472 91')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> validate('RO 185 472 90')  # the RO prefix is ignored
'18547290'
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    number = clean(number, ' -').upper().strip()
    if number.startswith('RO'):
        number = number[2:]
    return number


def calc_check_digit(number):
    """Calculate the check digit."""
    weights = (7, 5, 3, 2, 1, 7, 5, 3, 2)
    number = number.zfill(9)
    check = 10 * sum(w * int(n) for w, n in zip(weights, number))
    return str(check % 11 % 10)


def validate(number):
    """Check if the number is a valid CUI or CIF number. This checks the length,
    formatting and check digit."""
    number = compact(number)
    if not isdigits(number) or number[0] == '0':
        raise InvalidFormat()
    if not (2 <= len(number) <= 10):
        raise InvalidLength()
    if calc_check_digit(number[:-1]) != number[-1]:
        raise InvalidChecksum()
    return number


def is_valid(number):
    """Check if the number is a valid CUI or CIF number."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False
