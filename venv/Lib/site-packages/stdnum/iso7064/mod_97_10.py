# mod_97_10.py - functions for performing the ISO 7064 Mod 97, 10 algorithm
#
# Copyright (C) 2010-2022 Arthur de Jong
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

"""The ISO 7064 Mod 97, 10 algorithm.

The Mod 97, 10 algorithm evaluates the whole number as an integer which is
valid if the number modulo 97 is 1. As such it has two check digits.

>>> calc_check_digits('99991234567890121414')
'90'
>>> validate('9999123456789012141490')
'9999123456789012141490'
>>> calc_check_digits('4354111611551114')
'31'
>>> validate('08686001256515001121751')
'08686001256515001121751'
>>> calc_check_digits('22181321402534321446701611')
'35'
"""

from stdnum.exceptions import *


def _to_base10(number):
    """Prepare the number to its base10 representation."""
    return ''.join(
        str(int(x, 36)) for x in number)


def checksum(number):
    """Calculate the checksum. A valid number should have a checksum of 1."""
    return int(_to_base10(number)) % 97


def calc_check_digits(number):
    """Calculate the extra digits that should be appended to the number to
    make it a valid number."""
    return '%02d' % (98 - checksum(number + '00'))


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
