# cf.py - functions for handling Romanian CF (VAT) numbers
# coding: utf-8
#
# Copyright (C) 2012-2020 Arthur de Jong
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

"""CF (Cod de înregistrare în scopuri de TVA, Romanian VAT number).

The Romanian CF is used for VAT purposes and can be from 2 to 10 digits long.

>>> validate('RO 185 472 90')  # VAT CUI/CIF
'RO18547290'
>>> validate('185 472 90')  # non-VAT CUI/CIF
'18547290'
>>> validate('1630615123457')  # CNP
'1630615123457'
"""

from stdnum.exceptions import *
from stdnum.ro import cnp, cui
from stdnum.util import clean


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, ' -').upper().strip()


# for backwards compatibility
calc_check_digit = cui.calc_check_digit


def validate(number):
    """Check if the number is a valid VAT number. This checks the length,
    formatting and check digit."""
    number = compact(number)
    cnumber = number
    if cnumber.startswith('RO'):
        cnumber = cnumber[2:]
    if len(cnumber) == 13:
        # apparently a CNP can also be used (however, not all sources agree)
        cnp.validate(cnumber)
    elif 2 <= len(cnumber) <= 10:
        cui.validate(cnumber)
    else:
        raise InvalidLength()
    return number


def is_valid(number):
    """Check if the number is a valid VAT number."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False
