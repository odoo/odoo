# orgnr.py - functions for handling Swedish organisation numbers
# coding: utf-8
#
# Copyright (C) 2012-2015 Arthur de Jong
# Copyright (C) 2014 Tomas Thor Jonsson
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

"""Orgnr (Organisationsnummer, Swedish company number).

The Orgnr (Organisationsnummer) is the national number to identify Swedish
companies and consists of 10 digits. These are the first 10 digits in the
Swedish VAT number, i.e. it's the VAT number without the 'SE' in front and
the '01' at the end.

>>> validate('1234567897')
'1234567897'
>>> validate('1234567891')  # invalid check digits
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> format('123456-7897')
'123456-7897'
"""

from stdnum import luhn
from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, ' -.').strip()


def validate(number):
    """Check if the number is a valid organisation number. This checks
    the length, formatting and check digit."""
    number = compact(number)
    if not isdigits(number):
        raise InvalidFormat()
    if len(number) != 10:
        raise InvalidLength()
    return luhn.validate(number)


def is_valid(number):
    """Check if the number is a valid organisation number"""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    number = compact(number)
    return number[:6] + '-' + number[6:]
