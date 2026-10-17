# casrn.py - functions for handling CAS Registry Numbers
#
# Copyright (C) 2017-2022 Arthur de Jong
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

"""CAS RN (Chemical Abstracts Service Registry Number).

The CAS Registry Number is a unique identifier assigned by the Chemical
Abstracts Service (CAS) to a chemical substance.

More information:

* https://en.wikipedia.org/wiki/CAS_Registry_Number

>>> validate('87-86-5')
'87-86-5'
>>> validate('87-86-6')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> validate('012770-26-2')
Traceback (most recent call last):
    ...
InvalidFormat: ...
"""

import re

from stdnum.exceptions import *
from stdnum.util import clean


_cas_re = re.compile(r'^[1-9][0-9]{1,6}-[0-9]{2}-[0-9]$')


def compact(number):
    """Convert the number to the minimal representation."""
    number = clean(number, ' ').strip()
    if '-' not in number:
        number = '-'.join((number[:-3], number[-3:-1], number[-1:]))
    return number


def calc_check_digit(number):
    """Calculate the check digit for the number. The passed number should not
    have the check digit included."""
    number = number.replace('-', '')
    return str(
        sum((i + 1) * int(n) for i, n in enumerate(reversed(number))) % 10)


def validate(number):
    """Check if the number provided is a valid CAS RN."""
    number = compact(number)
    if not 7 <= len(number) <= 12:
        raise InvalidLength()
    if not _cas_re.match(number):
        raise InvalidFormat()
    if number[-1] != calc_check_digit(number[:-1]):
        raise InvalidChecksum()
    return number


def is_valid(number):
    """Check if the number provided is a valid CAS RN."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False
