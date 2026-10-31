# ice.py - functions for handling Morocco ICE numbers
# coding: utf-8
#
# Copyright (C) 2022 Leandro Regueiro
# Copyright (C) 2022 Arthur de Jong
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

"""ICE (Identifiant Commun de l’Entreprise, التعريف الموحد للمقاولة, Morocco tax number).

The ICE is a number that identifies the company and its branches in a unique
and uniform way by all Moroccan administrations. It comes in addition to the
other legal identifiers, notably the "identifiant fiscal" (IF), the "numéro de
registre de commerce" (RC) and the CNSS number. The ICE does not replace these
identifiers, which remain mandatory.

The ICE is intended to ease communication among Moroccan administration
branches, therefore simplifying procedures, increasing reliability and speed,
and therefore reducing costs.

The ICE applies to legal entities and their branches, as well as to natural
persons.

The ICE consists of 15 characters, where the first 9 represent the enterprise,
the following 4 represent its establishments, and the last 2 are control
characters.

More information:

* https://www.ice.gov.ma/
* https://www.ice.gov.ma/ICE/Depliant_ICE.pdf
* https://www.ice.gov.ma/ICE/Guide_ICE.pdf

>>> validate('001561191000066')
'001561191000066'
>>> validate('00 21 36 09 30 00 040')
'002136093000040'
>>> validate('12345')
Traceback (most recent call last):
    ...
InvalidLength: ...
>>> validate('001561191000065')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> format('00 21 36 09 30 00 040')
'002136093000040'
"""

from stdnum.exceptions import *
from stdnum.iso7064 import mod_97_10
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation.

    This strips the number of any valid separators, removes surrounding
    whitespace.
    """
    return clean(number, ' ')


def validate(number):
    """Check if the number is a valid Morocco ICE number.

    This checks the length and formatting.
    """
    number = compact(number)
    if len(number) != 15:
        raise InvalidLength()
    if not isdigits(number):
        raise InvalidFormat()
    if mod_97_10.checksum(number) != 0:
        raise InvalidChecksum()
    return number


def is_valid(number):
    """Check if the number is a valid Morocco ICE number."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    return compact(number).zfill(15)
