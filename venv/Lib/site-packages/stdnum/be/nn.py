# nn.py - function for handling Belgian national numbers
# coding: utf-8
#
# Copyright (C) 2021-2022 Cédric Krier
# Copyright (C) 2023 Jeff Horemans
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

"""NN, NISS, RRN (Belgian national number).

The national registration number (Rijksregisternummer, Numéro de registre
national, Nationalregisternummer) is a unique identification number of
natural persons who are registered in Belgium.

The number consists of 11 digits and includes the person's date of birth and
gender. It encodes the date of birth in the first 6 digits in the format
YYMMDD. The following 3 digits represent a counter of people born on the same
date, seperated by sex (odd for male and even for females respectively). The
final 2 digits form a check number based on the 9 preceding digits.

Special cases include:

* Counter exhaustion:
  When the even or uneven day counter range for a specific date of birth runs
  out, (e.g. from 001 tot 997 for males), the first 2 digits will represent
  the birth year as normal, while the next 4 digits (birth month and day) are
  taken to be zeroes. The remaining 3 digits still represent a day counter
  which will then restart.
  When those ranges would run out also, the sixth digit is incremented with 1
  and the day counter will restart again.

* Incomplete date of birth
  When the exact month or day of the birth date were not known at the time of
  assignment, incomplete parts are taken to be zeroes, similarly as with
  counter exhaustion.
  Note that a month with zeroes can thus both mean the date of birth was not
  exactly known, or the person was born on a day were at least 500 persons of
  the same gender got a number assigned already.

* Unknown date of birth
  When no part of the date of birth was known, a fictitious date is used
  depending on the century (i.e. 1900/00/01 or 2000/00/01).

More information:

* https://nl.wikipedia.org/wiki/Rijksregisternummer
* https://fr.wikipedia.org/wiki/Numéro_de_registre_national
* https://www.ibz.rrn.fgov.be/fileadmin/user_upload/nl/rr/instructies/IT-lijst/IT000_Rijksregisternummer.pdf

>>> compact('85.07.30-033 28')
'85073003328'
>>> validate('85 07 30 033 28')
'85073003328'
>>> validate('17 07 30 033 84')
'17073003384'
>>> validate('12345678901')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> format('85073003328')
'85.07.30-033.28'
>>> get_birth_date('85.07.30-033 28')
datetime.date(1985, 7, 30)
>>> get_birth_year('85.07.30-033 28')
1985
>>> get_birth_month('85.07.30-033 28')
7
>>> get_gender('85.07.30-033 28')
'M'
"""

import calendar
import datetime

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips the number
    of any valid separators and removes surrounding whitespace."""
    number = clean(number, ' -.').strip()
    return number


def _checksum(number):
    """Calculate the checksum and return the detected century."""
    numbers = [number]
    if int(number[:2]) + 2000 <= datetime.date.today().year:
        numbers.append('2' + number)
    for century, n in zip((1900, 2000), numbers):
        if 97 - (int(n[:-2]) % 97) == int(n[-2:]):
            return century
    raise InvalidChecksum()


def _get_birth_date_parts(number):
    """Check if the number's encoded birth date is valid, and return the contained
    birth year, month and day of month, accounting for unknown values."""
    century = _checksum(number)

    # If the fictitious dates 1900/00/01 or 2000/00/01 are detected,
    # the birth date (including the year) was not known when the number
    # was issued.
    if number[:6] in ('000001', '002001', '004001'):
        return (None, None, None)

    year = int(number[:2]) + century
    month = int(number[2:4]) % 20
    day = int(number[4:6])
    # When the month is zero, it was either unknown when the number was issued,
    # or the day counter ran out. In both cases, the month and day are not known
    # reliably.
    if month == 0:
        return (year, None, None)

    # Verify range of month
    if month > 12:
        raise InvalidComponent('Month must be in 1..12')

    # Case when only the day of the birth date is unknown
    if day == 0 or day > calendar.monthrange(year, month)[1]:
        return (year, month, None)

    return (year, month, day)


def validate(number):
    """Check if the number is a valid National Number."""
    number = compact(number)
    if not isdigits(number) or int(number) <= 0:
        raise InvalidFormat()
    if len(number) != 11:
        raise InvalidLength()
    _get_birth_date_parts(number)
    if not 0 <= int(number[2:4]) <= 12:
        raise InvalidComponent('Month must be in 1..12')
    return number


def is_valid(number):
    """Check if the number is a valid National Number."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    number = compact(number)
    return (
        '.'.join(number[i:i + 2] for i in range(0, 6, 2)) +
        '-' + '.'.join([number[6:9], number[9:11]]))


def get_birth_year(number):
    """Return the year of the birth date."""
    year, month, day = _get_birth_date_parts(compact(number))
    return year


def get_birth_month(number):
    """Return the month of the birth date."""
    year, month, day = _get_birth_date_parts(compact(number))
    return month


def get_birth_date(number):
    """Return the date of birth."""
    year, month, day = _get_birth_date_parts(compact(number))
    if None not in (year, month, day):
        return datetime.date(year, month, day)


def get_gender(number):
    """Get the person's gender ('M' or 'F')."""
    number = compact(number)
    if int(number[6:9]) % 2:
        return 'M'
    return 'F'
