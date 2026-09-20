# mod_11_2.py - functions for performing the ISO 7064 Mod 11, 2 algorithm
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

"""The ISO 7064 Mod 11, 2 algorithm.

The Mod 11, 2 algorithm is a simple module 11 checksum where the check
digit can be an X to make the number valid.

For a module that can do generic Mod x, 2 calculations see the
:mod:`stdnum.iso7064.mod_37_2` module.

>>> calc_check_digit('0794')
'0'
>>> validate('07940')
'07940'
>>> calc_check_digit('079')
'X'
>>> validate('079X')
'079X'
>>> checksum('079X')
1
"""

from stdnum.exceptions import *


def checksum(number):
    """Calculate the checksum. A valid number should have a checksum of 1."""
    check = 0
    for n in number:
        check = (2 * check + int(10 if n == 'X' else n)) % 11
    return check


def calc_check_digit(number):
    """Calculate the extra digit that should be appended to the number to
    make it a valid number."""
    c = (1 - 2 * checksum(number)) % 11
    return 'X' if c == 10 else str(c)


def validate(number):
    """Check whether the check digit is valid."""
    try:
        valid = checksum(number) == 1
    except Exception:  # noqa: B902
        raise InvalidFormat()
    if not valid:
        raise InvalidChecksum()
    return number


def is_valid(number):
    """Check whether the check digit is valid."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False
