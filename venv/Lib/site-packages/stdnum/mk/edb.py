# edb.py - functions for handling North Macedonia EDB numbers
# coding: utf-8
#
# Copyright (C) 2022 Leandro Regueiro
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

"""ЕДБ (Едниствен Даночен Број, North Macedonia tax number).

This number consists of 13 digits, sometimes with an additional "MK" prefix.

More information:

* http://www.ujp.gov.mk/en

>>> validate('4030000375897')
'4030000375897'
>>> validate('МК 4020990116747')  # Cyrillic letters
'4020990116747'
>>> validate('MK4057009501106')  # ASCII letters
'4057009501106'
>>> validate('4030000375890')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> format('МК 4020990116747')  # Cyrillic letters
'4020990116747'
>>> format('MK4057009501106')  # ASCII letters
'4057009501106'
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation.

    This strips the number of any valid separators and removes surrounding
    whitespace.
    """
    number = clean(number, ' -').upper().strip()
    # First two are ASCII, second two are Cyrillic and only strip matching
    # types to avoid implicit conversion to unicode strings in Python 2.7
    for prefix in ('MK', u'MK', 'МК', u'МК'):
        if isinstance(number, type(prefix)) and number.startswith(prefix):
            number = number[len(prefix):]
    return number


def calc_check_digit(number):
    """Calculate the check digit."""
    weights = (7, 6, 5, 4, 3, 2, 7, 6, 5, 4, 3, 2)
    total = sum(int(n) * w for n, w in zip(number, weights))
    return str((-total % 11) % 10)


def validate(number):
    """Check if the number is a valid North Macedonia ЕДБ number.

    This checks the length, formatting and check digit.
    """
    number = compact(number)
    if len(number) != 13:
        raise InvalidLength()
    if not isdigits(number):
        raise InvalidFormat()
    if number[-1] != calc_check_digit(number):
        raise InvalidChecksum()
    return number


def is_valid(number):
    """Check if the number is a valid North Macedonia ЕДБ number."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    return compact(number)
