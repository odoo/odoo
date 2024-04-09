# tin.py - functions for handling South Africa ID number
# coding: utf-8
#
# Copyright (C) 2020 Arthur de Jong
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

"""ID number (South African Identity Document number).

The South African ID number is issued to individuals within South Africa. The
number consists of 13 digits and contains information about a person's date
of birth, gender and whether the person is a citizen or permanent resident.

More information:

* https://en.wikipedia.org/wiki/South_African_identity_card
* http://www.dha.gov.za/index.php/identity-documents2

>>> validate('7503305044089')
'7503305044089'
>>> validate('8503305044089')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> validate('9125568')
Traceback (most recent call last):
    ...
InvalidLength: ...
>>> get_gender('7503305044089')
'M'
>>> get_birth_date('7503305044089')
datetime.date(1975, 3, 30)
>>> get_citizenship('7503305044089')
'citizen'
>>> format('750330 5044089')
'750330 5044 08 9'
"""

import datetime

from stdnum import luhn
from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation.

    This strips the number of any valid separators and removes surrounding
    whitespace.
    """
    return clean(number, ' ')


def get_birth_date(number):
    """Split the date parts from the number and return the date of birth.

    Since the number only uses two digits for the year, the century may be
    incorrect.
    """
    number = compact(number)
    today = datetime.date.today()
    year = int(number[0:2]) + (100 * (today.year // 100))
    month = int(number[2:4])
    day = int(number[4:6])
    if year > today.year:
        year -= 100
    try:
        return datetime.date(year, month, day)
    except ValueError:
        raise InvalidComponent()


def get_gender(number):
    """Get the gender (M/F) from the person's ID number."""
    number = compact(number)
    if number[6] in '01234':
        return 'F'
    else:
        return 'M'


def get_citizenship(number):
    """Get the citizenship status (citizen/resident) from the ID number."""
    number = compact(number)
    if number[10] == '0':
        return 'citizen'
    elif number[10] == '1':
        return 'resident'
    else:
        raise InvalidComponent()


def validate(number):
    """Check if the number is a valid South African ID number.

    This checks the length, formatting and check digit.
    """
    number = compact(number)
    if not isdigits(number):
        raise InvalidFormat()
    if len(number) != 13:
        raise InvalidLength()
    get_birth_date(number)
    get_citizenship(number)
    return luhn.validate(number)


def is_valid(number):
    """Check if the number is a valid South African ID number."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    number = compact(number)
    return ' '.join((number[:6], number[6:10], number[10:12], number[12:]))
