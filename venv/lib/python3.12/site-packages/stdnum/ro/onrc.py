# onrc.py - functions for handling Romanian ONRC numbers
# coding: utf-8
#
# Copyright (C) 2020 Dimitrios Josef Moustos
# Copyright (C) 2020 Arthur de Jong
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

"""ONRC (Ordine din Registrul Comerţului, Romanian Trade Register identifier).

All businesses in Romania have the to register with the National Trade
Register Office to receive a registration number. The number contains
information about the type of company, county, a sequence number and
registration year. This number can change when registration information
changes.

>>> validate('J52/750/2012')
'J52/750/2012'
>>> validate('X52/750/2012')
Traceback (most recent call last):
    ...
InvalidComponent: ...
"""

import datetime
import re

from stdnum.exceptions import *
from stdnum.util import clean


# These characters should all be replaced by slashes
_cleanup_re = re.compile(r'[ /\\-]+')

# This pattern should match numbers that for some reason have a full date
# as last field
_onrc_fulldate_re = re.compile(r'^([A-Z][0-9]+/[0-9]+/)\d{2}[.]\d{2}[.](\d{4})$')

# This pattern should match all valid numbers
_onrc_re = re.compile(r'^[A-Z][0-9]+/[0-9]+/[0-9]+$')

# List of valid counties
_counties = set(list(range(1, 41)) + [51, 52])


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    number = _cleanup_re.sub('/', clean(number).upper().strip())
    # remove optional slash between first letter and county digits
    if number[1:2] == '/':
        number = number[:1] + number[2:]
    # normalise county number to two digits
    if number[2:3] == '/':
        number = number[:1] + '0' + number[1:]
    # convert trailing full date to year only
    m = _onrc_fulldate_re.match(number)
    if m:
        number = ''.join(m.groups())
    return number


def validate(number):
    """Check if the number is a valid ONRC."""
    number = compact(number)
    if not _onrc_re.match(number):
        raise InvalidFormat()
    if number[:1] not in 'JFC':
        raise InvalidComponent()
    county, serial, year = number[1:].split('/')
    if len(serial) > 5:
        raise InvalidLength()
    if len(county) not in (1, 2) or int(county) not in _counties:
        raise InvalidComponent()
    if len(year) != 4:
        raise InvalidLength()
    if int(year) < 1990 or int(year) > datetime.date.today().year:
        raise InvalidComponent()
    return number


def is_valid(number):
    """Check if the number is a valid ONRC."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False
