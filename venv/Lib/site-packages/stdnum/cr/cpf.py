# cpf.py - functions for handling Costa Rica CPF numbers
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

"""CPF (Cédula de Persona Física, Costa Rica physical person ID number).

The Cédula de Persona Física (CPF), also known as Cédula de Identidad is an
identifier of physical persons.

The number consists of 10 digits in the form 0P-TTTT-AAAA where P represents
the province, TTTT represents the volume (tomo) padded with zeroes on the
left, and AAAA represents the entry (asiento) also padded with zeroes on the
left.

It seems to be usual for the leading zeroes in each of the three parts to be
omitted.

More information:

* https://www.hacienda.go.cr/consultapagos/ayuda_cedulas.htm
* https://www.procomer.com/downloads/quiero/guia_solicitud_vuce.pdf (page 11)
* https://www.hacienda.go.cr/ATV/frmConsultaSituTributaria.aspx

>>> validate('3-0455-0175')
'0304550175'
>>> validate('30-1234-1234')
Traceback (most recent call last):
    ...
InvalidComponent: ...
>>> validate('12345678')
Traceback (most recent call last):
    ...
InvalidLength: ...
>>> format('701610395')
'07-0161-0395'
>>> format('1-613-584')
'01-0613-0584'
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation.

    This strips the number of any valid separators and removes surrounding
    whitespace. Also adds padding zeroes if necessary.
    """
    number = clean(number, ' ').upper().strip()
    parts = number.split('-')
    if len(parts) == 3:
        # Pad each group with zeroes
        parts[0] = parts[0].zfill(2)
        parts[1] = parts[1].zfill(4)
        parts[2] = parts[2].zfill(4)
    number = ''.join(parts)
    if len(number) == 9:
        number = '0' + number  # Add leading zero
    return number


def validate(number):
    """Check if the number is a valid Costa Rica CPF number.

    This checks the length and formatting.
    """
    number = compact(number)
    if len(number) != 10:
        raise InvalidLength()
    if not isdigits(number):
        raise InvalidFormat()
    if number[0] != '0':
        raise InvalidComponent()
    return number


def is_valid(number):
    """Check if the number is a valid Costa Rica CPF number."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    number = compact(number)
    return '-'.join([number[:2], number[2:6], number[6:]])
