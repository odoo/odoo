# oss.py - functions for handling European VAT numbers
# coding: utf-8
#
# Copyright (C) 2023 Arthur de Jong
# Copyright (C) 2023 Sergi Almacellas Abellana
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

"""OSS (European VAT on e-Commerce - One Stop Shop).

This covers number that have been issued under the non-union scheme and the
import scheme of the European VAT on e-Commerce one stop shop. Numbers under
the non-union scheme are assigned to foreign companies providing digital
services to European Union consumers. Numbers under the import scheme are
assigned for importing goods from a third country (through an intermediary).

This is also called MOSS (mini One Stop Shop) and VoeS (VAT on e-Services).
The number under the import scheme is also called IOSS (Import One Stop Shop)
number.

Numbers under the non-union scheme are in the format EUxxxyyyyyz. For the
import scheme the format is IMxxxyyyyyyz. An intermediary will also get an
number in the format INxxxyyyyyyz but that may not be used as VAT
identification number.

There appears to be a check digit algorithm but the FITSDEV2-SC12-TS-Mini1SS
(Mini-1SS – Technical Specifications) document that describes the algorithm
appears to not be publicly available.

More information:

* https://vat-one-stop-shop.ec.europa.eu/one-stop-shop/register-oss_en
* https://europa.eu/youreurope/business/taxation/vat/vat-digital-services-moss-scheme/index_en.htm
* https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32002L0038

>>> validate('EU 372022452')
'EU372022452'
"""


from stdnum.exceptions import *
from stdnum.util import clean, isdigits


ISO_3166_1_MEMBER_STATES = (
    '040',  # Austria
    '056',  # Belgium
    '100',  # Bulgaria
    '191',  # Croatia
    '196',  # Cyprus
    '203',  # Czechia
    '208',  # Denmark
    '233',  # Estonia
    '246',  # Finland
    '250',  # France
    '276',  # Germany
    '300',  # Greece
    '348',  # Hungary
    '372',  # Ireland
    '380',  # Italy
    '428',  # Latvia
    '440',  # Lithuania
    '442',  # Luxembourg
    '470',  # Malta
    '528',  # Netherland
    '616',  # Poland
    '620',  # Portugal
    '642',  # Romania
    '703',  # Slovakia
    '705',  # Slovenia
    '724',  # Spain
    '752',  # Sweden
    '900',  # N. Ireland
)
"""The collection of member state codes (for MSI) that may make up a VAT number."""


def compact(number):
    """Compact European VAT Number"""
    return clean(number, ' -').upper().strip()


def validate(number):
    """Validate European VAT Number"""
    number = compact(number)
    if number.startswith('EU'):
        if len(number) != 11:
            raise InvalidLength()
    elif number.startswith('IM'):
        if len(number) != 12:
            raise InvalidLength()
    else:
        raise InvalidComponent()
    if not isdigits(number[2:]):
        raise InvalidFormat()
    if number[2:5] not in ISO_3166_1_MEMBER_STATES:
        raise InvalidComponent()
    return number


def is_valid(number):
    """Check if the number is a valid VAT number. This performs the
    country-specific check for the number."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False
