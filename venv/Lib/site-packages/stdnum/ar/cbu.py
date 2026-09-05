# cbu.py - functions for handling Argentinian CBU numbers
# coding: utf-8
#
# Copyright (C) 2016 Luciano Rossi
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

"""CBU (Clave Bancaria Uniforme, Argentine bank account number).

CBU it s a code of the Banks of Argentina to identify customer accounts. The
number consists of 22 digits and consists of a 3 digit bank identifier,
followed by a 4 digit branch identifier, a check digit, a 13 digit account
identifier and another check digit.

More information:

* https://es.wikipedia.org/wiki/Clave_Bancaria_Uniforme

>>> validate('2850590940090418135201')
'2850590940090418135201'
>>> format('2850590940090418135201')
'28505909 40090418135201'
>>> validate('2810590940090418135201')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, ' -').strip()


def calc_check_digit(number):
    """Calculate the check digit."""
    weights = (3, 1, 7, 9)
    check = sum(int(n) * weights[i % 4]
                for i, n in enumerate(reversed(number)))
    return str((10 - check) % 10)


def validate(number):
    """Check if the number is a valid CBU."""
    number = compact(number)
    if len(number) != 22:
        raise InvalidLength()
    if not isdigits(number):
        raise InvalidFormat()
    if calc_check_digit(number[:7]) != number[7]:
        raise InvalidChecksum()
    if calc_check_digit(number[8:-1]) != number[-1]:
        raise InvalidChecksum()
    return number


def is_valid(number):
    """Check if the number is a valid CBU."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    number = compact(number)
    return ' '.join((number[:8], number[8:]))
