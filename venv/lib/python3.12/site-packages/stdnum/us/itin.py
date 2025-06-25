# itin.py - functions for handling ITINs
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

"""ITIN (U.S. Individual Taxpayer Identification Number).

The Individual Taxpayer Identification Number is issued by the United
States IRS to individuals who are required to have a taxpayer
identification number but who are not eligible to obtain a Social Security
Number.

It is a nine-digit number that begins with the number 9 and the
fourth and fifth digit are expected to be in a certain range.

>>> validate('912-90-3456')
'912903456'
>>> validate('9129-03456')  # dash in the wrong place
Traceback (most recent call last):
    ...
InvalidFormat: ...
>>> validate('123-45-6789')  # wrong start digit
Traceback (most recent call last):
    ...
InvalidComponent: ...
>>> validate('912-93-4567')  # wrong group
Traceback (most recent call last):
    ...
InvalidComponent: ...
>>> compact('1234-56-789')
'123456789'
>>> format('111223333')
'111-22-3333'
>>> format('123')  # unknown formatting is left alone
'123'
"""

import re

from stdnum.exceptions import *
from stdnum.util import clean


# regular expression for matching ITINs
_itin_re = re.compile(r'^(?P<area>[0-9]{3})-?(?P<group>[0-9]{2})-?[0-9]{4}$')


# allowed group digits
_allowed_groups = set((str(x) for x in range(70, 100) if x not in (89, 93)))


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, '-').strip()


def validate(number):
    """Check if the number is a valid ITIN. This checks the length, groups
    and formatting if it is present."""
    match = _itin_re.search(clean(number, '').strip())
    if not match:
        raise InvalidFormat()
    area = match.group('area')
    group = match.group('group')
    if area[0] != '9' or group not in _allowed_groups:
        raise InvalidComponent()
    return compact(number)


def is_valid(number):
    """Check if the number is a valid ITIN."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    if len(number) == 9:
        number = number[:3] + '-' + number[3:5] + '-' + number[5:]
    return number
