# idnr.py - functions for handling Israeli personal numbers
# coding: utf-8
#
# Copyright (C) 2019 Arthur de Jong
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

"""Identity Number (Mispar Zehut, מספר זהות, Israeli identity number).

The identity number (Mispar Zehut, מספר זהות) is issued at birth to Israeli
citizens. The number consists of nine digits and includes a check digit.

More information:

* https://en.wikipedia.org/wiki/National_identification_number#Israel
* https://en.wikipedia.org/wiki/Israeli_identity_card
* https://he.wikipedia.org/wiki/מספר_זהות_(ישראל)

>>> validate('3933742-3')
'039337423'
>>> format('39337423')
'03933742-3'
>>> validate('3933742-2')  # invalid check digit
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> validate('490154203237518')  # longer than 9 digits
Traceback (most recent call last):
    ...
InvalidLength: ...
"""

from stdnum import luhn
from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    number = clean(number, ' -').strip()
    # pad with leading zeroes
    return (9 - len(number)) * '0' + number


def validate(number):
    """Check if the number provided is a valid ID. This checks the length,
    formatting and check digit."""
    number = compact(number)
    if len(number) > 9:
        raise InvalidLength()
    if not isdigits(number) or int(number) <= 0:
        raise InvalidFormat()
    luhn.validate(number)
    return number


def is_valid(number):
    """Check if the number provided is a valid ID. This checks the length,
    formatting and check digit."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    number = compact(number)
    return number[:-1] + '-' + number[-1:]
