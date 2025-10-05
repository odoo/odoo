# pin.py - functions for handling Kenya PIN numbers
# coding: utf-8
#
# Copyright (C) 2022 Leandro Regueiro
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

"""PIN (Personal Identification Number, Kenya tax number).

The Personal Identification Number (KRA PIN) is an 11 digit unique number that
is issued by Kenya Revenue Authority (KRA) for purposes of transacting business
with KRA, other Government agencies and service providers. It can be issued for
individuals and non-individuals like companies, schools, organisations, etc.

The number consists of 11 characters, where the first one is an A (for
individuals) or a P (for non-individuals), the last one is a letter, and the
rest are digits.

More information:

* https://www.kra.go.ke/individual/individual-pin-registration/learn-about-pin/about-pin
* https://itax.kra.go.ke/KRA-Portal/pinChecker.htm

>>> validate('P051365947M')
'P051365947M'
>>> validate('A004416331M')
'A004416331M'
>>> validate('12345')
Traceback (most recent call last):
    ...
InvalidLength: ...
>>> validate('V1234567890')
Traceback (most recent call last):
    ...
InvalidFormat: ...
>>> format('a004416331m')
'A004416331M'
"""

import re

from stdnum.exceptions import *
from stdnum.util import clean


# The number consists of 11 characters, where the first one is an A (for
# individuals) or a P (for non-individuals), the last one is a letter, and the
# rest are digits.
_pin_re = re.compile(r'^[A|P]{1}[0-9]{9}[A-Z]{1}$')


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, ' -').strip().upper()


def validate(number):
    """Check if the number is a valid Kenya PIN number.

    This checks the length and formatting.
    """
    number = compact(number)
    if len(number) != 11:
        raise InvalidLength()
    match = _pin_re.search(number)
    if not match:
        raise InvalidFormat()
    return number


def is_valid(number):
    """Check if the number is a valid Kenya PIN number."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    return compact(number)
