# iso11649.py - functions for performing the ISO 11649 checksum validation
#               for structured creditor reference numbers
#
# Copyright (C) 2018 Esben Toke Christensen
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

"""ISO 11649 (Structured Creditor Reference).

The ISO 11649 structured creditor number consists of 'RF' followed by two
check digits and up to 21 digits. The number may contain letters.

The reference number is validated by moving RF and the check digits to the
end of the number, and checking that the ISO 7064 Mod 97, 10 checksum of this
string is 1.

More information:

* https://en.wikipedia.org/wiki/Creditor_Reference

>>> validate('RF18 5390 0754 7034')
'RF18539007547034'
>>> validate('RF18 5390 0754 70Y')
'RF185390075470Y'
>>> is_valid('RF18 5390 0754 7034')
True
>>> validate('RF17 5390 0754 7034')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> format('RF18539007547034')
'RF18 5390 0754 7034'
"""

from stdnum.exceptions import *
from stdnum.iso7064 import mod_97_10
from stdnum.util import clean


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any invalid separators and removes surrounding whitespace."""
    return clean(number, ' -.,/:').upper().strip()


def validate(number):
    """Check if the number provided is a valid ISO 11649 structured creditor
    reference number."""
    number = compact(number)
    if len(number) < 5 or len(number) > 25:
        raise InvalidLength()
    if not number.startswith('RF'):
        raise InvalidFormat()
    mod_97_10.validate(number[4:] + number[:4])
    return number


def is_valid(number):
    """Check if the number provided is a valid ISO 11649 structured creditor
    number. This checks the length, formatting and check digits."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Format the number provided for output.

    Blocks of 4 characters, the last block can be less than 4 characters. See
    https://www.paymentstandards.ch/dam/downloads/ig-qr-bill-en.pdf chapter
    3.6.2.
    """
    number = compact(number)
    return ' '.join(number[i:i + 4] for i in range(0, len(number), 4))
