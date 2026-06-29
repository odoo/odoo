# uen.py - functions for handling Singapore UEN numbers
# coding: utf-8
#
# Copyright (C) 2020 Leandro Regueiro
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

"""UEN (Singapore's Unique Entity Number).

The Unique Entity Number (UEN) is a 9 or 10 digit identification issued by
the government of Singapore to businesses that operate within Singapore.


Accounting and Corporate Regulatory Authority (ACRA)

There are three different formats:

* Business (ROB): It consists of 8 digits followed by a check letter.
* Local Company (ROC): It consists of 9 digits (the 4 leftmost digits
  represent the year of issuance) followed by a check letter.
* Others: Consists of 10 characters, begins with either the R letter, or the
  S letter or the T letter followed by 2 digits representing the last two
  digits of the issuance year, followed by two letters representing the
  entity type, 4 digits and finally a check letter.

More information:

* https://www.oecd.org/tax/automatic-exchange/crs-implementation-and-assistance/tax-identification-numbers/Singapore-TIN.pdf
* https://www.uen.gov.sg/ueninternet/faces/pages/admin/aboutUEN.jspx

>>> validate('00192200M')
'00192200M'
>>> validate('197401143C')
'197401143C'
>>> validate('S16FC0121D')
'S16FC0121D'
>>> validate('T01FC6132D')
'T01FC6132D'
>>> validate('123456')
Traceback (most recent call last):
    ...
InvalidLength: ...
"""  # noqa: E501

# There are some references to special 10-digit (or 7-digit) numbers that
# start with an F for foreign companies but it is unclear whether this is
# still current and not even examples of these numbers could be found.

from datetime import datetime

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


OTHER_UEN_ENTITY_TYPES = (
    'CC', 'CD', 'CH', 'CL', 'CM', 'CP', 'CS', 'CX', 'DP', 'FB', 'FC', 'FM',
    'FN', 'GA', 'GB', 'GS', 'HS', 'LL', 'LP', 'MB', 'MC', 'MD', 'MH', 'MM',
    'MQ', 'NB', 'NR', 'PA', 'PB', 'PF', 'RF', 'RP', 'SM', 'SS', 'TC', 'TU',
    'VH', 'XL',
)


def compact(number):
    """Convert the number to the minimal representation.

    This converts to uppercase and removes surrounding whitespace. It
    also replaces the whitespace in UEN for foreign companies with
    zeroes.
    """
    return clean(number).upper().strip()


def calc_business_check_digit(number):
    """Calculate the check digit for the Business (ROB) number."""
    number = compact(number)
    weights = (10, 4, 9, 3, 8, 2, 7, 1)
    return 'XMKECAWLJDB'[sum(int(n) * w for n, w in zip(number, weights)) % 11]


def _validate_business(number):
    """Perform validation on UEN - Business (ROB) numbers."""
    if not isdigits(number[:-1]):
        raise InvalidFormat()
    if not number[-1].isalpha():
        raise InvalidFormat()
    if number[-1] != calc_business_check_digit(number):
        raise InvalidChecksum()
    return number


def calc_local_company_check_digit(number):
    """Calculate the check digit for the Local Company (ROC) number."""
    number = compact(number)
    weights = (10, 8, 6, 4, 9, 7, 5, 3, 1)
    return 'ZKCMDNERGWH'[sum(int(n) * w for n, w in zip(number, weights)) % 11]


def _validate_local_company(number):
    """Perform validation on UEN - Local Company (ROC) numbers."""
    if not isdigits(number[:-1]):
        raise InvalidFormat()
    current_year = str(datetime.now().year)
    if number[:4] > current_year:
        raise InvalidComponent()
    if number[-1] != calc_local_company_check_digit(number):
        raise InvalidChecksum()
    return number


def calc_other_check_digit(number):
    """Calculate the check digit for the other entities number."""
    number = compact(number)
    alphabet = 'ABCDEFGHJKLMNPQRSTUVWX0123456789'
    weights = (4, 3, 5, 3, 10, 2, 2, 5, 7)
    return alphabet[(sum(alphabet.index(n) * w for n, w in zip(number, weights)) - 5) % 11]


def _validate_other(number):
    """Perform validation on other UEN numbers."""
    if number[0] not in ('R', 'S', 'T'):
        raise InvalidComponent()
    if not isdigits(number[1:3]):
        raise InvalidFormat()
    current_year = str(datetime.now().year)
    if number[0] == 'T' and number[1:3] > current_year[2:]:
        raise InvalidComponent()
    if number[3:5] not in OTHER_UEN_ENTITY_TYPES:
        raise InvalidComponent()
    if not isdigits(number[5:-1]):
        raise InvalidFormat()
    if number[-1] != calc_other_check_digit(number):
        raise InvalidChecksum()
    return number


def validate(number):
    """Check if the number is a valid Singapore UEN number."""
    number = compact(number)
    if len(number) not in (9, 10):
        raise InvalidLength()
    if len(number) == 9:
        return _validate_business(number)
    if isdigits(number[0]):
        return _validate_local_company(number)
    return _validate_other(number)


def is_valid(number):
    """Check if the number is a valid Singapore UEN number."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    return compact(number)
