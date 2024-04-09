# pin.py - functions for handling Thailand PINs
#
# Copyright (C) 2021 Piruin Panichphol
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

"""PIN (Thailand Personal Identification Number).

The Thailand Personal Identification Number is a unique personal identifier
assigned at birth or upon receiving Thai citizenship issue by the Ministry of
Interior.

This number consists of 13 digits which the last is a check digit. Usually
separated into five groups using hyphens to make it easier to read.

More information:

* https://en.wikipedia.org/wiki/Thai_identity_card

>>> compact('1-2345-45678-78-1')
'1234545678781'
>>> validate('3100600445635')
'3100600445635'
>>> validate('1-2345-45678-78-1')
'1234545678781'
>>> validate('1-2345-45678-78-9')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> format('7100600445635')
'7-1006-00445-63-5'
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, ' -').strip()


def calc_check_digit(number):
    """Calculate the check digit."""
    s = sum((2 - i) * int(n) for i, n in enumerate(number[:12])) % 11
    return str((1 - s) % 10)


def validate(number):
    """Check if the number is a valid PIN. This checks the length,
    formatting and check digit."""
    number = compact(number)
    if len(number) != 13:
        raise InvalidLength()
    if not isdigits(number):
        raise InvalidFormat()
    if number[0] in ('0', '9'):
        raise InvalidComponent()
    if number[-1] != calc_check_digit(number):
        raise InvalidChecksum()
    return number


def is_valid(number):
    """Check whether the number is valid."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    number = compact(number)
    return '-'.join((
        number[:1], number[1:5], number[5:10], number[10:12], number[12:]))
