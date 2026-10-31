# postnummer.py - functions for handling Swedish postal codes
#
# Copyright (C) 2021 Michele Ciccozzi
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

"""Postcode (the Swedish postal code).

The Swedish postal code consists of three numbers followed by two numbers,
separated by a single space.

More information:

* https://en.wikipedia.org/wiki/Postal_codes_in_Sweden
* https://sv.wikipedia.org/wiki/Postnummer_i_Sverige

>>> validate('114 18')
'11418'
>>> validate('SE-11418')
'11418'
>>> validate('1145 18')
Traceback (most recent call last):
    ...
InvalidLength: ...
>>> format('11418')
'114 18'
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    number = clean(number, ' -').upper().strip()
    if number.startswith('SE'):
        number = number[2:]
    return number


def validate(number):
    """Check if the number is in the correct format. This currently does not
    check whether the code corresponds to a real address."""
    number = compact(number)
    if not isdigits(number) or number.startswith('0'):
        raise InvalidFormat()
    if len(number) != 5:
        raise InvalidLength()
    return number


def is_valid(number):
    """Check if the number is a valid postal code."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    number = compact(number)
    return '%s %s' % (number[:3], number[3:])
