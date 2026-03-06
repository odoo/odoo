# ein.py - functions for handling EINs
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

"""EIN (U.S. Employer Identification Number).

The Employer Identification Number, also known as Federal Employer
Identification Number (FEIN), is used to identify a business entity in the
United States. It is issued to anyone that has to pay withholding taxes on
employees.

>>> validate('91-1144442')
'911144442'
>>> get_campus('04-2103594') == 'Brookhaven'
True
>>> validate('911-14-4442')  # dash in the wrong place
Traceback (most recent call last):
    ...
InvalidFormat: ...
>>> validate('07-1144442')  # wrong prefix
Traceback (most recent call last):
    ...
InvalidComponent: ...
>>> format('042103594')
'04-2103594'
>>> format('123')  # unknown formatting is left alone
'123'
"""

import re

from stdnum.exceptions import *
from stdnum.util import clean


# regular expression for matching EINs
_ein_re = re.compile(r'^(?P<area>[0-9]{2})-?(?P<group>[0-9]{7})$')


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, '-').strip()


def get_campus(number):
    """Determine the Campus or other location that issued the EIN."""
    from stdnum import numdb
    number = compact(number)
    results = numdb.get('us/ein').info(number)[0][1]
    if not results:
        raise InvalidComponent()
    return results['campus']


def validate(number):
    """Check if the number is a valid EIN. This checks the length, groups and
    formatting if it is present."""
    match = _ein_re.search(clean(number, '').strip())
    if not match:
        raise InvalidFormat()
    get_campus(number)  # raises exception for unknown campus
    return compact(number)


def is_valid(number):
    """Check if the number is a valid EIN."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    if len(number) == 9:
        number = number[:2] + '-' + number[2:]
    return number
