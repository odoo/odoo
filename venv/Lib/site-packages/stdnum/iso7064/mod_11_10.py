# mod_11_10.py - functions for performing the ISO 7064 Mod 11, 10 algorithm
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

"""The ISO 7064 Mod 11, 10 algorithm.

The Mod 11, 10 algorithm uses a number of calculations modulo 11 and 10 to
determine a checksum.

For a module that can do generic Mod x+1, x calculations see the
:mod:`stdnum.iso7064.mod_37_36` module.

>>> calc_check_digit('79462')
'3'
>>> validate('794623')
'794623'
>>> calc_check_digit('00200667308')
'5'
>>> validate('002006673085')
'002006673085'
"""

from stdnum.exceptions import *


def checksum(number):
    """Calculate the checksum. A valid number should have a checksum of 1."""
    check = 5
    for n in number:
        check = (((check or 10) * 2) % 11 + int(n)) % 10
    return check


def calc_check_digit(number):
    """Calculate the extra digit that should be appended to the number to
    make it a valid number."""
    return str((1 - ((checksum(number) or 10) * 2) % 11) % 10)


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
