# bic.py - functions for handling ISO 9362 Business identifier codes
#
# Copyright (C) 2015 Lifealike Ltd
# Copyright (C) 2017-2018 Arthur de Jong
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

"""BIC (ISO 9362 Business identifier codes).

An ISO 9362 identifier (also: BIC, BEI, or SWIFT code) uniquely
identifies an institution. They are commonly used to route financial
transactions.

The code consists of a 4 letter institution code, a 2 letter country code,
and a 2 character location code, optionally followed by a three character
branch code.

>>> validate('AGRIFRPP882')
'AGRIFRPP882'
>>> validate('ABNA BE 2A')
'ABNABE2A'
>>> validate('AGRIFRPP')
'AGRIFRPP'
>>> validate('AGRIFRPP8')
Traceback (most recent call last):
    ...
InvalidLength: ..
>>> validate('AGRIF2PP')  # country code can't contain digits
Traceback (most recent call last):
    ...
InvalidFormat: ..
>>> format('agriFRPP')  # conventionally caps
'AGRIFRPP'

"""

import re

from stdnum.exceptions import *
from stdnum.util import clean


_bic_re = re.compile(r'^[A-Z]{6}[0-9A-Z]{2}([0-9A-Z]{3})?$')


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any surrounding whitespace."""
    return clean(number, ' -').strip().upper()


def validate(number):
    """Check if the number is a valid routing number. This checks the length
    and characters in each position."""
    number = compact(number)
    if len(number) not in (8, 11):
        raise InvalidLength()
    match = _bic_re.search(number)
    if not match:
        raise InvalidFormat()
    return number


def is_valid(number):
    """Check if the number provided is a valid BIC."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    return compact(number)
