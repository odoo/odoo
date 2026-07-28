# utr.py - functions for handling English UTRs
#
# Copyright (C) 2020 Holvi Payment Services
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

"""UTR (United Kingdom Unique Taxpayer Reference).

A UTR (unique taxpayer reference) is a 10 digit number used to identify UK
taxpayers who have to submit a tax return.

More information:

* https://www.oecd.org/tax/automatic-exchange/crs-implementation-and-assistance/tax-identification-numbers/UK-TIN.pdf

>>> validate('1955839661')
'1955839661'
>>> validate('2955839661')
Traceback (most recent call last):
    ...
InvalidChecksum: ..
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, ' ').upper().strip().lstrip('K')


def calc_check_digit(number):
    """Calculate the check digit for the number. The passed number should not
    have the check digit (the first one) included."""
    weights = (6, 7, 8, 9, 10, 5, 4, 3, 2)
    return '21987654321'[sum(int(n) * w for n, w in zip(number, weights)) % 11]


def validate(number):
    """Check if the number is a valid UTR."""
    number = compact(number)
    if not isdigits(number):
        raise InvalidFormat()
    if not len(number) == 10:
        raise InvalidLength()
    if number[0] != calc_check_digit(number[1:]):
        raise InvalidChecksum()
    return number


def is_valid(number):
    """Check if the number is a valid UTR."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False
