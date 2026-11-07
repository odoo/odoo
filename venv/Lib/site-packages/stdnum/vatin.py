# vatin.py - function to validate any given VATIN.
#
# Copyright (C) 2020 Leandro Regueiro
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

"""VATIN (International value added tax identification number)

The number VAT identification number (VATIN) is an identifier used in many
countries. It starts with an ISO 3166-1 alpha-2 (2 letters) country code
(except for Greece, which uses EL, instead of GR) and is followed by the
country-specific the identifier.

This module supports all VAT numbers that are supported in python-stdnum.

More information:

* https://en.wikipedia.org/wiki/VAT_identification_number

>>> validate('FR 40 303 265 045')
'FR40303265045'
>>> validate('DE136,695 976')
'DE136695976'
>>> validate('BR16.727.230/0001-97')
'BR16727230000197'
>>> validate('FR 40 303')
Traceback (most recent call last):
    ...
InvalidLength: ...
>>> validate('XX')
Traceback (most recent call last):
    ...
InvalidComponent: ...
"""

import re

from stdnum.exceptions import *
from stdnum.util import clean, get_cc_module


# Cache of country code modules
_country_modules = dict()


def _get_cc_module(cc):
    """Get the VAT number module based on the country code."""
    # Greece uses a "wrong" country code, special case for Northern Ireland
    cc = cc.lower().replace('el', 'gr').replace('xi', 'gb')
    if not re.match(r'^[a-z]{2}$', cc):
        raise InvalidFormat()
    if cc not in _country_modules:
        _country_modules[cc] = get_cc_module(cc, 'vat')
    if not _country_modules[cc]:
        raise InvalidComponent()  # unknown/unsupported country code
    return _country_modules[cc]


def compact(number):
    """Convert the number to the minimal representation."""
    number = clean(number).strip()
    module = _get_cc_module(number[:2])
    return number[:2] + module.compact(number[2:])


def validate(number):
    """Check if the number is a valid VAT number.

    This performs the country-specific check for the number.
    """
    number = clean(number, '').strip()
    module = _get_cc_module(number[:2])
    try:
        return number[:2].upper() + module.validate(number[2:])
    except ValidationError:
        return module.validate(number)


def is_valid(number):
    """Check if the number is a valid VAT number."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False
