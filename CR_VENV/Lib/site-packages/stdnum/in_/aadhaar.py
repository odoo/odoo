# aadhaar.py - functions for handling Indian personal identity numbers
#
# Copyright (C) 2017 Srikanth L
# Copyright (C) 2021 Gaurav Chauhan
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

"""Aadhaar (Indian personal identity number).

Aadhaar is a 12 digit identification number that can be obtained by Indian
citizens, non-residents passport holders of India and resident foreign
nationals. The number is issued by the Unique Identification Authority of
India (UIDAI).

Aadhaar is made up of 12 digits where the last digits is a check digit
calculated using the Verhoeff algorithm. The numbers are generated in a
random, non-repeating sequence and do not begin with 0 or 1.

More information:

* https://en.wikipedia.org/wiki/Aadhaar
* https://web.archive.org/web/20140611025606/http://uidai.gov.in/UID_PDF/Working_Papers/A_UID_Numbering_Scheme.pdf

>>> validate('234123412346')
'234123412346'
>>> validate('234123412347')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> validate('123412341234')  # number should not start with 0 or 1
Traceback (most recent call last):
    ...
InvalidFormat: ...
>>> validate('643343121')
Traceback (most recent call last):
    ...
InvalidLength: ...
>>> validate('222222222222')  # number cannot be a palindrome
Traceback (most recent call last):
    ...
InvalidFormat: ...
>>> format('234123412346')
'2341 2341 2346'
>>> mask('234123412346')
'XXXX XXXX 2346'
"""

import re

from stdnum import verhoeff
from stdnum.exceptions import *
from stdnum.util import clean


aadhaar_re = re.compile(r'^[2-9][0-9]{11}$')
"""Regular expression used to check syntax of Aadhaar numbers."""


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, ' -').strip()


def validate(number):
    """Check if the number provided is a valid Aadhaar number. This checks
    the length, formatting and check digit."""
    number = compact(number)
    if len(number) != 12:
        raise InvalidLength()
    if not aadhaar_re.match(number):
        raise InvalidFormat()
    if number == number[::-1]:
        raise InvalidFormat()  # Aadhaar cannot be a palindrome
    verhoeff.validate(number)
    return number


def is_valid(number):
    """Check if the number provided is a valid Aadhaar number. This checks
    the length, formatting and check digit."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    number = compact(number)
    return ' '.join((number[:4], number[4:8], number[8:]))


def mask(number):
    """Masks the first 8 digits as per Ministry of Electronics and
    Information Technology (MeitY) guidelines."""
    number = compact(number)
    return 'XXXX XXXX ' + number[-4:]
