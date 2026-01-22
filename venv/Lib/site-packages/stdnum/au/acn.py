# acn.py - functions for handling Australian Company Numbers (ACNs)
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

"""ACN (Australian Company Number).

The Australian Company Number (ACN) is a company identifier issued by the
Australian Securities and Investments Commission.

More information:

* https://en.wikipedia.org/wiki/Australian_Company_Number

>>> validate('004 085 616')
'004085616'
>>> validate('010 499 966')
'010499966'
>>> validate('999 999 999')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> format('004085616')
'004 085 616'
>>> to_abn('002 724 334')
'43002724334'
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, ' ').strip()


def calc_check_digit(number):
    """Calculate the checksum."""
    return str((sum(int(n) * (i - 8) for i, n in enumerate(number))) % 10)


def validate(number):
    """Check if the number is a valid ACN. This checks the length, formatting
    and check digit."""
    number = compact(number)
    if not isdigits(number):
        raise InvalidFormat()
    if len(number) != 9:
        raise InvalidLength()
    if calc_check_digit(number) != number[-1]:
        raise InvalidChecksum()
    return number


def is_valid(number):
    """Check if the number is a valid ACN."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    number = compact(number)
    return ' '.join((number[0:3], number[3:6], number[6:]))


def to_abn(number):
    """Convert the number to an Australian Business Number (ABN)."""
    from stdnum.au import abn
    number = compact(number)
    return abn.calc_check_digits(number) + number
