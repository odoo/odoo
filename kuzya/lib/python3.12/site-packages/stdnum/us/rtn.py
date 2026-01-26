# rtn.py - functions for handling banking routing transit numbers
#
# Copyright (C) 2014 Lifealike Ltd
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

"""RTN (Routing transport number).

The routing transport number is a nine digit number used in the US banking
system for processing deposits between banks.

The last digit is a checksum.

>>> calc_check_digit('11100002')
'5'
>>> validate('111000025')
'111000025'
>>> validate('11100002')  # Not nine digits
Traceback (most recent call last):
    ...
InvalidLength: ..
>>> validate('11100002B')  # Not all numeric
Traceback (most recent call last):
    ...
InvalidFormat: ..
>>> validate('112000025')  # bad checksum
Traceback (most recent call last):
    ...
InvalidChecksum: ..
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any surrounding whitespace."""
    number = clean(number).strip()
    return number


def calc_check_digit(number):
    """Calculate the check digit. The number passed should not have the
    check digit included."""
    digits = [int(c) for c in number]
    checksum = (
        7 * (digits[0] + digits[3] + digits[6]) +
        3 * (digits[1] + digits[4] + digits[7]) +
        9 * (digits[2] + digits[5])
    ) % 10
    return str(checksum)


def validate(number):
    """Check if the number is a valid routing number. This checks the length
    and check digit."""
    number = compact(number)
    if not isdigits(number):
        raise InvalidFormat()
    if len(number) != 9:
        raise InvalidLength()
    if calc_check_digit(number[:-1]) != number[-1]:
        raise InvalidChecksum()
    return number


def is_valid(number):
    """Check if the number is a valid RTN."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False
