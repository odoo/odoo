# ubn.py - functions for handling Taiwanese UBN numbers
# coding: utf-8
#
# Copyright (C) 2020 Leandro Regueiro
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

"""UBN (Unified Business Number, 統一編號, Taiwanese tax number).

The Unified Business Number (UBN, 統一編號) is the number assigned to businesses
within Taiwan for tax (VAT) purposes. The number consists of 8 digits, the
last being a check digit.

More information:

* https://zh.wikipedia.org/wiki/統一編號
* https://findbiz.nat.gov.tw/fts/query/QueryBar/queryInit.do?request_locale=en

>>> validate('00501503')
'00501503'
>>> validate('00501502')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> validate('12345')
Traceback (most recent call last):
    ...
InvalidLength: ...
>>> format(' 0050150 3 ')
'00501503'
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation.

    This strips the number of any valid separators and removes surrounding
    whitespace.
    """
    return clean(number, ' -').strip()


def calc_checksum(number):
    """Calculate the checksum over the number."""
    # convert to numeric first, then sum individual digits
    weights = (1, 2, 1, 2, 1, 2, 4, 1)
    number = ''.join(str(w * int(n)) for w, n in zip(weights, number))
    return sum(int(n) for n in number) % 10


def validate(number):
    """Check if the number is a valid Taiwan UBN number.

    This checks the length, formatting and check digit.
    """
    number = compact(number)
    if len(number) != 8:
        raise InvalidLength()
    if not isdigits(number):
        raise InvalidFormat()
    checksum = calc_checksum(number)
    if not (checksum == 0 or (checksum == 9 and number[6] == '7')):
        raise InvalidChecksum()
    return number


def is_valid(number):
    """Check if the number is a valid Taiwan UBN number."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    return compact(number)
