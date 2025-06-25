# personnummer.py - functions for handling Swedish Personal identity numbers
# coding: utf-8
#
# Copyright (C) 2018 Ilya Vihtinsky
# Copyright (C) 2018-2020 Arthur de Jong
# Copyright (C) 2020 Leon Sandøy
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

"""Personnummer (Swedish personal identity number).

The Swedish Personnummer is assigned at birth to all Swedish nationals and to
immigrants for tax and identification purposes. The number consists of 10 or
12 digits and starts with the birth date, followed by a serial and a check
digit.

More information:

* https://en.wikipedia.org/wiki/Personal_identity_number_(Sweden)

>>> validate('880320-0016')
'880320-0016'
>>> validate('880320-0018')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> get_gender('890102-3286')
'F'
>>> get_birth_date('811228-9841')
datetime.date(1981, 12, 28)
>>> format('8803200016')
'880320-0016'
"""

import datetime

from stdnum import luhn
from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    number = clean(number, ' :')
    if len(number) in (10, 12) and number[-5] not in '-+':
        number = '%s-%s' % (number[:-4], number[-4:])
    return number[:-5].replace('-', '').replace('+', '') + number[-5:]


def get_birth_date(number):
    """Determine the birth date from the number.

    For people aged 100 and up, the minus/dash in the personnummer is changed to a plus
    on New Year's Eve the year they turn 100.

    See Folkbokföringslagen (1991:481), §18.
    """
    number = compact(number)
    if len(number) == 13:
        year = int(number[0:4])
        month = int(number[4:6])
        day = int(number[6:8])
    else:
        year = datetime.date.today().year
        century = year // 100
        if int(number[0:2]) > year % 100:
            century -= 1
        if number[-5] == '+':
            century -= 1
        year = int('%d%s' % (century, number[0:2]))
        month = int(number[2:4])
        day = int(number[4:6])
    try:
        return datetime.date(year, month, day)
    except ValueError:
        raise InvalidComponent()


def get_gender(number):
    """Get the person's birth gender ('M' or 'F')."""
    number = compact(number)
    if int(number[-2]) % 2:
        return 'M'
    else:
        return 'F'


def validate(number):
    """Check if the number is a valid identity number."""
    number = compact(number)
    if len(number) not in (11, 13):
        raise InvalidLength()
    digits = number[:-5] + number[-4:]
    if number[-5] not in '-+' or not isdigits(digits):
        raise InvalidFormat()
    get_birth_date(number)
    luhn.validate(digits[-10:])
    return number


def is_valid(number):
    """Check if the number is a valid identity number."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    return compact(number)
