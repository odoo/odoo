# orgnr.py - functions for handling Norwegian organisation numbers
# coding: utf-8
#
# Copyright (C) 2014 Tomas Thor Jonsson
# Copyright (C) 2015 Tuomas Toivonen
# Copyright (C) 2015 Arthur de Jong
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

"""Orgnr (Organisasjonsnummer, Norwegian organisation number).

The Organisasjonsnummer is a 9-digit number with a straightforward check
mechanism.

More information:

* https://nn.wikipedia.org/wiki/Organisasjonsnummer
* https://no.wikipedia.org/wiki/Organisasjonsnummer

>>> validate('988 077 917')
'988077917'
>>> validate('988 077 918')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> format('988077917')
'988 077 917'
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, ' ').strip()


def checksum(number):
    """Calculate the checksum."""
    weights = (3, 2, 7, 6, 5, 4, 3, 2, 1)
    return sum(w * int(n) for w, n in zip(weights, number)) % 11


def validate(number):
    """Check if the number is a valid organisation number. This checks the
    length, formatting and check digit."""
    number = compact(number)
    if not isdigits(number):
        raise InvalidFormat()
    if len(number) != 9:
        raise InvalidLength()
    if checksum(number) != 0:
        raise InvalidChecksum()
    return number


def is_valid(number):
    """Check if the number is a valid organisation number."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    number = compact(number)
    return number[:3] + ' ' + number[3:6] + ' ' + number[6:]
