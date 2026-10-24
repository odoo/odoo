# cpj.py - functions for handling Costa Rica CPJ numbers
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

"""CPJ (Cédula de Persona Jurídica, Costa Rica tax number).

The Cédula de Persona Jurídica (CPJ) is an identifier of legal entities for
tax purposes.

This number consists of 10 digits, the first indicates the class of juridical
person, followed by a 3 digit sequence number identifying the type of
juridical person, followed by 6 digits sequence number assigned by Registro
Nacional de la República de Costa Rica.

More information:

* https://www.hacienda.go.cr/consultapagos/ayuda_cedulas.htm
* https://www.procomer.com/downloads/quiero/guia_solicitud_vuce.pdf (page 11)
* http://www.registronacional.go.cr/personas_juridicas/documentos/Consultas/Listado%20de%20Clases%20y%20Tipos%20Cedulas%20Juridicas.pdf
* https://www.hacienda.go.cr/ATV/frmConsultaSituTributaria.aspx

>>> validate('3-101-999999')
'3101999999'
>>> validate('3-534-123559')
Traceback (most recent call last):
    ...
InvalidComponent: ...
>>> validate('310132541')
Traceback (most recent call last):
    ...
InvalidLength: ...
>>> format('4 000 042138')
'4-000-042138'
"""  # noqa: E501

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation.

    This strips the number of any valid separators and removes surrounding
    whitespace.
    """
    return clean(number, ' -').upper().strip()


def validate(number):
    """Check if the number is a valid Costa Rica CPJ number.

    This checks the length and formatting.
    """
    number = compact(number)
    if len(number) != 10:
        raise InvalidLength()
    if not isdigits(number):
        raise InvalidFormat()
    if number[0] not in ('2', '3', '4', '5'):
        raise InvalidComponent()
    if number[0] == '2' and number[1:4] not in ('100', '200', '300', '400'):
        raise InvalidComponent()
    class_three_types = ('002', '003', '004', '005', '006', '007', '008',
                         '009', '010', '011', '012', '013', '014', '101',
                         '102', '103', '104', '105', '106', '107', '108',
                         '109', '110')
    if number[0] == '3' and number[1:4] not in class_three_types:
        raise InvalidComponent()
    if number[0] == '4' and number[1:4] != '000':
        raise InvalidComponent()
    if number[0] == '5' and number[1:4] != '001':
        raise InvalidComponent()
    return number


def is_valid(number):
    """Check if the number is a valid Costa Rica CPJ number."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    number = compact(number)
    return '-'.join([number[0], number[1:4], number[4:]])
