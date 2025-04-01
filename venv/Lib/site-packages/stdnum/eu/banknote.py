# banknote.py - functions for handling Euro banknote serial numbers
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

"""Euro banknote serial numbers.

The serial number consists of one letter and 11 digits, or two letters and 10
digits for the new series banknotes.

More information:

* https://en.wikipedia.org/wiki/Euro_banknotes#Serial_number

>>> validate('P36007033744')
'P36007033744'
>>> validate('P36007033743')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, ' ').upper().strip()


def checksum(number):
    """Calculate the checksum over the number."""
    # replace letters by their ASCII number
    return sum(int(x) if isdigits(x) else ord(x) for x in number) % 9


def validate(number):
    """Check if the number is a valid banknote serial number."""
    number = compact(number)
    if not number[:2].isalnum() or not isdigits(number[2:]):
        raise InvalidFormat()
    if len(number) != 12:
        raise InvalidLength()
    if number[0] not in 'BCDEFGHJLMNPRSTUVWXYZ':
        raise InvalidComponent()
    if checksum(number) != 0:
        raise InvalidChecksum()
    return number


def is_valid(number):
    """Check if the number is a valid banknote serial number."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False
