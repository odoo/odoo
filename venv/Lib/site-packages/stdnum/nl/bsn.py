# bsn.py - functions for handling BSNs
#
# Copyright (C) 2010-2015 Arthur de Jong
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

"""BSN (Burgerservicenummer, the Dutch citizen identification number).

The BSN is a unique personal identifier and has been introduced as the
successor to the sofinummer. It is issued to each Dutch national. The number
consists of up to nine digits (the leading zeros are commonly omitted) and
contains a simple checksum.

More information:

* https://en.wikipedia.org/wiki/National_identification_number#Netherlands
* https://nl.wikipedia.org/wiki/Burgerservicenummer
* http://www.burgerservicenummer.nl/

>>> validate('1112.22.333')
'111222333'
>>> validate('1112.52.333')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> validate('1112223334')
Traceback (most recent call last):
    ...
InvalidLength: ...
>>> format('111222333')
'1112.22.333'
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    number = clean(number, ' -.').strip()
    # pad with leading zeroes
    return (9 - len(number)) * '0' + number


def checksum(number):
    """Calculate the checksum over the number. A valid number should have
    a checksum of 0."""
    return (sum((9 - i) * int(n) for i, n in enumerate(number[:-1])) -
            int(number[-1])) % 11


def validate(number):
    """Check if the number is a valid BSN. This checks the length and whether
    the check digit is correct."""
    number = compact(number)
    if not isdigits(number) or int(number) <= 0:
        raise InvalidFormat()
    if len(number) != 9:
        raise InvalidLength()
    if checksum(number) != 0:
        raise InvalidChecksum()
    return number


def is_valid(number):
    """Check if the number is a valid BSN."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Reformat the passed number to the standard presentation format."""
    number = compact(number)
    return number[:4] + '.' + number[4:6] + '.' + number[6:]
