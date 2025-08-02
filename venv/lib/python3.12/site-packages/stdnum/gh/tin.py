# tin.py - functions for handling Ghana TIN numbers
# coding: utf-8
#
# Copyright (C) 2022 Leandro Regueiro
# Copyright (C) 2022 Arthur de Jong
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

"""TIN (Taxpayer Identification Number, Ghana tax number).

This number is issued by the Ghana Revenue Authority (GRA) to individuals who
are not eligible for the Ghanacard PIN and other entities.

This number consists of 11 alphanumeric characters. It begins with one of the
following prefixes:

    P00 For Individuals.
    C00 For Companies limited by guarantee, shares, Unlimited (i.e organisation required to register with the RGD).
    G00 Government Agencies, MDAs.
    Q00 Foreign Missions, Employees of foreign missions.
    V00 Public Institutions, Trusts, Co-operatives, Foreign Shareholder (Offshore), (Entities not registered by RGD).

More information:

* https://www.oecd.org/tax/automatic-exchange/crs-implementation-and-assistance/tax-identification-numbers/Ghana-TIN.pdf
* https://gra.gov.gh/tin/
* https://gra.gov.gh/tin/tin-faq/

>>> validate('C0000803561')
'C0000803561'
>>> validate('C0000803562')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
"""  # noqa: E501

import re

from stdnum.exceptions import *
from stdnum.util import clean


_gh_tin_re = re.compile(r'^[PCGQV]{1}00[A-Z0-9]{8}$')


def compact(number):
    """Convert the number to the minimal representation.

    This strips the number of any valid separators and removes surrounding
    whitespace.
    """
    return clean(number, ' ').upper()


def calc_check_digit(number):
    """Calculate the check digit for the TIN."""
    check = sum((i + 1) * int(n) for i, n in enumerate(number[1:10])) % 11
    return 'X' if check == 10 else str(check)


def validate(number):
    """Check if the number is a valid Ghana TIN."""
    number = compact(number)
    if len(number) != 11:
        raise InvalidLength()
    if not _gh_tin_re.match(number):
        raise InvalidFormat()
    if number[-1] != calc_check_digit(number):
        raise InvalidChecksum()
    return number


def is_valid(number):
    """Check if the number is a valid Ghana TIN."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False
