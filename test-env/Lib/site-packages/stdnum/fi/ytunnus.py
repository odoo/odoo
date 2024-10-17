# ytunnus.py - functions for handling Finnish business identifiers (y-tunnus)
# coding: utf-8
#
# Copyright (C) 2015 Holvi Payment Services Oy
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

"""Y-tunnus (Finnish business identifier).

The number is an 8-digit code with a weighted checksum.

>>> validate('2077474-0')
'20774740'
>>> validate('2077474-1')  # invalid check digit
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> format('2077474-0')
'2077474-0'
"""

from stdnum.exceptions import *
from stdnum.fi import alv


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return alv.compact(number)


def validate(number):
    """Check if the number is a valid business identifier. This checks the
    length, formatting and check digit."""
    return alv.validate(number)


def is_valid(number):
    """Check if the number is a valid business identifier."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    number = compact(number)
    return number[:7] + '-' + number[7:]
