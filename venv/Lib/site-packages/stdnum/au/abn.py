# abn.py - functions for handling Australian Business Numbers (ABNs)
#
# Copyright (C) 2016 Vincent Bastos
# Copyright (C) 2016 Arthur de Jong
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

"""ABN (Australian Business Number).

The Australian Business Number (ABN) is an identifier issued to entities
registered in the Australian Business Register (ABR). The number consists of
11 digits of which the first two are check digits.

More information:

* https://en.wikipedia.org/wiki/Australian_Business_Number
* https://abr.business.gov.au/

>>> validate('83 914 571 673')
'83914571673'
>>> validate('99 999 999 999')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> format('51824753556')
'51 824 753 556'
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, ' ').strip()


def calc_check_digits(number):
    """Calculate the check digits that should be prepended to make the number
    valid."""
    weights = (3, 5, 7, 9, 11, 13, 15, 17, 19)
    s = sum(-w * int(n) for w, n in zip(weights, number))
    return str(11 + (s - 1) % 89)


def validate(number):
    """Check if the number is a valid ABN. This checks the length, formatting
    and check digit."""
    number = compact(number)
    if not isdigits(number):
        raise InvalidFormat()
    if len(number) != 11:
        raise InvalidLength()
    if calc_check_digits(number[2:]) != number[:2]:
        raise InvalidChecksum()
    return number


def is_valid(number):
    """Check if the number is a valid ABN."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    number = compact(number)
    return ' '.join((number[0:2], number[2:5], number[5:8], number[8:]))
