# eic.py - functions for handling EU EIC numbers
# coding: utf-8
#
# Copyright (C) 2017 Arthur de Jong
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

"""EIC (European Energy Identification Code).

The EIC (Energy Identification Code) a 16 character code used in Europe to
uniquely identify entities and objects in the electricity and gas sector.

The number uses letters, digits and the minus sign. The first 2 character
identify the issuing office, 1 character for the object type, 12 digits for
the object and 1 check character.

More information:

* https://en.wikipedia.org/wiki/Energy_Identification_Code
* https://www.entsoe.eu/data/energy-identification-codes-eic/

>>> validate('22XWATTPLUS----G')
'22XWATTPLUS----G'
>>> validate('22XWATTPLUS----X')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> validate('23X--130302DLGW-')  # check digit cannot be minus
Traceback (most recent call last):
    ...
InvalidFormat: ...
"""

from stdnum.exceptions import *
from stdnum.util import clean


_alphabet = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ-'


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding white space."""
    return clean(number, ' ').strip()


def calc_check_digit(number):
    """Calculate the check digit for the number."""
    number = compact(number)
    s = sum((16 - i) * _alphabet.index(n) for i, n in enumerate(number[:15]))
    return _alphabet[36 - ((s - 1) % 37)]


def validate(number):
    """Check if the number is valid. This checks the length, format and check
    digit."""
    number = compact(number)
    if not all(x in _alphabet for x in number):
        raise InvalidFormat()
    if len(number) != 16:
        raise InvalidLength()
    if number[-1] == '-':
        raise InvalidFormat()
    if number[-1] != calc_check_digit(number):
        raise InvalidChecksum()
    return number


def is_valid(number):
    """Check if the number is valid. This checks the length, format and check
    digit."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False
