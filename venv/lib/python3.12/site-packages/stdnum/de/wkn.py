# wkn.py - functions for handling Wertpapierkennnummer
# coding: utf-8
#
# Copyright (C) 2015 Arthur de Jong
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

"""Wertpapierkennnummer (German securities identification code).

The WKN, WPKN, WPK (Wertpapierkennnummer) is a German code to identify
securities. It is a 6-digit alphanumeric number without a check digit that no
longer has any structure. It is expected to be replaced by the ISIN.

>>> validate('A0MNRK')
'A0MNRK'
>>> validate('AOMNRK')  # no capital o allowed
Traceback (most recent call last):
    ...
InvalidFormat: ...
>>> to_isin('SKWM02')
'DE000SKWM021'
"""

from stdnum.exceptions import *
from stdnum.util import clean


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, ' ').strip().upper()


# O and I are not valid but are accounted for in the check digit calculation
_alphabet = '0123456789ABCDEFGH JKLMN PQRSTUVWXYZ'


def validate(number):
    """Check if the number provided is valid. This checks the length and
    check digit."""
    number = compact(number)
    if not all(x in _alphabet for x in number):
        raise InvalidFormat()
    if len(number) != 6:
        raise InvalidLength()
    return number


def is_valid(number):
    """Check if the number provided is valid. This checks the length and
    check digit."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def to_isin(number):
    """Convert the number to an ISIN."""
    from stdnum import isin
    return isin.from_natid('DE', number)
