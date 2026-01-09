# pps.py - functions for handling Irish PPS numbers
#
# Copyright (C) 2012, 2013 Arthur de Jong
# Copyright (C) 2014 Olivier Dony
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

"""PPS No (Personal Public Service Number, Irish personal number).

The Personal Public Service number consists of 7 digits, and one or
two letters. The first letter is a check character.
When present (which should be the case for new numbers as of 2013),
the second letter can be 'A' (for individuals) or 'H' (for
non-individuals, such as limited companies, trusts, partnerships
and unincorporated bodies). Pre-2013 values may have 'W', 'T',
or 'X' as the second letter ; it is ignored by the check.

>>> validate('6433435F')  # pre-2013
'6433435F'
>>> validate('6433435FT')  # pre-2013 with special final 'T'
'6433435FT'
>>> validate('6433435FW')  # pre-2013 format for married women
'6433435FW'
>>> validate('6433435E')  # incorrect check digit
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> validate('6433435OA')  # 2013 format (personal)
'6433435OA'
>>> validate('6433435IH')  # 2013 format (non-personal)
'6433435IH'
>>> validate('6433435VH')  # 2013 format (incorrect check)
Traceback (most recent call last):
    ...
InvalidChecksum: ...
"""

import re

from stdnum.exceptions import *
from stdnum.ie import vat
from stdnum.util import clean


pps_re = re.compile(r'^\d{7}[A-W][AHWTX]?$')
"""Regular expression used to check syntax of PPS numbers."""


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, ' -').upper().strip()


def validate(number):
    """Check if the number provided is a valid PPS number. This checks the
    length, formatting and check digit."""
    number = compact(number)
    if not pps_re.match(number):
        raise InvalidFormat()
    if len(number) == 9 and number[8] in 'AH':
        # new 2013 format
        if number[7] != vat.calc_check_digit(number[:7] + number[8:]):
            raise InvalidChecksum()
    else:
        # old format, last letter ignored
        if number[7] != vat.calc_check_digit(number[:7]):
            raise InvalidChecksum()
    return number


def is_valid(number):
    """Check if the number provided is a valid PPS number. This checks the
    length, formatting and check digit."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False
