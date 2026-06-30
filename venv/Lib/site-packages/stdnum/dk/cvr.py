# cvr.py - functions for handling Danish CVR numbers
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

"""CVR (Momsregistreringsnummer, Danish VAT number).

The CVR (Momsregistreringsnummer, VAT) is an 8 digit number with a
straightforward check mechanism.

>>> validate('DK 13585628')
'13585628'
>>> validate('DK 13585627')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    number = clean(number, ' -.,/:').upper().strip()
    if number.startswith('DK'):
        number = number[2:]
    return number


def checksum(number):
    """Calculate the checksum."""
    weights = (2, 7, 6, 5, 4, 3, 2, 1)
    return sum(w * int(n) for w, n in zip(weights, number)) % 11


def validate(number):
    """Check if the number provided is a valid VAT number. This checks the
    length, formatting and check digit."""
    number = compact(number)
    if not isdigits(number) or number[0] == '0':
        raise InvalidFormat()
    if len(number) != 8:
        raise InvalidLength()
    if checksum(number) != 0:
        raise InvalidChecksum()
    return number


def is_valid(number):
    """Check if the number provided is a valid VAT number. This checks the
    length, formatting and check digit."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False
