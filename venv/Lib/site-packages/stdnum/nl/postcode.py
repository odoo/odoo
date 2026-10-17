# postcode.py - functions for handling Dutch postal codes
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

"""Postcode (the Dutch postal code).

The Dutch postal code consists of four numbers followed by two letters,
separated by a single space.

More information:
* https://en.wikipedia.org/wiki/Postal_codes_in_the_Netherlands
* https://nl.wikipedia.org/wiki/Postcodes_in_Nederland

>>> validate('2601 DC')
'2601 DC'
>>> validate('NL-2611ET')
'2611 ET'
>>> validate('26112 ET')
Traceback (most recent call last):
    ...
InvalidFormat: ...
>>> validate('2611 SS')  # a few letter combinations are banned
Traceback (most recent call last):
    ...
InvalidComponent: ...
"""

import re

from stdnum.exceptions import *
from stdnum.util import clean


_postcode_re = re.compile(r'^(?P<pt1>[1-9][0-9]{3})(?P<pt2>[A-Z]{2})$')


_postcode_blacklist = ('SA', 'SD', 'SS')


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    number = clean(number, ' -').upper().strip()
    if number.startswith('NL'):
        number = number[2:]
    return number


def validate(number):
    """Check if the number is in the correct format. This currently does not
    check whether the code corresponds to a real address."""
    number = compact(number)
    match = _postcode_re.search(number)
    if not match:
        raise InvalidFormat()
    if match.group('pt2') in _postcode_blacklist:
        raise InvalidComponent()
    return '%s %s' % (match.group('pt1'), match.group('pt2'))


def is_valid(number):
    """Check if the number is a valid postal code."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False
