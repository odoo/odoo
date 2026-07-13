# tva.py - functions for handling French TVA numbers
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

"""n° TVA (taxe sur la valeur ajoutée, French VAT number).

The n° TVA (Numéro d'identification à la taxe sur la valeur ajoutée) is the
SIREN (Système d’Identification du Répertoire des Entreprises) prefixed by
two digits. In old style numbers the two digits are numeric, with new
style numbers at least one is a alphabetic.

>>> compact('Fr 40 303 265 045')
'40303265045'
>>> validate('23334175221')
'23334175221'
>>> validate('84 323 140 391')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> validate('K7399859412')  # new-style number
'K7399859412'
>>> validate('4Z123456782')  # new-style number starting with digit
'4Z123456782'
>>> validate('IO334175221')   # the letters cannot by I or O
Traceback (most recent call last):
    ...
InvalidFormat: ...
"""

from stdnum.exceptions import *
from stdnum.fr import siren
from stdnum.util import clean, isdigits


# the valid characters for the first two digits (O and I are missing)
_alphabet = '0123456789ABCDEFGHJKLMNPQRSTUVWXYZ'


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    number = clean(number, ' -.').upper().strip()
    if number.startswith('FR'):
        number = number[2:]
    return number


def validate(number):
    """Check if the number is a valid VAT number. This checks the length,
    formatting and check digit."""
    number = compact(number)
    if not all(x in _alphabet for x in number[:2]):
        raise InvalidFormat()
    if not isdigits(number[2:]):
        raise InvalidFormat()
    if len(number) != 11:
        raise InvalidLength()
    if number[2:5] != '000':
        # numbers from Monaco are valid TVA but not SIREN
        siren.validate(number[2:])
    if isdigits(number):
        # all-numeric digits
        if int(number[:2]) != (int(number[2:] + '12') % 97):
            raise InvalidChecksum()
    else:
        # one of the first two digits isn't a number
        if isdigits(number[0]):
            check = (
                _alphabet.index(number[0]) * 24 +
                _alphabet.index(number[1]) - 10)
        else:
            check = (
                _alphabet.index(number[0]) * 34 +
                _alphabet.index(number[1]) - 100)
        if (int(number[2:]) + 1 + check // 11) % 11 != (check % 11):
            raise InvalidChecksum()
    return number


def is_valid(number):
    """Check if the number is a valid VAT number."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False
