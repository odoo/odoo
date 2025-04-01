# pan.py - functions for handling Indian Permanent Account number (PAN)
#
# Copyright (C) 2017 Srikanth Lakshmanan
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
Indian individuals, families and corporates for income tax purposes.

The number is built up of 5 characters, 4 numbers and 1 character. The fourth
character indicates the type of holder of the number and the last character
is computed by an undocumented checksum algorithm.

More information:

* https://en.wikipedia.org/wiki/Permanent_account_number

>>> validate('ACUPA7085R')
'ACUPA7085R'
>>> validate('234123412347')
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
>>> mask('AAPPV8261K')
'AAPPVXXXXK'
>>> info('AAPPV8261K')['card_holder_type']
'Individual'
"""

import re

from stdnum.exceptions import *
from stdnum.util import clean


_pan_re = re.compile(r'^[A-Z]{5}[0-9]{4}[A-Z]$')


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, ' -').upper().strip()


def validate(number):
    """Check if the number provided is a valid PAN. This checks the
    length and formatting."""
    number = compact(number)
    if len(number) != 10:
        raise InvalidLength()
    if not _pan_re.match(number):
        raise InvalidFormat()
    info(number)  # used to check 4th digit
    return number


def is_valid(number):
    """Check if the number provided is a valid PAN. This checks the
    length and formatting."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


_card_holder_types = {
    'A': 'Association of Persons (AOP)',
    'B': 'Body of Individuals (BOI)',
    'C': 'Company',
    'F': 'Firm',
    'G': 'Government',
    'H': 'HUF (Hindu Undivided Family)',
    'L': 'Local Authority',
    'J': 'Artificial Juridical Person',
    'P': 'Individual',
    'T': 'Trust (AOP)',
    'K': 'Krish (Trust Krish)',
}


def info(number):
    """Provide information that can be decoded from the PAN."""
    number = compact(number)
    card_holder_type = _card_holder_types.get(number[3])
    if not card_holder_type:
        raise InvalidComponent()
    return {
        'card_holder_type': card_holder_type,
        'initial': number[4],
    }


def mask(number):
    """Mask the PAN as per CBDT masking standard."""
    number = compact(number)
    return number[:5] + 'XXXX' + number[-1:]
