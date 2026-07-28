# vsk.py - functions for handling Icelandic VAT numbers
# coding: utf-8
#
# Copyright (C) 2015 Tuomas Toivonen
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

"""VSK number (Virðisaukaskattsnúmer, Icelandic VAT number).

The Icelandic VAT number is five or six digits.

>>> validate('IS 00621')
'00621'
>>> validate('IS 0062199')
Traceback (most recent call last):
    ...
InvalidLength: ...
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    number = clean(number, ' ').upper().strip()
    if number.startswith('IS'):
        number = number[2:]
    return number


def validate(number):
    """Check if the number provided is a valid VAT number. This checks the
    length and formatting."""
    number = compact(number)
    if not isdigits(number):
        raise InvalidFormat()
    if len(number) not in (5, 6):
        raise InvalidLength()
    return number


def is_valid(number):
    """Check if the number provided is a valid VAT number. This checks the
    length and formatting."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False
