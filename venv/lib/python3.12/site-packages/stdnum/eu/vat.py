# vat.py - functions for handling European VAT numbers
# coding: utf-8
#
# Copyright (C) 2012-2021 Arthur de Jong
# Copyright (C) 2015 Lionel Elie Mamane
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

"""VAT (European Union VAT number).

The European Union VAT number consists of a 2 letter country code (ISO
3166-1, except Greece which uses EL) followed by a number that is
allocated per country.

The exact format of the numbers varies per country and a country-specific
check is performed on the number using the VAT module that is relevant for
that country.

>>> compact('ATU 57194903')
'ATU57194903'
>>> validate('BE697449992')
'BE0697449992'
>>> validate('FR 61 954 506 077')
'FR61954506077'
>>> guess_country('00449544B01')
['nl']
"""

from stdnum.eu import oss
from stdnum.exceptions import *
from stdnum.util import clean, get_cc_module, get_soap_client


MEMBER_STATES = set([
    'at', 'be', 'bg', 'cy', 'cz', 'de', 'dk', 'ee', 'es', 'fi', 'fr', 'gr',
    'hr', 'hu', 'ie', 'it', 'lt', 'lu', 'lv', 'mt', 'nl', 'pl', 'pt', 'ro',
    'se', 'si', 'sk', 'xi',
])
"""The collection of country codes that are queried. Greece is listed with a
country code of gr while for VAT purposes el is used instead. For Northern
Ireland numbers are prefixed with xi of United Kingdom numbers."""

_country_modules = dict()

vies_wsdl = 'https://ec.europa.eu/taxation_customs/vies/checkVatService.wsdl'
"""The WSDL URL of the VAT Information Exchange System (VIES)."""


def _get_cc_module(cc):
    """Get the VAT number module based on the country code."""
    # Greece uses a "wrong" country code
    cc = cc.lower()
    if cc in ('eu', 'im'):
        return oss
    if cc == 'el':
        cc = 'gr'
    if cc not in MEMBER_STATES:
        return
    if cc == 'xi':
        cc = 'gb'
    if cc not in _country_modules:
        _country_modules[cc] = get_cc_module(cc, 'vat')
    return _country_modules[cc]


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    number = clean(number, '').upper().strip()
    cc = number[:2]
    module = _get_cc_module(cc)
    if not module:
        raise InvalidComponent()
    number = module.compact(number)
    if not number.startswith(cc):
        number = cc + number
    return number


def validate(number):
    """Check if the number is a valid VAT number. This performs the
    country-specific check for the number."""
    number = clean(number, '').upper().strip()
    cc = number[:2]
    module = _get_cc_module(cc)
    if not module:
        raise InvalidComponent()
    number = module.validate(number)
    if not number.startswith(cc):
        number = cc + number
    return number


def is_valid(number):
    """Check if the number is a valid VAT number. This performs the
    country-specific check for the number."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def guess_country(number):
    """Guess the country code based on the number. This checks the number
    against each of the validation routines and returns the list of countries
    for which it is valid. This returns lower case codes and returns gr (not
    el) for Greece."""
    return [cc
            for cc in MEMBER_STATES
            if _get_cc_module(cc).is_valid(number)]


def check_vies(number, timeout=30):  # pragma: no cover (not part of normal test suite)
    """Query the online European Commission VAT Information Exchange System
    (VIES) for validity of the provided number. Note that the service has
    usage limitations (see the VIES website for details). The timeout is in
    seconds. This returns a dict-like object."""
    # this function isn't automatically tested because it would require
    # network access for the tests and unnecessarily load the VIES website
    number = compact(number)
    client = get_soap_client(vies_wsdl, timeout)
    return client.checkVat(number[:2], number[2:])


def check_vies_approx(number, requester, timeout=30):  # pragma: no cover
    """Query the online European Commission VAT Information Exchange System
    (VIES) for validity of the provided number, providing a validity
    certificate as proof. You will need to give your own VAT number for this
    to work. Note that the service has usage limitations (see the VIES
    website for details). The timeout is in seconds. This returns a dict-like
    object."""
    # this function isn't automatically tested because it would require
    # network access for the tests and unnecessarily load the VIES website
    number = compact(number)
    requester = compact(requester)
    client = get_soap_client(vies_wsdl, timeout)
    return client.checkVatApprox(
        countryCode=number[:2], vatNumber=number[2:],
        requesterCountryCode=requester[:2], requesterVatNumber=requester[2:])
