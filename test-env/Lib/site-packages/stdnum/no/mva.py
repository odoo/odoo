# mva.py - functions for handling Norwegian VAT numbers
# coding: utf-8
#
# Copyright (C) 2015 Tuomas Toivonen
# Copyright (C) 2015 Arthur de Jong
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

"""MVA (Merverdiavgift, Norwegian VAT number).

The VAT number is the standard Norwegian organisation number
(Organisasjonsnummer) with 'MVA' as suffix.

>>> validate('NO 995 525 828 MVA')
'995525828MVA'
>>> validate('NO 995 525 829 MVA')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> format('995525828MVA')
'NO 995 525 828 MVA'
"""

from stdnum.exceptions import *
from stdnum.no import orgnr
from stdnum.util import clean


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    number = clean(number, ' ').upper().strip()
    if number.startswith('NO'):
        number = number[2:]
    return number


def validate(number):
    """Check if the number is a valid MVA number. This checks the length,
    formatting and check digit."""
    number = compact(number)
    if not number.endswith('MVA'):
        raise InvalidFormat()
    orgnr.validate(number[:-3])
    return number


def is_valid(number):
    """Check if the number is a valid MVA number."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    number = compact(number)
    return 'NO ' + orgnr.format(number[:9]) + ' ' + number[9:]
