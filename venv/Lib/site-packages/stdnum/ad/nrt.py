# nrt.py - functions for handling Andorra NRT numbers
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

"""NRT (Número de Registre Tributari, Andorra tax number).

The Número de Registre Tributari (NRT) is an identifier of legal and natural
entities for tax purposes.

This number consists of one letter indicating the type of entity, then 6
digits, followed by a check letter.

More information:

* https://www.oecd.org/tax/automatic-exchange/crs-implementation-and-assistance/tax-identification-numbers/Andorra-TIN.pdf

>>> validate('U-132950-X')
'U132950X'
>>> validate('A123B')
Traceback (most recent call last):
    ...
InvalidLength: ...
>>> validate('I 706193 G')
Traceback (most recent call last):
    ...
InvalidComponent: ...
>>> format('D059888N')
'D-059888-N'
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation.

    This strips the number of any valid separators and removes surrounding
    whitespace.
    """
    return clean(number, ' -.').upper().strip()


def validate(number):
    """Check if the number is a valid Andorra NRT number.

    This checks the length, formatting and other constraints. It does not check
    for control letter.
    """
    number = compact(number)
    if len(number) != 8:
        raise InvalidLength()
    if not number[0].isalpha() or not number[-1].isalpha():
        raise InvalidFormat()
    if not isdigits(number[1:-1]):
        raise InvalidFormat()
    if number[0] not in 'ACDEFGLOPU':
        raise InvalidComponent()
    if number[0] == 'F' and number[1:-1] > '699999':
        raise InvalidComponent()
    if number[0] in 'AL' and not ('699999' < number[1:-1] < '800000'):
        raise InvalidComponent()
    return number


def is_valid(number):
    """Check if the number is a valid Andorra NRT number."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    number = compact(number)
    return '-'.join([number[0], number[1:-1], number[-1]])
