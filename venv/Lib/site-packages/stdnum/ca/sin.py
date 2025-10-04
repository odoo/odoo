# sin.py - functions for handling Canadian Social Insurance Numbers (SINs)
#
# Copyright (C) 2017 Arthur de Jong
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

"""SIN (Canadian Social Insurance Number).

The Social Insurance Number (SIN) is a 9-digit identifier issued to
individuals for various government programs. SINs that begin with a 9 are
issued to temporary workers who are neither Canadian citizens nor permanent
residents.

More information:

* https://www.canada.ca/en/employment-social-development/services/sin.html
* https://en.wikipedia.org/wiki/Social_Insurance_Number

>>> validate('123-456-782')
'123456782'
>>> validate('999-999-999')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> validate('12345678Z')
Traceback (most recent call last):
    ...
InvalidFormat: ...
>>> format('123456782')
'123-456-782'
"""

from stdnum import luhn
from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, '- ').strip()


def validate(number):
    """Check if the number is a valid SIN. This checks the length, formatting
    and check digit."""
    number = compact(number)
    if len(number) != 9:
        raise InvalidLength()
    if not isdigits(number):
        raise InvalidFormat()
    return luhn.validate(number)


def is_valid(number):
    """Check if the number is a valid SIN."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    number = compact(number)
    return '-'.join((number[0:3], number[3:6], number[6:]))
