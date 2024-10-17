# uid.py - functions for handling Swiss business identifiers
# coding: utf-8
#
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

"""UID (Unternehmens-Identifikationsnummer, Swiss business identifier).

The Swiss UID is used to uniquely identify businesses for taxation purposes.
The number consists of a fixed "CHE" prefix, followed by 9 digits that are
protected with a simple checksum.

This module only supports the "new" format that was introduced in 2011 which
completely replaced the "old" 6-digit format in 2014.

More information:

* https://www.uid.admin.ch/
* https://de.wikipedia.org/wiki/Unternehmens-Identifikationsnummer

>>> validate('CHE-100.155.212')
'CHE100155212'
>>> validate('CHE-100.155.213')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> format('CHE100155212')
'CHE-100.155.212'
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips
    surrounding whitespace and separators."""
    return clean(number, ' -.').strip().upper()


def calc_check_digit(number):
    """Calculate the check digit for organisations. The number passed should
    not have the check digit included."""
    weights = (5, 4, 3, 2, 7, 6, 5, 4)
    s = sum(w * int(n) for w, n in zip(weights, number))
    return str((11 - s) % 11)


def validate(number):
    """Check if the number is a valid UID. This checks the length, formatting
    and check digit."""
    number = compact(number)
    if len(number) != 12:
        raise InvalidLength()
    if not number.startswith('CHE'):
        raise InvalidComponent()
    if not isdigits(number[3:]):
        raise InvalidFormat()
    if number[-1] != calc_check_digit(number[3:-1]):
        raise InvalidChecksum()
    return number


def is_valid(number):
    """Check if the number is a valid UID."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    number = compact(number)
    return number[:3] + '-' + '.'.join(
        number[i:i + 3] for i in range(3, len(number), 3))
