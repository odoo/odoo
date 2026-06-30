# atin.py - functions for handling  ATINs
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

"""ATIN (U.S. Adoption Taxpayer Identification Number).

An Adoption Taxpayer Identification Number (ATIN) is a temporary
nine-digit number issued by the United States IRS for a child for whom the
adopting parents cannot obtain a Social Security Number.

>>> validate('123-45-6789')
'123456789'
>>> validate('1234-56789')  # dash in the wrong place
Traceback (most recent call last):
    ...
InvalidFormat: ...
>>> format('123456789')
'123-45-6789'
>>> format('123')  # unknown formatting is left alone
'123'
"""

import re

from stdnum.exceptions import *
from stdnum.util import clean


# regular expression for matching ATINs
_atin_re = re.compile(r'^[0-9]{3}-?[0-9]{2}-?[0-9]{4}$')


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, '-').strip()


def validate(number):
    """Check if the number is a valid ATIN. This checks the length and
    formatting if it is present."""
    match = _atin_re.search(clean(number, '').strip())
    if not match:
        raise InvalidFormat()
    # sadly, no more information on ATIN number validation was found
    return compact(number)


def is_valid(number):
    """Check if the number is a valid ATIN."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    if len(number) == 9:
        number = number[:3] + '-' + number[3:5] + '-' + number[5:]
    return number
