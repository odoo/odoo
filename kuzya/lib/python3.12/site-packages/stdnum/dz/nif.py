# nif.py - functions for handling Algeria NIF numbers
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

"""NIF, sometimes N.I.F. (Numéro d'Identification Fiscale, Algeria tax number).

The NIF was adopted by the Algerian tax authorities on 2006, replacing the NIS
number.

The NIF applies to physical persons, legal persons, legal entities,
administrative entities, local branches for foreign companies, associations,
professional organisations, etc.

The NIF consists of 15 digits, but sometimes it can be 20 digits long in order
to represent branches or secondary establishments.

More information:

* http://www.jecreemonentreprise.dz/index.php?option=com_content&view=article&id=612&Itemid=463&lang=fr
* https://www.mf.gov.dz/index.php/fr/fiscalite
* https://cnrcinfo.cnrc.dz/numero-didentification-fiscale-nif/
* https://nifenligne.mfdgi.gov.dz/
* http://nif.mfdgi.gov.dz/nif.asp

>>> validate('416001000000007')
'416001000000007'
>>> validate('408 020 000 150 039')
'408020000150039'
>>> validate('41201600000606600001')
'41201600000606600001'
>>> validate('000 216 001 808 337 13010')
'00021600180833713010'
>>> validate('12345')
Traceback (most recent call last):
    ...
InvalidLength: ...
>>> validate('X1600100000000V')
Traceback (most recent call last):
    ...
InvalidFormat: ...
>>> format('408 020 000 150 039')
'408020000150039'
>>> format('000 216 001 808 337 13010')
'00021600180833713010'
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation.

    This strips the number of any valid separators, removes surrounding
    whitespace.
    """
    return clean(number, ' ')


def validate(number):
    """Check if the number is a valid Algeria NIF number.

    This checks the length and formatting.
    """
    number = compact(number)
    if len(number) not in (15, 20):
        raise InvalidLength()
    if not isdigits(number):
        raise InvalidFormat()
    return number


def is_valid(number):
    """Check if the number is a valid Algeria NIF number."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    return compact(number)
