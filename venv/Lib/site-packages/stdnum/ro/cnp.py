# cnp.py - functions for handling Romanian CNP numbers
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

"""CNP (Cod Numeric Personal, Romanian Numerical Personal Code).

The CNP is a 13 digit number that includes information on the person's
gender, birth date and country zone.

More information:

* https://ro.wikipedia.org/wiki/Cod_numeric_personal
* https://github.com/vimishor/cnp-spec/blob/master/spec.md

>>> validate('1630615123457')
'1630615123457'
>>> get_county('1630615123457')
'Cluj'
>>> validate('0800101221142')  # invalid first digit
Traceback (most recent call last):
    ...
InvalidComponent: ...
>>> validate('1632215123457')  # invalid date
Traceback (most recent call last):
    ...
InvalidComponent: ...
>>> validate('1630615993454')  # invalid county
Traceback (most recent call last):
    ...
InvalidComponent: ...
>>> validate('1630615123458')  # invalid check digit
Traceback (most recent call last):
    ...
InvalidChecksum: ...
"""

import datetime

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


# The Romanian counties
_COUNTIES = {
    '01': 'Alba',
    '02': 'Arad',
    '03': 'Arges',
    '04': 'Bacau',
    '05': 'Bihor',
    '06': 'Bistrita-Nasaud',
    '07': 'Botosani',
    '08': 'Brasov',
    '09': 'Braila',
    '10': 'Buzau',
    '11': 'Caras-Severin',
    '12': 'Cluj',
    '13': 'Constanta',
    '14': 'Covasna',
    '15': 'Dambovita',
    '16': 'Dolj',
    '17': 'Galati',
    '18': 'Gorj',
    '19': 'Harghita',
    '20': 'Hunedoara',
    '21': 'Ialomita',
    '22': 'Iasi',
    '23': 'Ilfov',
    '24': 'Maramures',
    '25': 'Mehedinti',
    '26': 'Mures',
    '27': 'Neamt',
    '28': 'Olt',
    '29': 'Prahova',
    '30': 'Satu Mare',
    '31': 'Salaj',
    '32': 'Sibiu',
    '33': 'Suceava',
    '34': 'Teleorman',
    '35': 'Timis',
    '36': 'Tulcea',
    '37': 'Vaslui',
    '38': 'Valcea',
    '39': 'Vrancea',
    '40': 'Bucuresti',
    '41': 'Bucuresti - Sector 1',
    '42': 'Bucuresti - Sector 2',
    '43': 'Bucuresti - Sector 3',
    '44': 'Bucuresti - Sector 4',
    '45': 'Bucuresti - Sector 5',
    '46': 'Bucuresti - Sector 6',
    '47': 'Bucuresti - Sector 7 (desfiintat)',
    '48': 'Bucuresti - Sector 8 (desfiintat)',
    '51': 'Calarasi',
    '52': 'Giurgiu',
}


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, ' -').strip()


def calc_check_digit(number):
    """Calculate the check digit for personal codes."""
    # note that this algorithm has not been confirmed by an independent source
    weights = (2, 7, 9, 1, 4, 6, 3, 5, 8, 2, 7, 9)
    check = sum(w * int(n) for w, n in zip(weights, number)) % 11
    return '1' if check == 10 else str(check)


def get_birth_date(number):
    """Split the date parts from the number and return the birth date."""
    number = compact(number)
    centuries = {
        '1': 1900, '2': 1900, '3': 1800, '4': 1800, '5': 2000, '6': 2000,
    }  # we assume 1900 for the others in order to try to construct a date
    year = int(number[1:3]) + centuries.get(number[0], 1900)
    month = int(number[3:5])
    day = int(number[5:7])
    try:
        return datetime.date(year, month, day)
    except ValueError:
        raise InvalidComponent()


def get_county(number):
    """Get the county name from the number"""
    try:
        return _COUNTIES[compact(number)[7:9]]
    except KeyError:
        raise InvalidComponent()


def validate(number):
    """Check if the number is a valid VAT number. This checks the length,
    formatting and check digit."""
    number = compact(number)
    if not isdigits(number):
        raise InvalidFormat()
    # first digit should be a known one
    # (7,8=foreign resident, 9=other foreigner but apparently only as NIF)
    if number[0] not in '123456789':
        raise InvalidComponent()
    if len(number) != 13:
        raise InvalidLength()
    # check if birth date is valid
    get_birth_date(number)
    # TODO: check that the birth date is not in the future
    get_county(number)
    if calc_check_digit(number[:-1]) != number[-1]:
        raise InvalidChecksum()
    return number


def is_valid(number):
    """Check if the number is a valid VAT number."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False
