# mst.py - functions for handling Vietnam MST numbers
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

"""MST (Mã số thuế, Vietnam tax number).

This number consists of 10 digits. Branches have a 13 digit number,
where the first ten digits are the same as the parent company's.

The first two digits is the province code where the business was
established. If an enterprise relocates its head office from one
province to another, the MST will remain unchanged.

The following seven digits are a sequential number from 0000001 to
9999999.

The tenth digit is the check digit for the first nine digits, which is
used to verify the number was correctly typed.

The last optional three digits are a sequence from 001 to 999
indicating branches of the enterprise. These digits are usually
separated from the first ten digits using a dash (-)

More information:

* https://vi.wikipedia.org/wiki/Thuế_Việt_Nam#Mã_số_thuế_(MST)_của_doanh_nghiệp
* https://easyinvoice.vn/ma-so-thue/
* https://ub.com.vn/threads/huong-dan-tra-cuu-ma-so-thue-doanh-nghiep-moi-nhat.261393/

>>> validate('0100233488')
'0100233488'
>>> validate('0314409058-002')
'0314409058002'
>>> validate('12345')
Traceback (most recent call last):
    ...
InvalidLength: ...
>>> validate('0100233480')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> format('01.00.112.437')
'0100112437'
>>> format('0312 68 78 78 - 001')
'0312687878-001'
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation.

    This strips the number of any valid separators and removes surrounding
    whitespace.
    """
    return clean(number, ' -.').strip()


def calc_check_digit(number):
    """Calculate the check digit."""
    weights = (31, 29, 23, 19, 17, 13, 7, 5, 3)
    total = sum(w * int(n) for w, n in zip(weights, number))
    return str(10 - (total % 11))


def validate(number):
    """Check if the number is a valid Vietnam MST number.

    This checks the length, formatting and check digit.
    """
    number = compact(number)
    if len(number) not in (10, 13):
        raise InvalidLength()
    if not isdigits(number):
        raise InvalidFormat()
    if number[2:9] == '0000000':
        raise InvalidComponent()
    if len(number) == 13 and number[-3:] == '000':
        raise InvalidComponent()
    if number[9] != calc_check_digit(number):
        raise InvalidChecksum()
    return number


def is_valid(number):
    """Check if the number is a valid Vietnam MST number."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    number = compact(number)
    return number if len(number) == 10 else '-'.join([number[:10], number[10:]])
