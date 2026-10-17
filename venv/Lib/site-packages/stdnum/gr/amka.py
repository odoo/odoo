# amka.py - functions for handling Greek social security numbers
# coding: utf-8
#
# Copyright (C) 2019 Arthur de Jong
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

"""AMKA (Αριθμός Μητρώου Κοινωνικής Ασφάλισης, Greek social security number).

The Αριθμός Μητρώου Κοινωνικής Ασφάλισης (AMKA or Arithmos Mitroou Koinonikis
Asfalisis) is the personal identifier that is used for social security
purposes in Greece. The number consists of 11 digits and includes the
person's date of birth and gender.

More information:

* https://www.amka.gr/tieinai_en.html

>>> validate('01013099997')
'01013099997'
>>> validate('01013099999')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> get_birth_date('01013099997')
datetime.date(1930, 1, 1)
>>> get_gender('01013099997')
'M'
"""

import datetime

from stdnum import luhn
from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, ' -').strip()


def get_birth_date(number):
    """Split the date parts from the number and return the date of birth.
    Since only two digits are used for the year, the century may be
    incorrect."""
    number = compact(number)
    day = int(number[0:2])
    month = int(number[2:4])
    year = int(number[4:6]) + 1900
    try:
        return datetime.date(year, month, day)
    except ValueError:
        try:
            return datetime.date(year + 100, month, day)
        except ValueError:
            raise InvalidComponent()


def get_gender(number):
    """Get the gender (M/F) from the person's AMKA."""
    number = compact(number)
    if int(number[9]) % 2:
        return 'M'
    else:
        return 'F'


def validate(number):
    """Check if the number is a valid AMKA. This checks the length,
    formatting and check digit."""
    number = compact(number)
    if not isdigits(number):
        raise InvalidFormat()
    if len(number) != 11:
        raise InvalidLength()
    luhn.validate(number)
    get_birth_date(number)
    return number


def is_valid(number):
    """Check if the number is a valid AMKA."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False
