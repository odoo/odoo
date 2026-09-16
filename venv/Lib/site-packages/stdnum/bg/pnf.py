# pnf.py - functions for handling Bulgarian personal number of a foreigner
# coding: utf-8
#
# Copyright (C) 2012-2015 Arthur de Jong
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

"""PNF (ЛНЧ, Личен номер на чужденец, Bulgarian number of a foreigner).

The personal number of a foreigner is a 10-digit number where the last digit
is the result of a weighted checksum.

>>> validate('7111 042 925')
'7111042925'
>>> validate('7111042922')  # invalid check digit
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> validate('71110A2922')  # invalid digit
Traceback (most recent call last):
    ...
InvalidFormat: ...
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, ' -.').upper().strip()


def calc_check_digit(number):
    """Calculate the check digit. The number passed should not have the
    check digit included."""
    weights = (21, 19, 17, 13, 11, 9, 7, 3, 1)
    return str(sum(w * int(n) for w, n in zip(weights, number)) % 10)


def validate(number):
    """Check if the number is a valid national identification number. This
    checks the length, formatting, embedded date and check digit."""
    number = compact(number)
    if not isdigits(number):
        raise InvalidFormat()
    if len(number) != 10:
        raise InvalidLength()
    if calc_check_digit(number[:-1]) != number[-1]:
        raise InvalidChecksum()
    return number


def is_valid(number):
    """Check if the number is a valid national identification number."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False
