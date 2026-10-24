# verhoeff.py - functions for performing the Verhoeff checksum
#
# Copyright (C) 2010-2021 Arthur de Jong
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

"""The Verhoeff algorithm.

The Verhoeff algorithm is a checksum algorithm that should catch most common
(typing) errors in numbers. The algorithm uses two tables for permutations
and multiplications and as a result is more complex than the Luhn algorithm.

More information:

* https://en.wikipedia.org/wiki/Verhoeff_algorithm
* https://en.wikibooks.org/wiki/Algorithm_Implementation/Checksums/Verhoeff_Algorithm

The module provides the checksum() function to calculate the Verhoeff
checksum a calc_check_digit() function to generate a check digit that can be
append to an existing number to result in a number with a valid checksum and
validation functions.

>>> validate('1234')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> checksum('1234')
1
>>> calc_check_digit('1234')
'0'
>>> validate('12340')
'12340'
"""

from stdnum.exceptions import *


# These are the multiplication and permutation tables used in the
# Verhoeff algorithm.

_multiplication_table = (
    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
    (1, 2, 3, 4, 0, 6, 7, 8, 9, 5),
    (2, 3, 4, 0, 1, 7, 8, 9, 5, 6),
    (3, 4, 0, 1, 2, 8, 9, 5, 6, 7),
    (4, 0, 1, 2, 3, 9, 5, 6, 7, 8),
    (5, 9, 8, 7, 6, 0, 4, 3, 2, 1),
    (6, 5, 9, 8, 7, 1, 0, 4, 3, 2),
    (7, 6, 5, 9, 8, 2, 1, 0, 4, 3),
    (8, 7, 6, 5, 9, 3, 2, 1, 0, 4),
    (9, 8, 7, 6, 5, 4, 3, 2, 1, 0))

_permutation_table = (
    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
    (1, 5, 7, 6, 2, 8, 3, 0, 9, 4),
    (5, 8, 0, 3, 7, 9, 6, 1, 4, 2),
    (8, 9, 1, 6, 0, 4, 3, 5, 2, 7),
    (9, 4, 5, 3, 1, 2, 6, 8, 7, 0),
    (4, 2, 8, 6, 5, 7, 3, 9, 0, 1),
    (2, 7, 9, 3, 8, 0, 6, 4, 1, 5),
    (7, 0, 4, 6, 9, 1, 3, 2, 5, 8))


def checksum(number):
    """Calculate the Verhoeff checksum over the provided number. The checksum
    is returned as an int. Valid numbers should have a checksum of 0."""
    # transform number list
    number = tuple(int(n) for n in reversed(str(number)))
    # calculate checksum
    check = 0
    for i, n in enumerate(number):
        check = _multiplication_table[check][_permutation_table[i % 8][n]]
    return check


def validate(number):
    """Check if the number provided passes the Verhoeff checksum."""
    if not bool(number):
        raise InvalidFormat()
    try:
        valid = checksum(number) == 0
    except Exception:  # noqa: B902
        raise InvalidFormat()
    if not valid:
        raise InvalidChecksum()
    return number


def is_valid(number):
    """Check if the number provided passes the Verhoeff checksum."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def calc_check_digit(number):
    """Calculate the extra digit that should be appended to the number to
    make it a valid number."""
    return str(_multiplication_table[checksum(str(number) + '0')].index(0))
