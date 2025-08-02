# bn.py - functions for handling Canadian Business Numbers (BNs)
#
# Copyright (C) 2017 Arthur de Jong
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

"""BN (Canadian Business Number).

A Business Number (BN) is a 9-digit identification number for businesses
issued by the Canada Revenue Agency for tax purposes. The 9-digit number can
be followed by two letters (program identifier) and 4 digits (reference
number) to form a program account (or BN15).

More information:

* https://www.canada.ca/en/services/taxes/business-number.html
* https://www.ic.gc.ca/app/scr/cc/CorporationsCanada/fdrlCrpSrch.html?locale=en_CA/

>>> validate('12302 6635')
'123026635'
>>> validate('12302 6635 RC 0001')
'123026635RC0001'
>>> validate('123456783')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> validate('12345678Z')
Traceback (most recent call last):
    ...
InvalidFormat: ...
"""

from stdnum import luhn
from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, '- ').strip()


def validate(number):
    """Check if the number is a valid BN or BN15. This checks the length,
    formatting and check digit."""
    number = compact(number)
    if len(number) not in (9, 15):
        raise InvalidLength()
    if not isdigits(number[:9]):
        raise InvalidFormat()
    luhn.validate(number[:9])
    if len(number) == 15:
        if number[9:11] not in ('RC', 'RM', 'RP', 'RT'):
            raise InvalidComponent()
        if not isdigits(number[11:]):
            raise InvalidFormat()
    return number


def is_valid(number):
    """Check if the number is a valid BN or BN15."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False
