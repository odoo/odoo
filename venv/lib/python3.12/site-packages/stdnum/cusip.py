# cusip.py - functions for handling CUSIP numbers
#
# Copyright (C) 2015-2022 Arthur de Jong
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

"""CUSIP number (financial security identification number).

CUSIP (Committee on Uniform Securities Identification Procedures) numbers are
used to identify financial securities. CUSIP numbers are a nine-character
alphanumeric code where the first six characters identify the issuer,
followed by two digits that identify and a check digit.

More information:

* https://en.wikipedia.org/wiki/CUSIP
* https://www.cusip.com/

>>> validate('DUS0421C5')
'DUS0421C5'
>>> validate('DUS0421CN')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> to_isin('91324PAE2')
'US91324PAE25'
"""

from stdnum.exceptions import *
from stdnum.util import clean


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, ' ').strip().upper()


_alphabet = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ*@#'


def calc_check_digit(number):
    """Calculate the check digits for the number."""
    # convert to numeric first, then sum individual digits
    number = ''.join(
        str((1, 2)[i % 2] * _alphabet.index(n)) for i, n in enumerate(number))
    return str((10 - sum(int(n) for n in number)) % 10)


def validate(number):
    """Check if the number provided is valid. This checks the length and
    check digit."""
    number = compact(number)
    if not all(x in _alphabet for x in number):
        raise InvalidFormat()
    if len(number) != 9:
        raise InvalidLength()
    if calc_check_digit(number[:-1]) != number[-1]:
        raise InvalidChecksum()
    return number


def is_valid(number):
    """Check if the number provided is valid. This checks the length and
    check digit."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def to_isin(number):
    """Convert the number to an ISIN."""
    from stdnum import isin
    return isin.from_natid('US', number)
