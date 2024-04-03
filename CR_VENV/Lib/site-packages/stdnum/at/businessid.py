# businessid.py - functions for handling Austrian company register numbers
#
# Copyright (C) 2015 Holvi Payment Services Oy
# Copyright (C) 2012-2019 Arthur de Jong
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

"""Austrian Company Register Numbers.

The Austrian company register number consist of digits followed by a single
letter, e.g. "122119m". Sometimes it is presented with preceding "FN", e.g.
"FN 122119m".

>>> validate('FN 122119m')
'122119m'
>>> validate('122119m')
'122119m'
>>> validate('m123123')
Traceback (most recent call last):
    ...
InvalidFormat: ...
>>> validate('abc')
Traceback (most recent call last):
    ...
InvalidFormat: ...
"""

import re

from stdnum.exceptions import *
from stdnum.util import clean


_businessid_re = re.compile('^[0-9]+[a-z]$')


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace.
    Preceding "FN" is also removed."""
    number = clean(number, ' -./').strip()
    if number.upper().startswith('FN'):
        number = number[2:]
    return number


def validate(number):
    """Check if the number is a valid company register number. This only
    checks the formatting."""
    number = compact(number)
    if not _businessid_re.match(number):
        raise InvalidFormat()
    return number


def is_valid(number):
    """Check if the number is a valid company register number."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False
