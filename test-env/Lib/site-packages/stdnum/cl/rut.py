# rut.py - functions for handling Chile RUT/RUN numbers
# coding: utf-8
#
# Copyright (C) 2008-2011 Cédric Krier
# Copyright (C) 2008-2011 B2CK
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

"""RUT (Rol Único Tributario, Chilean national tax number).

The RUT, the Chilean national tax number is the same as the RUN (Rol Único
Nacional) the Chilean national identification number. The number consists of
8 digits, followed by a check digit.

>>> validate('76086428-5')
'760864285'
>>> validate('CL 12531909-2')
'125319092'
>>> validate('12531909-3')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> validate('76086A28-5')
Traceback (most recent call last):
    ...
InvalidFormat: ...
>>> format('125319092')
'12.531.909-2'
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    number = clean(number, ' -.').upper().strip()
    if number.startswith('CL'):
        number = number[2:]
    return number


def calc_check_digit(number):
    """Calculate the check digit. The number passed should not have the
    check digit included."""
    s = sum(int(n) * (4 + (5 - i) % 6) for i, n in enumerate(number[::-1]))
    return '0123456789K'[s % 11]


def validate(number):
    """Check if the number is a valid RUT. This checks the length, formatting
    and check digit."""
    number = compact(number)
    if len(number) not in (8, 9):
        raise InvalidLength()
    if not isdigits(number[:-1]):
        raise InvalidFormat()
    if number[-1] != calc_check_digit(number[:-1]):
        raise InvalidChecksum()
    return number


def is_valid(number):
    """Check if the number is a valid RUT."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    number = compact(number)
    return (number[:-7] + '.' + number[-7:-4] + '.' +
            number[-4:-1] + '-' + number[-1])
