# isrc.py - functions for International Standard Recording Codes (ISRC)
# coding: utf-8
#
# Copyright (C) 2021 Nuno André Novo
# Copyright (C) 2021 Arthur de Jong
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

"""ISRC (International Standard Recording Code).

The ISRC is an international standard code (ISO 3901) for uniquely
identifying sound recordings and music video recordings.

More information:

* https://en.wikipedia.org/wiki/International_Standard_Recording_Code

>>> validate('US-SKG-19-12345')
'USSKG1912345'
>>> validate('XX-SKG-19-12345')
Traceback (most recent call last):
    ...
InvalidComponent: ...
"""

import re

from stdnum.exceptions import *
from stdnum.isin import _iso_3116_1_country_codes
from stdnum.util import clean


# An ISRC is composed of a country code, a registrant code a year of
# reference and designation code.
_isrc_re = re.compile(
    r'^(?P<country>[A-Z]{2})(?P<registrant>[A-Z0-9]{3})(?P<year>[0-9]{2})(?P<record>[0-9]{5})$')


# These special codes are allowed for ISRC
_country_codes = set(_iso_3116_1_country_codes + [
    'QM',  # US new registrants due to US codes became exhausted
    'CP',  # reserved for further overflow
    'DG',  # reserved for further overflow
    'ZZ',  # International ISRC Agency codes
])


def compact(number):
    """Convert the ISRC to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, ' -').strip().upper()


def validate(number):
    """Check if the number provided is a valid ISRC. This checks the length,
    the alphabet, and the country code but does not check if the registrant
    code is known."""
    number = compact(number)
    if len(number) != 12:
        raise InvalidLength()
    match = _isrc_re.search(number)
    if not match:
        raise InvalidFormat()
    if match.group('country') not in _country_codes:
        raise InvalidComponent()
    return number


def is_valid(number):
    """Check if the number provided is a valid ISRC."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number, separator='-'):
    """Reformat the number to the standard presentation format."""
    number = compact(number)
    return separator.join((number[0:2], number[2:5], number[5:7], number[7:]))
