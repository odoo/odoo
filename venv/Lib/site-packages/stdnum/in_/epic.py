# epic.py - functions for handling Indian voter identification numbers
#
# Copyright (C) 2021 Gaurav Chauhan
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

"""EPIC (Electoral Photo Identity Card, Indian Voter ID).

The Electoral Photo Identity Card (EPIC) is an identity document issued by
the Election Commission of India (ECI) only to the India citizens who have
reached the age of 18.

Each EPIC contains an unique 10 digit alphanumeric identifier known as EPIC
number or Voter ID number.

Every EPIC number begins with a Functional Unique Serial Number (FUSN), a 3
letter unique identifier for each Assembly Constituency. FUSN is followed by
a 6 digit serial number and 1 check digit of the serial number calculated
using Luhn algorithm.

More information:

* https://en.wikipedia.org/wiki/Voter_ID_(India)
* https://www.kotaksecurities.com/ksweb/voter-id/serial-number-in-elctoral-roll

>>> validate('WKH1186253')
'WKH1186253'
>>> validate('WKH118624')
Traceback (most recent call last):
    ...
InvalidLength: ...
>>> validate('1231186253')
Traceback (most recent call last):
    ...
InvalidFormat: ...
>>> validate('WKH1186263')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
"""

import re

from stdnum import luhn
from stdnum.exceptions import *
from stdnum.util import clean


_EPIC_RE = re.compile(r'^[A-Z]{3}[0-9]{7}$')


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, ' -').upper().strip()


def validate(number):
    """Check if the number provided is a valid EPIC number. This checks the
    length, formatting and checksum."""
    number = compact(number)
    if len(number) != 10:
        raise InvalidLength
    if not _EPIC_RE.match(number):
        raise InvalidFormat()
    luhn.validate(number[3:])
    return number


def is_valid(number):
    """Check if the number provided is a valid EPIC number. This checks the
    length, formatting and checksum."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False
