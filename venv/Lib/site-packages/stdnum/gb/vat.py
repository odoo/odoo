# vat.py - functions for handling United Kingdom VAT numbers
#
# Copyright (C) 2012-2021 Arthur de Jong
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

"""VAT (United Kingdom (and Isle of Man) VAT registration number).

The VAT number can either be a 9-digit standard number, a 12-digit standard
number followed by a 3-digit branch identifier, a 5-digit number for
government departments (first two digits are GD) or a 5-digit number for
health authorities (first two digits are HA). The 9-digit variants use a
weighted checksum.

>>> validate('GB 980 7806 84')
'980780684'
>>> validate('802311781')  # invalid check digit
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> format('980780684')
'980 7806 84'
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    number = clean(number, ' -.').upper().strip()
    if number.startswith('GB') or number.startswith('XI'):
        number = number[2:]
    return number


def checksum(number):
    """Calculate the checksum. The checksum is only used for the 9 digits
    of the number and the result can either be 0 or 42."""
    weights = (8, 7, 6, 5, 4, 3, 2, 10, 1)
    return sum(w * int(n) for w, n in zip(weights, number)) % 97


def validate(number):
    """Check if the number is a valid VAT number. This checks the length,
    formatting and check digit."""
    number = compact(number)
    if len(number) == 5:
        if not isdigits(number[2:]):
            raise InvalidFormat()
        if number.startswith('GD') and int(number[2:]) < 500:
            # government department
            pass
        elif number.startswith('HA') and int(number[2:]) >= 500:
            # health authority
            pass
        else:
            raise InvalidComponent()
    elif len(number) == 11 and number[0:6] in ('GD8888', 'HA8888'):
        if not isdigits(number[6:]):
            raise InvalidFormat()
        if number.startswith('GD') and int(number[6:9]) < 500:
            # government department
            pass
        elif number.startswith('HA') and int(number[6:9]) >= 500:
            # health authority
            pass
        else:
            raise InvalidComponent()
        if int(number[6:9]) % 97 != int(number[9:11]):
            raise InvalidChecksum()
    elif len(number) in (9, 12):
        if not isdigits(number):
            raise InvalidFormat()
        # standard number: nnn nnnn nn
        # branch trader: nnn nnnn nn nnn (ignore the last thee digits)
        # restarting: 100 nnnn nn
        if int(number[:3]) >= 100:
            if checksum(number[:9]) not in (0, 42, 55):
                raise InvalidChecksum()
        else:
            if checksum(number[:9]) != 0:
                raise InvalidChecksum()
    else:
        raise InvalidLength()
    return number


def is_valid(number):
    """Check if the number is a valid VAT number."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    number = compact(number)
    if len(number) == 5:
        # government department or health authority
        return number
    if len(number) == 12:
        # includes branch number
        return number[:3] + ' ' + number[3:7] + ' ' + number[7:9] + ' ' + number[9:]
    # standard number: nnn nnnn nn
    return number[:3] + ' ' + number[3:7] + ' ' + number[7:]
