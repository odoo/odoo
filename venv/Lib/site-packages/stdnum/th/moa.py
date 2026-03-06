# moa.py - functions for handling Memorandum of Association Number
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

"""MOA (Thailand Memorandum of Association Number).

Memorandum of Association Number (aka Company's Taxpayer Identification
Number) are numbers issued by the Department of Business Development.

The number consists of 13 digits of which the last is a check digit following
the same algorithm as in the Personal Identity Number (PIN). It uses a
different grouping format and always starts with zero to indicate that the
number issued by DBD.

More information:

* https://www.dbd.go.th/download/pdf_kc/s09/busin_2542-48.pdf

>>> compact('0 10 5 536 11201 4')
'0105536112014'
>>> validate('0994000617721')
'0994000617721'
>>> validate('0-99-4-000-61772-1')
'0994000617721'
>>> validate('0-99-4-000-61772-3')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> format('0993000133978')
'0-99-3-000-13397-8'
"""

from stdnum.exceptions import *
from stdnum.th import pin
from stdnum.util import clean, isdigits


__all__ = ['compact', 'calc_check_digit', 'validate', 'is_valid', 'format']


# use the same calc_check_digit function as PIN
calc_check_digit = pin.calc_check_digit


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, ' -').strip()


def validate(number):
    """Check if the number is a valid MOA Number. This checks the length,
    formatting, component and check digit."""
    number = compact(number)
    if len(number) != 13:
        raise InvalidLength()
    if not isdigits(number):
        raise InvalidFormat()
    if number[0] != '0':
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
        number[:1], number[1:3], number[3:4], number[4:7], number[7:12],
        number[12:]))
