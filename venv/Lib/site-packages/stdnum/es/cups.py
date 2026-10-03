# cups.py - functions for handling Spanish CUPS code
# coding: utf-8
#
# Copyright (C) 2016 David García Garzón
# Copyright (C) 2016 Arthur de Jong
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

"""CUPS (Código Unificado de Punto de Suministro, Spanish meter point number).

CUPS codes are used in Spain as unique identifier for energy supply points.
They are used both for electricity and pipelined gas.

The format is set by the Energy Ministry, and individual codes are issued by
each local distribution company. The number consist or 20 or 22 digits and is
built up as follows:

* LL: (letters) country (always 'ES' since it is a national code)
* DDDD: (numbers) distribution company code (numeric)
* CCCC CCCC CCCC: identifier within the distribution company (numeric)
* EE: (letters) check digits
* N: (number) border point sequence
* T: (letter) kind of border point

More information:

* https://es.wikipedia.org/wiki/Código_Unificado_de_Punto_de_Suministro

>>> validate('ES 1234-123456789012-JY')
'ES1234123456789012JY'
>>> validate('ES 1234-123456789012-JY 1T')
Traceback (most recent call last):
    ...
InvalidFormat: ...
>>> validate('ES 1234-123456789012-XY 1F')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> format('ES1234123456789012JY1F')
'ES 1234 1234 5678 9012 JY 1F'
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, ' -').strip().upper()


def format(number):
    """Reformat the number to the standard presentation format."""
    number = compact(number)
    return ' '.join((
        number[:2],
        number[2:6],
        number[6:10],
        number[10:14],
        number[14:18],
        number[18:20],
        number[20:],
    )).strip()


def calc_check_digits(number):
    """Calculate the check digits for the number."""
    alphabet = 'TRWAGMYFPDXBNJZSQVHLCKE'
    check0, check1 = divmod(int(number[2:18]) % 529, 23)
    return alphabet[check0] + alphabet[check1]


def validate(number):
    """Check if the number provided is a valid CUPS. This checks length,
    formatting and check digits."""
    number = compact(number)
    if len(number) not in (20, 22):
        raise InvalidLength()
    if number[:2] != 'ES':
        raise InvalidComponent()
    if not isdigits(number[2:18]):
        raise InvalidFormat()
    if number[20:]:
        pnumber, ptype = number[20:]
        if not isdigits(pnumber):
            raise InvalidFormat()
        if ptype not in 'FPRCXYZ':
            raise InvalidFormat()
    if calc_check_digits(number) != number[18:20]:
        raise InvalidChecksum()
    return number


def is_valid(number):
    """Check if the number provided is a valid CUPS."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False
