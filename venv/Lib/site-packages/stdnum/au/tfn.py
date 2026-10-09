# tfn.py - functions for handling Australian Tax File Numbers (TFNs)
#
# Copyright (C) 2016 Vincent Bastos
# Copyright (C) 2016 Arthur de Jong
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

"""TFN (Australian Tax File Number).

The Tax File Number (TFN) is issued by the Australian Taxation Office (ATO)
to taxpaying individuals and organisations. A business has both a TFN and an
Australian Business Number (ABN).

The number consists of 8 (older numbers) or 9 digits and includes a check
digit but otherwise without structure.

More information:

* https://en.wikipedia.org/wiki/Tax_file_number
* https://www.ato.gov.au/Individuals/Tax-file-number/

>>> validate('123 456 782')
'123456782'
>>> validate('999 999 999')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> format('123456782')
'123 456 782'
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, ' ').strip()


def checksum(number):
    """Calculate the checksum."""
    weights = (1, 4, 3, 7, 5, 8, 6, 9, 10)
    return sum(w * int(n) for w, n in zip(weights, number)) % 11


def validate(number):
    """Check if the number is a valid TFN. This checks the length, formatting
    and check digit."""
    number = compact(number)
    if not isdigits(number):
        raise InvalidFormat()
    if len(number) not in (8, 9):
        raise InvalidLength()
    if checksum(number) != 0:
        raise InvalidChecksum()
    return number


def is_valid(number):
    """Check if the number is a valid TFN."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    number = compact(number)
    return ' '.join((number[0:3], number[3:6], number[6:]))
