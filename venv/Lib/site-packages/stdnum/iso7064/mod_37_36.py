# mod_37_36.py - functions for performing the ISO 7064 Mod 37, 36 algorithm
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

"""The ISO 7064 Mod 37, 36 algorithm.

The Mod 37, 36 algorithm uses an alphanumeric check digit and the number
itself may also contain letters.

>>> checksum('A12425GABC1234002M')
1
>>> calc_check_digit('A12425GABC1234002')
'M'
>>> validate('A12425GABC1234002M')
'A12425GABC1234002M'

By changing the alphabet this can be turned into any Mod x+1, x
algorithm. For example Mod 11, 10:

>>> calc_check_digit('00200667308', alphabet='0123456789')
'5'
>>> validate('002006673085', alphabet='0123456789')
'002006673085'
"""

from stdnum.exceptions import *


def checksum(number, alphabet='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'):
    """Calculate the checksum. A valid number should have a checksum of 1."""
    modulus = len(alphabet)
    check = modulus // 2
    for n in number:
        check = (((check or modulus) * 2) % (modulus + 1) + alphabet.index(n)) % modulus
    return check


def calc_check_digit(number, alphabet='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'):
    """Calculate the extra digit that should be appended to the number to
    make it a valid number."""
    modulus = len(alphabet)
    return alphabet[(1 - ((checksum(number, alphabet) or modulus) * 2) % (modulus + 1)) % modulus]


def validate(number, alphabet='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'):
    """Check whether the check digit is valid."""
    try:
        valid = checksum(number, alphabet) == 1
    except Exception:  # noqa: B902
        raise InvalidFormat()
    if not valid:
        raise InvalidChecksum()
    return number


def is_valid(number, alphabet='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'):
    """Check whether the check digit is valid."""
    try:
        return bool(validate(number, alphabet))
    except ValidationError:
        return False
