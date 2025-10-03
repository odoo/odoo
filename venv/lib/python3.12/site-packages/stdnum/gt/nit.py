# nit.py - functions for handling Guatemala NIT numbers
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

"""NIT (Número de Identificación Tributaria, Guatemala tax number).

The Número de Identificación Tributaria (NIT) is an identifier of legal
entities for tax purposes in Guatemala.

The number consists of 2 to 12 characters, where the last one is the check
digit (a digit or the letter K) and the rest are digits. Leading zeroes are
usually omitted. Digits and check digit are usually separated with a hyphen.

More information:

* https://portal.sat.gob.gt/portal/descarga/6524/factura-electronica-fel/25542/fel-reglas-y-validaciones.pdf (page 58)
* https://portal.sat.gob.gt/portal/consulta-cui-nit/

>>> validate('576937-K')
'576937K'
>>> validate('7108-0')
'71080'
>>> validate('8977112-0')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> validate('1234567890123')
Traceback (most recent call last):
    ...
InvalidLength: ...
>>> format('39525503')
'3952550-3'
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, ' -').upper().strip().lstrip('0')


def calc_check_digit(number):
    """Calculate the check digit. The number passed should not have the
    check digit included."""
    c = -sum(i * int(n) for i, n in enumerate(reversed(number), 2)) % 11
    return 'K' if c == 10 else str(c)


def validate(number):
    """Check if the number is a valid Guatemala NIT number.

    This checks the length, formatting and check digit.
    """
    number = compact(number)
    if len(number) < 2 or len(number) > 12:
        raise InvalidLength()
    if not isdigits(number[:-1]):
        raise InvalidFormat()
    if number[-1] != 'K' and not isdigits(number[-1]):
        raise InvalidFormat()
    if number[-1] != calc_check_digit(number[:-1]):
        raise InvalidChecksum()
    return number


def is_valid(number):
    """Check if the number is a valid Guatemala NIT number."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    number = compact(number)
    return '-'.join([number[:-1], number[-1]])
