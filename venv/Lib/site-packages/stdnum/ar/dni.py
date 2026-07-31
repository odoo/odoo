# dni.py - functions for handling Argentinian national identifiers
# coding: utf-8
#
# Copyright (C) 2018 Arthur de Jong
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

"""DNI (Documento Nacional de Identidad, Argentinian national identity nr.).

The DNI number is the number that appears on the Argentinian national
identity document and is used to identify citizen and foreigners residing in
the country.

More information:

* https://en.wikipedia.org/wiki/Documento_Nacional_de_Identidad_(Argentina)

>>> validate('20.123.456')
'20123456'
>>> validate('2012345699')
Traceback (most recent call last):
    ...
InvalidLength: ...
>>> format('20123456')
'20.123.456'
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, ' .').strip()


def validate(number):
    """Check if the number is a valid DNI."""
    number = compact(number)
    if not isdigits(number):
        raise InvalidFormat()
    if len(number) not in (7, 8):
        raise InvalidLength()
    return number


def is_valid(number):
    """Check if the number is a valid DNI."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    number = compact(number)
    return '.'.join((number[:-6], number[-6:-3], number[-3:]))
