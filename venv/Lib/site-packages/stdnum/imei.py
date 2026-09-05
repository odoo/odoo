# imei.py - functions for handling International Mobile Equipment Identity
#           (IMEI) numbers
#
# Copyright (C) 2010-2015 Arthur de Jong
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

"""IMEI (International Mobile Equipment Identity).

The  IMEI is used to identify mobile phones. An IMEI is 14, 15 (when the
check digit is included) or 16 digits (IMEISV) long. The check digit is
validated using the Luhn algorithm.

More information:

* https://en.wikipedia.org/wiki/International_Mobile_Equipment_Identity

>>> validate('35686800-004141-20')
'3568680000414120'
>>> validate('35-417803-685978-1')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> compact('35686800-004141-20')
'3568680000414120'
>>> format('354178036859789')
'35-417803-685978-9'
>>> format('35686800-004141', add_check_digit=True)
'35-686800-004141-8'
>>> imei_type('35686800-004141-20')
'IMEISV'
>>> split('35686800-004141')
('35686800', '004141', '')
"""

from stdnum import luhn
from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the IMEI number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, ' -').strip().upper()


def validate(number):
    """Check if the number provided is a valid IMEI (or IMEISV) number."""
    number = compact(number)
    if not isdigits(number):
        raise InvalidFormat()
    if len(number) == 15:
        # only 15 digit IMEI has check digit
        luhn.validate(number)
    elif len(number) not in (14, 16):
        # neither IMEI without check digit or IMEISV (which doesn't have one)
        raise InvalidLength()
    return number


def imei_type(number):
    """Check the passed number and return 'IMEI', 'IMEISV' or None (for
    invalid) for checking the type of number passed."""
    try:
        number = validate(number)
    except ValidationError:
        return None
    if len(number) in (14, 15):
        return 'IMEI'
    else:  # len(number) == 16:
        return 'IMEISV'


def is_valid(number):
    """Check if the number provided is a valid IMEI (or IMEISV) number."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def split(number):
    """Split the number into a Type Allocation Code (TAC), serial number
    and either the checksum (for IMEI) or the software version number (for
    IMEISV)."""
    number = compact(number)
    return (number[:8], number[8:14], number[14:])


def format(number, separator='-', add_check_digit=False):
    """Reformat the number to the standard presentation format."""
    number = compact(number)
    if len(number) == 14 and add_check_digit:
        number += luhn.calc_check_digit(number)
    number = (number[:2], number[2:8], number[8:14], number[14:])
    return separator.join(x for x in number if x)
