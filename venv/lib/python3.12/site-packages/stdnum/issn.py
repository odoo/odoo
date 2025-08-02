# issn.py - functions for handling ISSNs
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

"""ISSN (International Standard Serial Number).

The ISSN (International Standard Serial Number) is the standard code to
identify periodical publications (e.g. magazines).

An ISSN has 8 digits and is formatted in two pairs of 4 digits separated by a
hyphen. The last digit is a check digit and may be 0-9 or X (similar to
ISBN-10).

More information:

* https://en.wikipedia.org/wiki/International_Standard_Serial_Number
* https://www.issn.org/

>>> validate('0024-9319')
'00249319'
>>> validate('0032147X')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> validate('003214712')
Traceback (most recent call last):
    ...
InvalidLength: ...
>>> compact('0032-1478')
'00321478'
>>> format('00249319')
'0024-9319'
>>> to_ean('0264-3596')
'9770264359008'
"""

from stdnum import ean
from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the ISSN to the minimal representation. This strips the number
    of any valid ISSN separators and removes surrounding whitespace."""
    return clean(number, ' -').strip().upper()


def calc_check_digit(number):
    """Calculate the ISSN check digit for 8-digit numbers. The number passed
    should not have the check digit included."""
    check = (11 - sum((8 - i) * int(n)
                      for i, n in enumerate(number))) % 11
    return 'X' if check == 10 else str(check)


def validate(number):
    """Check if the number is a valid ISSN. This checks the length and
    whether the check digit is correct."""
    number = compact(number)
    if not isdigits(number[:-1]):
        raise InvalidFormat()
    if len(number) != 8:
        raise InvalidLength()
    if calc_check_digit(number[:-1]) != number[-1]:
        raise InvalidChecksum()
    return number


def is_valid(number):
    """Check if the number provided is a valid ISSN."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    number = compact(number)
    return number[:4] + '-' + number[4:]


def to_ean(number, issue_code='00'):
    """Convert the number to EAN-13 format."""
    number = '977' + validate(number)[:-1] + issue_code
    return number + ean.calc_check_digit(number)
