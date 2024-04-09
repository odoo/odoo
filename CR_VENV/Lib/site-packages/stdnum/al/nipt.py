# nipt.py - functions for handling Albanian VAT numbers
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

"""NIPT (Numri i Identifikimit për Personin e Tatueshëm, Albanian VAT number).

The Albanian NIPT is a 10-digit number with the first and last character
being letters.

>>> validate('AL J 91402501 L')
'J91402501L'
>>> validate('K22218003V')
'K22218003V'
>>> validate('(AL) J 91402501')
Traceback (most recent call last):
    ...
InvalidLength: ...
>>> validate('Z 22218003 V')
Traceback (most recent call last):
    ...
InvalidFormat: ...
"""

import re

from stdnum.exceptions import *
from stdnum.util import clean


# regular expression for matching number
_nipt_re = re.compile(r'^[JKL][0-9]{8}[A-Z]$')


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    number = clean(number, ' ').upper().strip()
    if number.startswith('AL'):
        number = number[2:]
    if number.startswith('(AL)'):
        number = number[4:]
    return number


def validate(number):
    """Check if the number is a valid VAT number. This checks the length and
    formatting."""
    number = compact(number)
    if len(number) != 10:
        raise InvalidLength()
    if not _nipt_re.match(number):
        raise InvalidFormat()
    return number


def is_valid(number):
    """Check if the number is a valid VAT number."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False
