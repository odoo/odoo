# cnic.py - functions for handling Pakistani CNIC numbers
# coding: utf-8
#
# Copyright (C) 2022 Syed Haseeb Shah
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

"""CNIC number (Pakistani Computerised National Identity Card number).

The CNIC (Computerised National Identity Card, قومی شناختی کارڈ) or SNIC
(Smart National Identity Card) is issued by by Pakistan's NADRA (National
Database and Registration Authority) to citizens of 18 years or older.

The number consists of 13 digits and encodes the person's locality (5
digits), followed by 7 digit serial number an a single digit indicating
gender.

More Information:

* https://en.wikipedia.org/wiki/CNIC_(Pakistan)
* https://www.nadra.gov.pk/identity/identity-cnic/

>>> validate('34201-0891231-8')
'3420108912318'
>>> validate('42201-0397640-8')
'4220103976408'
>>> get_gender('42201-0397640-8')
'F'
>>> get_province('42201-0397640-8')
'Sindh'
>>> format('3420108912318')
'34201-0891231-8'
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, '-').strip()


def get_gender(number):
    """Get the person's birth gender ('M' or 'F')."""
    number = compact(number)
    if number[-1] in '13579':
        return 'M'
    elif number[-1] in '2468':
        return 'F'


# Valid Province IDs
PROVINCES = {
    '1': 'Khyber Pakhtunkhwa',
    '2': 'FATA',
    '3': 'Punjab',
    '4': 'Sindh',
    '5': 'Balochistan',
    '6': 'Islamabad',
    '7': 'Gilgit-Baltistan',
}


def get_province(number):
    """Get the person's birth gender ('M' or 'F')."""
    number = compact(number)
    return PROVINCES.get(number[0])


def validate(number):
    """Check if the number is a valid CNIC. This checks the length, formatting
    and some digits."""
    number = compact(number)
    if not isdigits(number):
        raise InvalidFormat()
    if len(number) != 13:
        raise InvalidLength()
    if not get_gender(number):
        raise InvalidComponent()
    if not get_province(number):
        raise InvalidComponent()
    return number


def is_valid(number):
    """Check if the number is a valid CNIC."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    number = compact(number)
    return '-'.join((number[:5], number[5:12], number[12:]))
