# sedol.py - functions for handling SEDOL numbers
#
# Copyright (C) 2015 Arthur de Jong
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

"""SEDOL number (Stock Exchange Daily Official List number).

The SEDOL number is a security identifier used in the United Kingdom and
Ireland assigned by the London Stock Exchange. A SEDOL is seven characters
in length consisting of six alphanumeric digits, followed by a check digit.

>>> validate('B15KXQ8')
'B15KXQ8'
>>> validate('B15KXQ7')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> to_isin('B15KXQ8')
'GB00B15KXQ89'
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


# the letters allowed in an SEDOL (vowels are never used)
_alphabet = '0123456789 BCD FGH JKLMN PQRST VWXYZ'


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, ' ').strip().upper()


def calc_check_digit(number):
    """Calculate the check digits for the number."""
    weights = (1, 3, 1, 7, 3, 9)
    s = sum(w * _alphabet.index(n) for w, n in zip(weights, number))
    return str((10 - s) % 10)


def validate(number):
    """Check if the number is valid. This checks the length and check
    digit."""
    number = compact(number)
    if not all(x in _alphabet for x in number):
        raise InvalidFormat()
    if len(number) != 7:
        raise InvalidLength()
    if isdigits(number[0]) and not isdigits(number):
        # new style SEDOLs are supposed to start with a letter, old-style
        # numbers should be fully numeric
        raise InvalidFormat()
    if calc_check_digit(number[:-1]) != number[-1]:
        raise InvalidChecksum()
    return number


def is_valid(number):
    """Check if the number is valid."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def to_isin(number):
    """Convert the number to an ISIN."""
    from stdnum import isin
    return isin.from_natid('GB', number)
