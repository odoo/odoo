# nhs.py - functions for handling United Kingdom NHS numbers
#
# Copyright (C) 2016-2017 Arthur de Jong
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

"""NHS (United Kingdom National Health Service patient identifier).

The NHS number is used by the NHS (National Health Service) and its partners
to uniquely identify patients. The number is used in England, Wales and the
Isle of Man. The number is assigned at birth and consists of 10 digits where
the final digit is a check digit.

More information:

* https://en.wikipedia.org/wiki/NHS_number
* https://www.nhs.uk/using-the-nhs/about-the-nhs/what-is-an-nhs-number/
* https://digital.nhs.uk/article/301/NHS-Number
* https://www.datadictionary.nhs.uk/data_dictionary/attributes/n/nhs/nhs_number_de.asp

>>> validate('943-476-5870')
'9434765870'
>>> validate('9434765871')  # invalid check digit
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> format('9434765870')
'943 476 5870'
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, ' -').strip()


def checksum(number):
    """Calculate the checksum. The checksum is only used for the 9 digits
    of the number and the result can either be 0 or 42."""
    return sum(i * int(n) for i, n in enumerate(reversed(number), 1)) % 11


def validate(number):
    """Check if the number is valid. This checks the length and check
    digit."""
    number = compact(number)
    if not isdigits(number):
        raise InvalidFormat()
    if len(number) != 10:
        raise InvalidLength()
    if checksum(number) != 0:
        raise InvalidChecksum()
    return number


def is_valid(number):
    """Check if the number is valid."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number, separator=' '):
    """Reformat the number to the standard presentation format."""
    number = compact(number)
    return separator.join((number[0:3], number[3:6], number[6:]))
