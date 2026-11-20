# nit.py - functions for handling El Salvador NIT numbers
# coding: utf-8
#
# Copyright (C) 2020 Leandro Regueiro
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

"""NIT (Número de Identificación Tributaria, El Salvador tax number).

This number consists of 14 digits, usually separated into four groups
using hyphens to make it easier to read, like XXXX-XXXXXX-XXX-X.

The first four digits indicate the code for the municipality of birth
for natural persons or the municipality of stablishment for juridical
persons. NIT for El Salvador nationals begins with either 0 or 1, and
for foreigners it begins with 9.

The following six digits indicate the date of birth for the natural
person, or the stablishment date for the juridical person, using the
format DDMMYY, where DD is the day, MM is the month, and YY is the
year. For example XXXX-051180-XXX-X is (November 5 1980)

The next 3 digits are a sequential number.

The last digit is the check digit, which is used to verify the number
was correctly typed.

More information:

* https://es.wikipedia.org/wiki/Identificaci%C3%B3n_tributaria
* https://www.listasal.info/articulos/nit-el-salvador.shtml
* https://tramitesyrequisitos.com/el-salvador/nit/#Estructura_del_NIT
* https://www.svcommunity.org/forum/programacioacuten/como-calcular-digito-verificador-del-dui-y-nit/msg951882/#msg951882

>>> validate('0614-050707-104-8')
'06140507071048'
>>> validate('SV 0614-050707-104-8')
'06140507071048'
>>> validate('0614-050707-104-0')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> validate('12345678')
Traceback (most recent call last):
    ...
InvalidLength: ...
>>> format('06140507071048')
'0614-050707-104-8'
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation.

    This strips the number of any valid separators and removes surrounding
    whitespace.
    """
    number = clean(number, ' -').upper().strip()
    if number.startswith('SV'):
        return number[2:]
    return number


def calc_check_digit(number):
    """Calculate the check digit."""
    # Old NIT
    if number[10:13] <= '100':
        weights = (14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2)
        total = sum(int(n) * w for n, w in zip(number, weights))
        return str((total % 11) % 10)
    # New NIT
    weights = (2, 7, 6, 5, 4, 3, 2, 7, 6, 5, 4, 3, 2)
    total = sum(int(n) * w for n, w in zip(number, weights))
    return str((-total % 11) % 10)


def validate(number):
    """Check if the number is a valid El Salvador NIT number.

    This checks the length, formatting and check digit.
    """
    number = compact(number)
    if len(number) != 14:
        raise InvalidLength()
    if not isdigits(number):
        raise InvalidFormat()
    if number[0] not in ('0', '1', '9'):
        raise InvalidComponent()
    if number[-1] != calc_check_digit(number):
        raise InvalidChecksum()
    return number


def is_valid(number):
    """Check if the number is a valid El Salvador NIT number."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    number = compact(number)
    return '-'.join([number[:4], number[4:-4], number[-4:-1], number[-1]])
