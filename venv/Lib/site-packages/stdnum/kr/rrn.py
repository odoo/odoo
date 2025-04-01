# rrn.py - functions for handling South Korean RRN numbers
# coding: utf-8
#
# Copyright (C) 2019 Dimitri Papadopoulos
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

"""RRN (South Korean resident registration number).

The RRN (resident registration number, 주민등록번호) is a 13-digit number
issued to all residents of the Republic of Korea. Foreigners residing in the
Republic of Korea receive an alien registration number (ARN) which follows
the same encoding pattern.

The first six digits code the date of birth. The seventh digit encodes the
century and gender. The next four digits encode the place of birth for
Koreans or the issuing agency for foreigners, followed by two digits for the
community center number, one serial number and a check digit.

More information:

* https://www.law.go.kr/lsSc.do?tabMenuId=tab18&p1=&subMenu=1&nwYn=1&section=&tabNo=&query=개인정보+보호법
* https://en.wikipedia.org/wiki/Resident_registration_number
* https://techscience.org/a/2015092901/

>>> validate('971013-9019902')
'9710139019902'
>>> validate('971013-9019903')  # incorrect checksum
Traceback (most recent call last):
    ...
InvalidChecksum: ...
"""

import datetime

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, '-').strip()


def calc_check_digit(number):
    """Calculate the check digit."""
    weights = (2, 3, 4, 5, 6, 7, 8, 9, 2, 3, 4, 5)
    check = sum(w * int(n) for w, n in zip(weights, number))
    return str((11 - (check % 11)) % 10)


def get_birth_date(number, allow_future=True):
    """Split the date parts from the number and return the birth date. If
    allow_future is False birth dates in the future are rejected."""
    number = compact(number)
    year = int(number[0:2])
    month = int(number[2:4])
    day = int(number[4:6])
    if number[6] in '1256':  # born 1900-1999
        year += 1900
    elif number[6] in '3478':  # born 2000-2099
        year += 2000
    else:  # born 1800-1899
        year += 1800
    try:
        date_of_birth = datetime.date(year, month, day)
    except ValueError:
        raise InvalidComponent()
    else:
        # The resident registration number is given to each Korean citizen
        # at birth or by naturalization, although the resident registration
        # card is issued upon the 17th birthday.
        if not allow_future and date_of_birth >= datetime.date.today():
            raise InvalidComponent()
    return date_of_birth


def validate(number, allow_future=True):
    """Check if the number is a valid RNN. This checks the length, formatting
    and check digit. If allow_future is False birth dates in the future are
    rejected."""
    number = compact(number)
    if not isdigits(number):
        raise InvalidFormat()
    if len(number) != 13:
        raise InvalidLength()
    get_birth_date(number, allow_future)
    place_of_birth = int(number[7:9])
    if place_of_birth > 96:
        raise InvalidComponent()
    # We cannot check the community center (CC), any information on
    # valid/invalid CC digits is welcome.
    if number[-1] != calc_check_digit(number[:-1]):
        raise InvalidChecksum()
    return number


def is_valid(number, allow_future=True):
    """Check if the number provided is valid."""
    try:
        return bool(validate(number, allow_future))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    number = compact(number)
    if len(number) == 13:
        number = number[:6] + '-' + number[6:]
    return number
