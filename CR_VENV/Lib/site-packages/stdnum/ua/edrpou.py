# ubn.py - functions for handling Ukrainian EDRPOU numbers
# coding: utf-8
#
# Copyright (C) 2020 Leandro Regueiro
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

"""ЄДРПОУ, EDRPOU (Identifier for enterprises and organizations in Ukraine).

The ЄДРПОУ (Єдиного державного реєстру підприємств та організацій України,
Unified State Register of Enterprises and Organizations of Ukraine) is a
unique identification number of a legal entities in Ukraine. Th number
consists of 8 digits, the last being a check digit.

More information:

* https://uk.wikipedia.org/wiki/Код_ЄДРПОУ
* https://1cinfo.com.ua/Articles/Proverka_koda_po_EDRPOU.aspx

>>> validate('32855961')
'32855961'
>>> validate('32855968')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> validate('12345')
Traceback (most recent call last):
    ...
InvalidLength: ...
>>> format(' 32855961 ')
'32855961'
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation."""
    return clean(number, ' ').strip()


def calc_check_digit(number):
    """Calculate the check digit for number."""
    weights = (1, 2, 3, 4, 5, 6, 7)
    if number[0] in '345':
        weights = (7, 1, 2, 3, 4, 5, 6)
    total = sum(w * int(n) for w, n in zip(weights, number))
    if total % 11 < 10:
        return str(total % 11)
    # Calculate again with other weights
    weights = tuple(w + 2 for w in weights)
    total = sum(w * int(n) for w, n in zip(weights, number))
    return str(total % 11)


def validate(number):
    """Check if the number is a valid Ukraine EDRPOU (ЄДРПОУ) number.

    This checks the length, formatting and check digit.
    """
    number = compact(number)
    if len(number) != 8:
        raise InvalidLength()
    if not isdigits(number):
        raise InvalidFormat()
    if number[-1] != calc_check_digit(number):
        raise InvalidChecksum()
    return number


def is_valid(number):
    """Check if the number is a valid Ukraine EDRPOU (ЄДРПОУ) number."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    return compact(number)
