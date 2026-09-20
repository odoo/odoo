# rut.py - functions for handling Uruguay RUT numbers
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

"""RUT (Registro Único Tributario, Uruguay tax number).

The Registro Único Tributario (RUT) is an identifier of legal entities for
tax purposes.

This number consists of 12 digits, the first two indicate the registration
number, followed by a 6 digit sequence number, followed by 001 and a check
digit.

More information:

* https://www.agesic.gub.uy/innovaportal/file/1634/1/modelo_de_datos.pdf (page 71)
* https://servicios.dgi.gub.uy/ServiciosEnLinea/dgi--servicios-en-linea--consulta-de-certifcado-unico

>>> validate('21-100342-001-7')
'211003420017'
>>> validate('UY 21 140634 001 1')
'211406340011'
>>> validate('210303670014')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> validate('12345678')
Traceback (most recent call last):
    ...
InvalidLength: ...
>>> format('211003420017')
'21-100342-001-7'
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


# There are various online validation services available but they require
# registration and WS-Securety signatures.
# https://www.agesic.gub.uy/innovaportal/v/1600/9/agesic/consulta-de-entidad-por-rut.html
# https://servicios.dgi.gub.uy/ServiciosEnLinea/ampliar/servicios-automatizados


def compact(number):
    """Convert the number to the minimal representation.

    This strips the number of any valid separators and removes surrounding
    whitespace.
    """
    number = clean(number, ' -').upper().strip()
    if number.startswith('UY'):
        return number[2:]
    return number


def calc_check_digit(number):
    """Calculate the check digit."""
    weights = (4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
    total = sum(int(n) * w for w, n in zip(weights, number))
    return str(-total % 11)


def validate(number):
    """Check if the number is a valid Uruguay RUT number.

    This checks the length, formatting and check digit.
    """
    number = compact(number)
    if len(number) != 12:
        raise InvalidLength()
    if not isdigits(number):
        raise InvalidFormat()
    if number[:2] < '01' or number[:2] > '21':
        raise InvalidComponent()
    if number[2:8] == '000000':
        raise InvalidComponent()
    if number[8:11] != '001':
        raise InvalidComponent()
    if number[-1] != calc_check_digit(number):
        raise InvalidChecksum()
    return number


def is_valid(number):
    """Check if the number is a valid Uruguay RUT number."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    number = compact(number)
    return '-'.join([number[:2], number[2:-4], number[-4:-1], number[-1]])
