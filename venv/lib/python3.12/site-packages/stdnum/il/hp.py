# hp.py - functions for handling Israeli company numbers
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

"""Company Number (מספר חברה, or short ח.פ. Israeli company number).

It consists of nine digits and includes a check digit. For companies
the first digit is a 5. The first two digits identify the type of
company.

More information:

* https://he.wikipedia.org/wiki/תאגיד#מספר_רישום_התאגיד
* https://www.oecd.org/tax/automatic-exchange/crs-implementation-and-assistance/tax-identification-numbers/Israel-TIN.pdf
* https://wiki.scn.sap.com/wiki/display/CRM/Israel

>>> validate('516179157')
'516179157'
>>> format(' 5161 79157 ')
'516179157'
>>> validate('516179150')  # invalid check digit
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> validate('490154203237518')  # longer than 9 digits
Traceback (most recent call last):
    ...
InvalidLength: ...
>>> validate('416179157')
Traceback (most recent call last):
    ...
InvalidComponent: ...
"""  # noqa: E501

from stdnum import luhn
from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any separators and removes surrounding whitespace."""
    return clean(number, ' -').strip()


def validate(number):
    """Check if the number provided is a valid ID. This checks the length,
    formatting and check digit."""
    number = compact(number)
    if len(number) != 9:
        raise InvalidLength()
    if not isdigits(number) or int(number) <= 0:
        raise InvalidFormat()
    if number[0] != '5':
        raise InvalidComponent()
    luhn.validate(number)
    return number


def is_valid(number):
    """Check if the number provided is a valid ID. This checks the length,
    formatting and check digit."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    return compact(number)
