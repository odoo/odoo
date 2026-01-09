# mf.py - functions for handling Tunisia MF numbers
# coding: utf-8
#
# Copyright (C) 2022 Leandro Regueiro
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

"""MF (Matricule Fiscal, Tunisia tax number).

The MF consists of 4 parts: the "identifiant fiscal", the "code TVA", the "code
catégorie" and the "numéro d'etablissement secondaire".

The "identifiant fiscal" consists of 2 parts: the "identifiant unique" and the
"clef de contrôle". The "identifiant unique" is composed of 7 digits. The "clef
de contrôle" is a letter, excluding "I", "O" and "U" because of their
similarity to "1", "0" and "4".

The "code TVA" is a letter that tells which VAT regime is being used. The valid
values are "A", "P", "B", "D" and "N".

The "code catégorie" is a letter that tells the category the contributor
belongs to. The valid values are "M", "P", "C", "N" and "E".

The "numéro d'etablissement secondaire" consists of 3 digits. It is usually
"000", but it can be "001", "002"... depending on the branches. If it is not
"000" then "code catégorie" must be "E".

More information:

* https://futurexpert.tn/2019/10/22/structure-et-utilite-du-matricule-fiscal/
* https://www.registre-entreprises.tn/

>>> validate('1234567/M/A/E/001')
'1234567MAE001'
>>> validate('1282182 W')
'1282182W'
>>> validate('121J')
'0000121J'
>>> validate('1219773U')
Traceback (most recent call last):
    ...
InvalidFormat: ...
>>> validate('1234567/M/A/X/000')
Traceback (most recent call last):
    ...
InvalidFormat: ...
>>> format('121J')
'0000121/J'
>>> format('1496298 T P N 000')
'1496298/T/P/N/000'
"""

import re

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


_VALID_CONTROL_KEYS = ('A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'J', 'K', 'L',
                       'M', 'N', 'P', 'Q', 'R', 'S', 'T', 'V', 'W', 'X', 'Y',
                       'Z')
_VALID_TVA_CODES = ('A', 'P', 'B', 'D', 'N')
_VALID_CATEGORY_CODES = ('M', 'P', 'C', 'N', 'E')


def compact(number):
    """Convert the number to the minimal representation.

    This strips the number of any valid separators, removes surrounding
    whitespace.
    """
    number = clean(number, ' /.-').upper()
    # Zero pad the numeric serial to length 7
    match = re.match(r'^(?P<serial>[0-9]+)(?P<rest>.*)$', number)
    if match:
        number = match.group('serial').zfill(7) + match.group('rest')
    return number


def validate(number):
    """Check if the number is a valid Tunisia MF number.

    This checks the length and formatting.
    """
    number = compact(number)
    if len(number) not in (8, 13):
        raise InvalidLength()
    if not isdigits(number[:7]):
        raise InvalidFormat()
    if number[7] not in _VALID_CONTROL_KEYS:
        raise InvalidFormat()
    if len(number) == 8:
        return number
    if number[8] not in _VALID_TVA_CODES:
        raise InvalidFormat()
    if number[9] not in _VALID_CATEGORY_CODES:
        raise InvalidFormat()
    if not isdigits(number[10:]):
        raise InvalidFormat()
    if number[10:] != '000' and number[9] != 'E':
        raise InvalidFormat()
    return number


def is_valid(number):
    """Check if the number is a valid Tunisia MF number."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    result = compact(number)
    if len(result) == 8:
        return '/'.join([result[:7], result[7]])
    return '/'.join([result[:7], result[7], result[8], result[9], result[10:]])
