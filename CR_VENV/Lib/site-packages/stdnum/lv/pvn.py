# pvn.py - functions for handling Latvian PVN (VAT) numbers
# coding: utf-8
#
# Copyright (C) 2012-2019 Arthur de Jong
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

"""PVN (Pievienotās vērtības nodokļa, Latvian VAT number).

The PVN is a 11-digit number that can either be a reference to a legal
entity (in which case the first digit > 3) or a natural person (in which
case it should be the same as the personal code (personas kods)). Personal
codes start with 6 digits to denote the birth date in the form ddmmyy.

>>> validate('LV 4000 3521 600')
'40003521600'
>>> validate('40003521601')  # invalid check digit
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> validate('161175-19997')  # personal code
'16117519997'
>>> validate('161375-19997')  # invalid date
Traceback (most recent call last):
    ...
InvalidComponent: ...
"""

import datetime

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


# validation functions are available on-line but it is not allowed
# to perform automated queries:
# https://www6.vid.gov.lv/VID_PDB?aspxerrorpath=/vid_pdb/pvn.asp


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    number = clean(number, ' -').upper().strip()
    if number.startswith('LV'):
        number = number[2:]
    return number


def checksum(number):
    """Calculate the checksum for legal entities."""
    weights = (9, 1, 4, 8, 3, 10, 2, 5, 7, 6, 1)
    return sum(w * int(n) for w, n in zip(weights, number)) % 11


def calc_check_digit_pers(number):
    """Calculate the check digit for personal codes. The number passed
    should not have the check digit included."""
    # note that this algorithm has not been confirmed by an independent source
    weights = (10, 5, 8, 4, 2, 1, 6, 3, 7, 9)
    check = 1 + sum(w * int(n) for w, n in zip(weights, number))
    return str(check % 11 % 10)


def get_birth_date(number):
    """Split the date parts from the number and return the birth date."""
    number = compact(number)
    day = int(number[0:2])
    month = int(number[2:4])
    year = int(number[4:6])
    year += 1800 + int(number[6]) * 100
    try:
        return datetime.date(year, month, day)
    except ValueError:
        raise InvalidComponent()


def validate(number):
    """Check if the number is a valid VAT number. This checks the length,
    formatting and check digit."""
    number = compact(number)
    if not isdigits(number):
        raise InvalidFormat()
    if len(number) != 11:
        raise InvalidLength()
    if number[0] > '3':
        # legal entity
        if checksum(number) != 3:
            raise InvalidChecksum()
    else:
        # natural resident, check if birth date is valid
        get_birth_date(number)
        # TODO: check that the birth date is not in the future
        if calc_check_digit_pers(number[:-1]) != number[-1]:
            raise InvalidChecksum()
    return number


def is_valid(number):
    """Check if the number is a valid VAT number."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False
