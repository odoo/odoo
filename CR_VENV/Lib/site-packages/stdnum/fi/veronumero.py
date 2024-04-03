# veronumero.py - functions for handling Finnish individual tax numbers
# coding: utf-8
#
# Copyright (C) 2017 Holvi Payment Services Oy
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

"""
Veronumero (Finnish individual tax number).

The Veronumero an individual tax number that is assigned to workers in the
construction industry in Finland. The number is separate from the HETU and is
a 12 digit number without any embedded information such as birth dates.

More information:

* https://www.vero.fi/en/detailed-guidance/guidance/48791/individual_tax_numbers__instructions_fo/
* https://prosentti.vero.fi/Veronumerorekisteri/Tarkistus/VeronumeronTarkistus.aspx

>>> validate('123456789123')
'123456789123'
>>> validate('12345678912A')
Traceback (most recent call last):
    ...
InvalidFormat: ...
>>> validate('123456789')
Traceback (most recent call last):
    ...
InvalidLength: ...
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the Veronumero to the minimal representation. This strips
    surrounding whitespace and removes separators."""
    return clean(number, ' ').strip()


def validate(number):
    """Check if the number is a valid tax number. This checks the length and
    formatting."""
    number = compact(number)
    if not isdigits(number):
        raise InvalidFormat()
    if len(number) != 12:
        raise InvalidLength()
    # there is no known check digit validation
    return number


def is_valid(number):
    """Check if the number is a valid tax number."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False
