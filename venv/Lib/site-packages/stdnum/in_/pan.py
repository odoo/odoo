# pan.py - functions for handling Indian income tax numbers
#
# Copyright (C) 2017 Srikanth Lakshmanan
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

"""PAN (Permanent Account Number, Indian income tax identifier).

The Permanent Account Number (PAN) is a 10 digit alphanumeric identifier for
Indian individuals, families and corporates for income tax purposes. It is
also issued to foreign nationals subject to a valid visa.

PAN is made up of 5 letters, 4 digits and 1 alphabetic check digit. The 4th
character indicates the type of holder, the 5th character is either 1st
letter of the holder's name or holder's surname in case of 'Individual' PAN,
next 4 digits are serial numbers running from 0001 to 9999 and the last
character is a check digit computed by an undocumented checksum algorithm.

More information:

* https://en.wikipedia.org/wiki/Permanent_account_number
* https://incometaxindia.gov.in/tutorials/1.permanent%20account%20number%20(pan).pdf

>>> validate('ACUPA7085R')
'ACUPA7085R'
>>> validate('ACUPA7085RR')
Traceback (most recent call last):
    ...
InvalidLength: ...
>>> validate('ABMPA32111')  # check digit should be a letter
Traceback (most recent call last):
    ...
InvalidFormat: ...
>>> validate('ABMXA3211G')  # invalid type of holder
Traceback (most recent call last):
    ...
InvalidComponent: ...
>>> validate('ACUPA0000R')  # serial number should not be '0000'
Traceback (most recent call last):
    ...
InvalidComponent: ...
>>> mask('AAPPV8261K')
'AAPPVXXXXK'
>>> info('AAPPV8261K')['holder_type']
'Individual'
"""

import re

from stdnum.exceptions import *
from stdnum.util import clean


_pan_re = re.compile(r'^[A-Z]{5}[0-9]{4}[A-Z]$')

_pan_holder_types = {
    'A': 'Association of Persons (AOP)',
    'B': 'Body of Individuals (BOI)',
    'C': 'Company',
    'F': 'Firm/Limited Liability Partnership',
    'G': 'Government Agency',
    'H': 'Hindu Undivided Family (HUF)',
    'L': 'Local Authority',
    'J': 'Artificial Juridical Person',
    'P': 'Individual',
    'T': 'Trust',
    'K': 'Krish (Trust Krish)',
}
# Type 'K' may have been discontinued, not listed on Income Text Dept website.


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, ' -').upper().strip()


def validate(number):
    """Check if the number provided is a valid PAN. This checks the length
    and formatting."""
    number = compact(number)
    if len(number) != 10:
        raise InvalidLength()
    if not _pan_re.match(number):
        raise InvalidFormat()
    info(number)  # used to check 4th digit
    if number[5:9] == '0000':
        raise InvalidComponent()
    return number


def is_valid(number):
    """Check if the number provided is a valid PAN. This checks the length
    and formatting."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def info(number):
    """Provide information that can be decoded from the PAN."""
    number = compact(number)
    holder_type = _pan_holder_types.get(number[3])
    if not holder_type:
        raise InvalidComponent()
    return {
        'holder_type': holder_type,
        'card_holder_type': holder_type,  # for backwards compatibility
        'initial': number[4],
    }


def mask(number):
    """Mask the PAN as per Central Board of Direct Taxes (CBDT) masking
    standard."""
    number = compact(number)
    return number[:5] + 'XXXX' + number[-1:]
