# ptin.py - functions for handling  PTINs
#
# Copyright (C) 2013 Arthur de Jong
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

"""PTIN (U.S. Preparer Tax Identification Number).

A Preparer Tax Identification Number (PTIN) is United States
identification number for tax return preparers. It is an eight-digit
number prefixed with a capital P.

>>> validate('P-00634642')
'P00634642'
>>> validate('P01594846')
'P01594846'
>>> validate('00634642')  # missing P
Traceback (most recent call last):
    ...
InvalidFormat: ...
"""

import re

from stdnum.exceptions import *
from stdnum.util import clean


# regular expression for matching PTINs
_ptin_re = re.compile(r'^P[0-9]{8}$')


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, '-').strip()


def validate(number):
    """Check if the number is a valid PTIN. This checks the length, groups
    and formatting if it is present."""
    number = compact(number).upper()
    if not _ptin_re.search(number):
        raise InvalidFormat()
    # sadly, no more information on PTIN number validation was found
    return number


def is_valid(number):
    """Check if the number is a valid ATIN."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False
