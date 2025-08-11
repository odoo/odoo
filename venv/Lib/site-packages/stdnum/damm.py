# damm.py - functions for performing the Damm checksum algorithm
#
# Copyright (C) 2016-2021 Arthur de Jong
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

"""The Damm algorithm.

The Damm algorithm is a check digit algorithm that should detect all
single-digit errors and all adjacent transposition errors. Based on
anti-symmetric quasigroup of order 10 it uses a substitution table.

This implementation uses the table from Wikipedia by default but a custom
table can be provided.

More information:

* https://en.wikipedia.org/wiki/Damm_algorithm

>>> validate('572')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> calc_check_digit('572')
'4'
>>> validate('5724')
'5724'
>>> table = (
...     (0, 2, 3, 4, 5, 6, 7, 8, 9, 1),
...     (2, 0, 4, 1, 7, 9, 5, 3, 8, 6),
...     (3, 7, 0, 5, 2, 8, 1, 6, 4, 9),
...     (4, 1, 8, 0, 6, 3, 9, 2, 7, 5),
...     (5, 6, 2, 9, 0, 7, 4, 1, 3, 8),
...     (6, 9, 7, 3, 1, 0, 8, 5, 2, 4),
...     (7, 5, 1, 8, 4, 2, 0, 9, 6, 3),
...     (8, 4, 6, 2, 9, 5, 3, 0, 1, 7),
...     (9, 8, 5, 7, 3, 1, 6, 4, 0, 2),
...     (1, 3, 9, 6, 8, 4, 2, 7, 5, 0))
>>> checksum('816', table=table)
9
"""

from stdnum.exceptions import *


_operation_table = (
    (0, 3, 1, 7, 5, 9, 8, 6, 4, 2),
    (7, 0, 9, 2, 1, 5, 4, 8, 6, 3),
    (4, 2, 0, 6, 8, 7, 1, 3, 5, 9),
    (1, 7, 5, 0, 9, 8, 3, 4, 2, 6),
    (6, 1, 2, 3, 0, 4, 5, 9, 7, 8),
    (3, 6, 7, 4, 2, 0, 9, 5, 8, 1),
    (5, 8, 6, 9, 7, 2, 0, 1, 3, 4),
    (8, 9, 4, 5, 3, 6, 2, 0, 1, 7),
    (9, 4, 3, 8, 6, 1, 7, 2, 0, 5),
    (2, 5, 8, 1, 4, 3, 6, 7, 9, 0))


def checksum(number, table=None):
    """Calculate the Damm checksum over the provided number. The checksum is
    returned as an integer value and should be 0 when valid."""
    table = table or _operation_table
    i = 0
    for n in str(number):
        i = table[i][int(n)]
    return i


def validate(number, table=None):
    """Check if the number provided passes the Damm algorithm."""
    if not bool(number):
        raise InvalidFormat()
    try:
        valid = checksum(number, table=table) == 0
    except Exception:  # noqa: B902
        raise InvalidFormat()
    if not valid:
        raise InvalidChecksum()
    return number


def is_valid(number, table=None):
    """Check if the number provided passes the Damm algorithm."""
    try:
        return bool(validate(number, table=table))
    except ValidationError:
        return False


def calc_check_digit(number, table=None):
    """Calculate the extra digit that should be appended to the number to
    make it a valid number."""
    return str(checksum(number, table=table))
