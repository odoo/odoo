# cr.py - functions for handling Costa Rica DIMEX numbers
# coding: utf-8
#
# Copyright (C) 2019 Leandro Regueiro
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

"""CR (Cédula de Residencia, Costa Rica foreigners ID number).

The Cédula de Residencia (CR), also know as DIMEX or Documento de
Identificación Migratorio para Extranjeros, is an identifier of foreigners in
Costa Rica.

This number consists of 11 or 12 digits in the form 1NNN-CC...C-EE...E where
NNN represents the code of the country the foreigner comes from as specified
by Costa Rica's Dirección General de Migración y Extranjería, CC...C is a
sequence telling how many Cédula de Residencia have been issued in total and
EE...E is a sequence telling how many Cédula de Residencia have been issued
for that particular foreign country.

More information:

* https://www.hacienda.go.cr/consultapagos/ayuda_cedulas.htm
* https://www.procomer.com/downloads/quiero/guia_solicitud_vuce.pdf (page 12)
* https://www.hacienda.go.cr/ATV/frmConsultaSituTributaria.aspx

>>> validate('155812994816')
'155812994816'
>>> validate('30123456789')
Traceback (most recent call last):
    ...
InvalidComponent: ...
>>> validate('12345678')
Traceback (most recent call last):
    ...
InvalidLength: ...
>>> format('122200569906')
'122200569906'
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation.

    This strips the number of any valid separators and removes surrounding
    whitespace.
    """
    return clean(number, ' -').upper().strip()


def validate(number):
    """Check if the number is a valid Costa Rica CR number.

    This checks the length and formatting.
    """
    number = compact(number)
    if len(number) not in (11, 12):
        raise InvalidLength()
    if not isdigits(number):
        raise InvalidFormat()
    if number[0] != '1':
        raise InvalidComponent()
    return number


def is_valid(number):
    """Check if the number is a valid Costa Rica CR number."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    return compact(number)
