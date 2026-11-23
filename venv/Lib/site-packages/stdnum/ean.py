# ean.py - functions for handling EANs
#
# Copyright (C) 2011-2017 Arthur de Jong
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

"""EAN (International Article Number).

Module for handling EAN (International Article Number) codes. This
module handles numbers EAN-13, EAN-8, UPC (12-digit) and GTIN (EAN-14) format.

>>> validate('73513537')
'73513537'
>>> validate('978-0-471-11709-4') # EAN-13 format
'9780471117094'
>>> validate('98412345678908') # GTIN format
'98412345678908'
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the EAN to the minimal representation. This strips the number
    of any valid separators and removes surrounding whitespace."""
    return clean(number, ' -').strip()


def calc_check_digit(number):
    """Calculate the EAN check digit for 13-digit numbers. The number passed
    should not have the check bit included."""
    return str((10 - sum((3, 1)[i % 2] * int(n)
                         for i, n in enumerate(reversed(number)))) % 10)


def validate(number):
    """Check if the number provided is a valid EAN-13. This checks the length
    and the check bit but does not check whether a known GS1 Prefix and
    company identifier are referenced."""
    number = compact(number)
    if not isdigits(number):
        raise InvalidFormat()
    if len(number) not in (14, 13, 12, 8):
        raise InvalidLength()
    if calc_check_digit(number[:-1]) != number[-1]:
        raise InvalidChecksum()
    return number


def is_valid(number):
    """Check if the number provided is a valid EAN-13. This checks the length
    and the check bit but does not check whether a known GS1 Prefix and
    company identifier are referenced."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False
