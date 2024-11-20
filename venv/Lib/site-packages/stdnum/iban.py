# iban.py - functions for handling International Bank Account Numbers (IBANs)
#
# Copyright (C) 2011-2018 Arthur de Jong
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

"""IBAN (International Bank Account Number).

The IBAN is used to identify bank accounts across national borders. The
first two letters are a country code. The next two digits are check digits
for the ISO 7064 Mod 97, 10 checksum. Each country uses its own format
for the remainder of the number.

Some countries may also use checksum algorithms within their number but
this is only checked for a few countries.

More information:

* https://en.wikipedia.org/wiki/International_Bank_Account_Number
* https://www.swift.com/products_services/bic_and_iban_format_registration_iban_format_r

>>> validate('GR16 0110 1050 0000 1054 7023 795')
'GR1601101050000010547023795'
>>> validate('BE31435411161155')
'BE31435411161155'
>>> compact('GR16 0110 1050 0000 1054 7023 795')
'GR1601101050000010547023795'
>>> format('GR1601101050000010547023795')
'GR16 0110 1050 0000 1054 7023 795'
>>> calc_check_digits('BExx435411161155')
'31'
"""

import re

from stdnum import numdb
from stdnum.exceptions import *
from stdnum.iso7064 import mod_97_10
from stdnum.util import clean, get_cc_module


# our open copy of the IBAN database
_ibandb = numdb.get('iban')

# regular expression to check IBAN structure
_struct_re = re.compile(r'([1-9][0-9]*)!([nac])')

# cache of country codes to modules
_country_modules = {}


def compact(number):
    """Convert the iban number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, ' -.').strip().upper()


def calc_check_digits(number):
    """Calculate the check digits that should be put in the number to make
    it valid. Check digits in the supplied number are ignored."""
    number = compact(number)
    return mod_97_10.calc_check_digits(number[4:] + number[:2])


def _struct_to_re(structure):
    """Convert an IBAN structure to a regular expression that can be used
    to validate the number."""
    def conv(match):
        chars = {
            'n': '[0-9]',
            'a': '[A-Z]',
            'c': '[A-Za-z0-9]',
        }[match.group(2)]
        return '%s{%s}' % (chars, match.group(1))
    return re.compile('^%s$' % _struct_re.sub(conv, structure))


def _get_cc_module(cc):
    """Get the IBAN module based on the country code."""
    cc = cc.lower()
    if cc not in _country_modules:
        _country_modules[cc] = get_cc_module(cc, 'iban')
    return _country_modules[cc]


def validate(number, check_country=True):
    """Check if the number provided is a valid IBAN. The country-specific
    check can be disabled with the check_country argument."""
    number = compact(number)
    # ensure that checksum is valid
    mod_97_10.validate(number[4:] + number[:4])
    # look up the number
    info = _ibandb.info(number)
    if not info[0][1]:
        raise InvalidComponent()
    # check if the bban part of number has the correct structure
    bban = number[4:]
    if not _struct_to_re(info[0][1].get('bban', '')).match(bban):
        raise InvalidFormat()
    # check the country-specific module if it exists
    if check_country:
        module = _get_cc_module(number[:2])
        if module:
            module.validate(number)
    # return the compact representation
    return number


def is_valid(number, check_country=True):
    """Check if the number provided is a valid IBAN."""
    try:
        return bool(validate(number, check_country=check_country))
    except ValidationError:
        return False


def format(number, separator=' '):
    """Reformat the passed number to the space-separated format."""
    number = compact(number)
    return separator.join(number[i:i + 4] for i in range(0, len(number), 4))
