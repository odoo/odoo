# imo.py - functions for handling IMO numbers
# coding: utf-8
#
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

"""IMO number (International Maritime Organization number).

A number used to uniquely identify ships (the hull) for purposes of
registering owners and management companies. The ship identification number
consists of a six-digit sequentially assigned number and a check digit. The
number is usually prefixed with "IMO".

Note that there seem to be a large number of ships with an IMO that does not
have a valid check digit or even have a different length.

>>> validate('IMO 9319466')
'9319466'
>>> validate('IMO 8814275')
'8814275'
>>> validate('8814274')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> format('8814275')
'IMO 8814275'
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    number = clean(number, ' ').upper().strip()
    if number.startswith('IMO'):
        number = number[3:]
    return number


def calc_check_digit(number):
    """Calculate the check digits for the number."""
    return str(sum(int(n) * (7 - i) for i, n in enumerate(number[:6])) % 10)


def validate(number):
    """Check if the number provided is valid. This checks the length and
    check digit."""
    number = compact(number)
    if not isdigits(number):
        raise InvalidFormat()
    if len(number) != 7:
        raise InvalidLength()
    if calc_check_digit(number[:-1]) != number[-1]:
        raise InvalidChecksum()
    return number


def is_valid(number):
    """Check if the number provided is valid. This checks the length and
    check digit."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    return 'IMO ' + compact(number)
