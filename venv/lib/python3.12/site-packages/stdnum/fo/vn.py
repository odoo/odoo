# vn.py - functions for handling Faroe Islands V-number numbers
# coding: utf-8
#
# Copyright (C) 2022 Leandro Regueiro
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

"""V-number (Vinnutal, Faroe Islands tax number).

In the Faroe Islands the legal persons TIN equals the V number issued by the
Faroese Tax Administration. It is a consecutive number.

More information:

* https://www.taks.fo/fo/borgari/bolkar/at-stovna-virki/
* https://www.oecd.org/tax/automatic-exchange/crs-implementation-and-assistance/tax-identification-numbers/Faroe-islands-TIN.pdf

>>> validate('623857')
'623857'
>>> validate('1234')
Traceback (most recent call last):
    ...
InvalidLength: ...
>>> validate('12345X')
Traceback (most recent call last):
    ...
InvalidFormat: ...
>>> format('602 590')
'602590'
"""  # noqa: E501

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation.

    This strips the number of any valid separators and removes surrounding
    whitespace.
    """
    number = clean(number, ' -.').upper().strip()
    if number.startswith('FO'):
        return number[2:]
    return number


def validate(number):
    """Check if the number is a valid Faroe Islands V-number number.

    This checks the length and formatting.
    """
    number = compact(number)
    if len(number) != 6:
        raise InvalidLength()
    if not isdigits(number):
        raise InvalidFormat()
    return number


def is_valid(number):
    """Check if the number is a valid Faroe Islands V-number number."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    return compact(number)
