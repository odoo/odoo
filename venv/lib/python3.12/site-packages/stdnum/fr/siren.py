# siren.py - functions for handling French SIREN numbers
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

"""SIREN (a French company identification number).

The SIREN (Système d'Identification du Répertoire des Entreprises) is a 9
digit number used to identify French companies. The Luhn checksum is used
to validate the numbers.

>>> compact('552 008 443')
'552008443'
>>> validate('404833048')
'404833048'
>>> validate('404833047')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> to_tva('443 121 975')
'46 443 121 975'
"""

from stdnum import luhn
from stdnum.exceptions import *
from stdnum.util import clean, isdigits


# An online validation function is available but it does not provide an
# automated entry point, has usage restrictions and seems to require
# attribution to the service for any results used.
# https://avis-situation-sirene.insee.fr/


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, ' .').strip()


def validate(number):
    """Check if the number provided is a valid SIREN. This checks the length,
    formatting and check digit."""
    number = compact(number)
    if not isdigits(number):
        raise InvalidFormat()
    if len(number) != 9:
        raise InvalidLength()
    luhn.validate(number)
    return number


def is_valid(number):
    """Check if the number provided is a valid SIREN."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def to_tva(number):
    """Return a TVA that prepends the two extra check digits to the SIREN."""
    # note that this always returns numeric check digits
    # it is unclean when the alphabetic ones are used
    return '%02d%s%s' % (
        int(compact(number) + '12') % 97,
        ' ' if ' ' in number else '',
        number)
