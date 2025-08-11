# cpf.py - functions for handling CPF numbers
# coding: utf-8
#
# Copyright (C) 2011-2016 Arthur de Jong
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

"""CPF (Cadastro de Pessoas Físicas, Brazilian national identifier).

The Cadastro de Pessoas Físicas is the Brazilian identification number
assigned to individuals for tax purposes. The number consists of 11 digits
and includes two check digits.

More information:

* https://en.wikipedia.org/wiki/Cadastro_de_Pessoas_Físicas

>>> validate('390.533.447-05')
'39053344705'
>>> validate('231.002.999-00')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> validate('390.533.447=0')  # invalid delimiter
Traceback (most recent call last):
    ...
InvalidFormat: ...
>>> format('23100299900')
'231.002.999-00'
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, ' -.').strip()


def _calc_check_digits(number):
    """Calculate the check digits for the number."""
    d1 = sum((10 - i) * int(number[i]) for i in range(9))
    d1 = (11 - d1) % 11 % 10
    d2 = sum((11 - i) * int(number[i]) for i in range(9)) + 2 * d1
    d2 = (11 - d2) % 11 % 10
    return '%d%d' % (d1, d2)


def validate(number):
    """Check if the number is a valid CPF. This checks the length and whether
    the check digit is correct."""
    number = compact(number)
    if not isdigits(number) or int(number) <= 0:
        raise InvalidFormat()
    if len(number) != 11:
        raise InvalidLength()
    if _calc_check_digits(number) != number[-2:]:
        raise InvalidChecksum()
    return number


def is_valid(number):
    """Check if the number is a valid CPF."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    number = compact(number)
    return number[:3] + '.' + number[3:6] + '.' + number[6:-2] + '-' + number[-2:]
