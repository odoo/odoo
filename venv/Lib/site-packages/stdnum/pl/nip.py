# nip.py - functions for handling Polish VAT numbers
#
# Copyright (C) 2012-2015 Arthur de Jong
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

"""NIP (Numer Identyfikacji Podatkowej, Polish VAT number).

The NIP (Numer Identyfikacji Podatkowej) number consists of 10 digit with
a straightforward weighted checksum.

>>> validate('PL 8567346215')
'8567346215'
>>> validate('PL 8567346216')  # invalid check digits
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> format('PL 8567346215')
'856-734-62-15'
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    number = clean(number, ' -').upper().strip()
    if number.startswith('PL'):
        number = number[2:]
    return number


def checksum(number):
    """Calculate the checksum."""
    weights = (6, 5, 7, 2, 3, 4, 5, 6, 7, -1)
    return sum(w * int(n) for w, n in zip(weights, number)) % 11


def validate(number):
    """Check if the number is a valid VAT number. This checks the length,
    formatting and check digit."""
    number = compact(number)
    if not isdigits(number):
        raise InvalidFormat()
    if len(number) != 10:
        raise InvalidLength()
    if checksum(number) != 0:
        raise InvalidChecksum()
    return number


def is_valid(number):
    """Check if the number is a valid VAT number."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    number = compact(number)
    return '-'.join((number[0:3], number[3:6], number[6:8], number[8:]))
