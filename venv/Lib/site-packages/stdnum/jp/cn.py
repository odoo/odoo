# cn.py - functions for handling Japanese Corporate Number (CN)
# coding: utf-8
#
# Copyright (C) 2019 Alan Hettinger
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

"""CN (法人番号, hōjin bangō, Japanese Corporate Number).

The Corporate Number is assigned by the Japanese National Tax Agency to
identify government organs, public entities, registered corporations and
other organisations. The number consists of 13 digits where the first digit
is a non-zero check digit.

More information:

 * https://en.wikipedia.org/wiki/Corporate_Number
 * https://www.nta.go.jp/taxes/tetsuzuki/mynumberinfo/houjinbangou/

>>> validate('5-8356-7825-6246')
'5835678256246'
>>> validate('2-8356-7825-6246')
Traceback (most recent call last):
  ...
InvalidChecksum: ...
>>> format('5835678256246')
'5-8356-7825-6246'
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, '- ').strip()


def calc_check_digit(number):
    """Calculate the check digit. The number passed should not have
    the check digit included."""
    weights = (1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2)
    s = sum(w * int(n) for w, n in zip(weights, reversed(number))) % 9
    return str(9 - s)


def validate(number):
    """Check if the number is valid. This checks the length and check
    digit."""
    number = compact(number)
    if len(number) != 13:
        raise InvalidLength()
    if not isdigits(number):
        raise InvalidFormat()
    if calc_check_digit(number[1:]) != number[0]:
        raise InvalidChecksum()
    return number


def is_valid(number):
    """Check if the number is a valid CN."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    number = compact(number)
    return '-'.join(
        (number[0], number[1:5], number[5:9], number[9:13]))
