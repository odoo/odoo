# siret.py - functions for handling French SIRET numbers
# coding: utf-8
#
# Copyright (C) 2016 Yoann Aubineau
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

"""SIRET (a French company establishment identification number).

The SIRET (Système d'Identification du Répertoire des ETablissements)
is a 14 digit number used to identify French companies' establishments
and facilities. The Luhn checksum is used to validate the numbers (except
for La Poste).

More information:

* https://fr.wikipedia.org/wiki/Système_d'identification_du_répertoire_des_établissements

>>> validate('73282932000074')
'73282932000074'
>>> validate('73282932000079')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> to_siren('732 829 320 00074')
'732 829 320'
>>> to_siren('73282932000074')
'732829320'
>>> to_tva('732 829 320 00074')
'44 732 829 320'
>>> to_tva('73282932000074')
'44732829320'
>>> format('73282932000074')
'732 829 320 00074'
"""

from stdnum import luhn
from stdnum.exceptions import *
from stdnum.fr import siren
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, ' .').strip()


def validate(number):
    """Check if the number is a valid SIRET. This checks the length,
    formatting and check digit."""
    number = compact(number)
    if not isdigits(number):
        raise InvalidFormat()
    if len(number) != 14:
        raise InvalidLength()
    # La Poste SIRET (except the head office) do not use the Luhn checksum
    # but the sum of digits must be a multiple of 5
    if number.startswith('356000000') and number != '35600000000048':
        if sum(map(int, number)) % 5 != 0:
            raise InvalidChecksum()
    else:
        luhn.validate(number)
    siren.validate(number[:9])
    return number


def is_valid(number):
    """Check if the number is a valid SIRET."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def to_siren(number):
    """Convert the SIRET number to a SIREN number.

    The SIREN number is the 9 first digits of the SIRET number.
    """
    _siren = []
    digit_count = 0
    for char in number:
        if digit_count < 9:
            _siren.append(char)
            if isdigits(char):
                digit_count += 1
    return ''.join(_siren)


def to_tva(number):
    """Convert the SIRET number to a TVA number.

    The TVA number is built from the SIREN number, prepended by two extra
    error checking digits.
    """
    return siren.to_tva(to_siren(number))


def format(number, separator=' '):
    """Reformat the number to the standard presentation format."""
    number = compact(number)
    return separator.join((number[0:3], number[3:6], number[6:9], number[9:]))
