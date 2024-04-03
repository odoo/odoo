# gstin.py - functions for handling Indian VAT numbers
#
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

"""GSTIN (Goods and Services Tax identification number, Indian VAT number).

The Goods and Services Tax identification number (GSTIN) is a 15 digit unique
identifier assigned to all business entities in India registered under the
Goods and Services Tax (GST) Act, 2017.

Each GSTIN begins with a 2 digit state code, the next 10 characters are the
holder's PAN, the 13th character is an alphanumeric digit that represents the
number of GSTIN registrations made in a state or union territory for same the
PAN, the 14th character is 'Z' and the last character is an alphanumeric
check digit calculated using Luhn mod 36 algorithm.

More information:

* https://bajajfinserv.in/insights/what-is-goods-and-service-tax-identification-number
* https://ddvat.gov.in/docs/List%20of%20State%20Code.pdf
* https://en.wikipedia.org/wiki/Goods_and_Services_Tax_(India)

>>> validate('27AAPFU0939F1ZV')
'27AAPFU0939F1ZV'
>>> validate('27AAPFU0939F1Z')
Traceback (most recent call last):
    ...
InvalidLength: ...
>>> validate('369296450896540')
Traceback (most recent call last):
    ...
InvalidFormat: ...
>>> validate('27AAPFU0939F1AA')
Traceback (most recent call last):
    ...
InvalidComponent: ...
>>> validate('27AAPFU0939F1ZO')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> to_pan('27AAPFU0939F1ZV')
'AAPFU0939F'
>>> info('27AAPFU0939F1ZV')['state']
'Maharashtra'
"""

import re

from stdnum import luhn
from stdnum.exceptions import *
from stdnum.in_ import pan
from stdnum.util import clean


_GSTIN_RE = re.compile(r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9A-Z]{3}$')

_ALPHABET = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'

_STATE_CODES = {
    '01': 'Jammu and Kashmir',
    '02': 'Himachal Pradesh',
    '03': 'Punjab',
    '04': 'Chandigarh',
    '05': 'Uttarakhand',
    '06': 'Haryana',
    '07': 'Delhi',
    '08': 'Rajasthan',
    '09': 'Uttar Pradesh',
    '10': 'Bihar',
    '11': 'Sikkim',
    '12': 'Arunachal Pradesh',
    '13': 'Nagaland',
    '14': 'Manipur',
    '15': 'Mizoram',
    '16': 'Tripura',
    '17': 'Meghalaya',
    '18': 'Assam',
    '19': 'West Bengal',
    '20': 'Jharkhand',
    '21': 'Orissa',
    '22': 'Chattisgarh',
    '23': 'Madhya Pradesh',
    '24': 'Gujarat',
    '25': 'Daman and Diu',
    '26': 'Dadar and Nagar Haveli',
    '27': 'Maharashtra',
    '28': 'Andhra Pradesh',
    '29': 'Karnataka',
    '30': 'Goa',
    '31': 'Lakshadweep',
    '32': 'Kerala',
    '33': 'Tamil Nadu',
    '34': 'Puducherry',
    '35': 'Anadaman and Nicobar Islands',
    '36': 'Telangana',
    '37': 'Andhra Pradesh (New)',
}


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, ' -').upper().strip()


def validate(number):
    """Check if the number provided is a valid GSTIN. This checks the length,
    formatting and check digit."""
    number = compact(number)
    if len(number) != 15:
        raise InvalidLength()
    if not _GSTIN_RE.match(number):
        raise InvalidFormat()
    if number[:2] not in _STATE_CODES or number[12] == '0' or number[13] != 'Z':
        raise InvalidComponent()
    pan.validate(number[2:12])
    luhn.validate(number, _ALPHABET)
    return number


def is_valid(number):
    """Check if the number provided is a valid GSTIN. This checks the length,
    formatting and check digit."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def to_pan(number):
    """Convert the number to a PAN."""
    number = compact(number)
    return number[2:12]


def info(number):
    """Provide information that can be decoded locally from GSTIN (without
    API)."""
    number = validate(number)
    return {
        'state': _STATE_CODES.get(number[:2]),
        'pan': number[2:12],
        'holder_type': pan.info(number[2:12])['holder_type'],
        'initial': number[6],
        'registration_count': _ALPHABET.index(number[12]),
    }
