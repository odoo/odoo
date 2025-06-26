# vat.py - functions for handling Belgian VAT numbers
#
# Copyright (C) 2012-2016 Arthur de Jong
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

"""BTW, TVA, NWSt, ondernemingsnummer (Belgian enterprise number).

The enterprise number (ondernemingsnummer) is a unique identifier of
companies within the Belgian administrative services. It was previously
the VAT ID number. The number consists of 10 digits.

>>> compact('BE403019261')
'0403019261'
>>> compact('(0)403019261')
'0403019261'
>>> validate('BE 428759497')
'0428759497'
>>> validate('BE431150351')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    number = clean(number, ' -./').upper().strip()
    if number.startswith('BE'):
        number = number[2:]
    if number.startswith('(0)'):
        number = '0' + number[3:]
    if len(number) == 9:
        number = '0' + number  # old format had 9 digits
    return number


def checksum(number):
    """Calculate the checksum."""
    return (int(number[:-2]) + int(number[-2:])) % 97


def validate(number):
    """Check if the number is a valid VAT number. This checks the length,
    formatting and check digit."""
    number = compact(number)
    if not isdigits(number) or int(number) <= 0:
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
