# uscc.py - functions for handling Chinese USCC numbers
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

"""USCC (Unified Social Credit Code, 统一社会信用代码, China tax number).

This number consists of 18 digits or uppercase English letters (excluding the
letters I, O, Z, S, V). The number is comprised of several parts:

* Digit 1 represents the registering authority,
* Digit 2 represents the registered entity type,
* Digits 3 through 8 represent the registering region code,
* Digits 9 through 17 represent the organisation code,
* Digit 18 is a check digit (either a number or letter).

The registering authority digit most often is a 9, which represents the State
Administration for Industry and Commerce (SAIC) as the registering authority.

The registered entity type indicates the type of business (or entity). The
most common entity types in China are:

* Wholly Foreign-Owned Enterprises (WFOE): 外商独资企业
* Joint Ventures (JV): 合资
* Representative Office: 代表处
* State-Owned Enterprise (SOE): 国有企业
* Private Enterprise: 民营企业
* Individually-Owned: 个体户

The registering region code, sometimes referred to as the "administrative
division code", is a string of six numbers that indicates where the company
is registered. It roughly follows the organisation of the official Chinese
regions.

The organisation code comes directly from the China Organization Code
certificate, an alternative document to the China Business License. It can
contain letters or digits.

More information:

* https://zh.wikipedia.org/wiki/统一社会信用代码
* https://zh.wikipedia.org/wiki/校验码
* https://www.oecd.org/tax/automatic-exchange/crs-implementation-and-assistance/tax-identification-numbers/China-TIN.pdf

>>> validate('91110000600037341L')
'91110000600037341L'
>>> validate('A1110000600037341L')
Traceback (most recent call last):
    ...
InvalidFormat: ...
>>> validate('12345')
Traceback (most recent call last):
    ...
InvalidLength: ...
>>> format('9 1 110000 600037341L')
'91110000600037341L'
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


_alphabet = '0123456789ABCDEFGHJKLMNPQRTUWXY'


def compact(number):
    """Convert the number to the minimal representation.

    This strips the number of any valid separators and removes surrounding
    whitespace.
    """
    return clean(number, ' -').upper().strip()


def calc_check_digit(number):
    """Calculate the check digit for the number."""
    weights = (1, 3, 9, 27, 19, 26, 16, 17, 20, 29, 25, 13, 8, 24, 10, 30, 28)
    number = compact(number)
    total = sum(_alphabet.index(n) * w for n, w in zip(number, weights))
    return _alphabet[(31 - total) % 31]


def validate(number):
    """Check if the number is a valid USCC.

    This checks the length, formatting and check digit.
    """
    number = compact(number)
    if len(number) != 18:
        raise InvalidLength()
    if not isdigits(number[:8]):
        raise InvalidFormat()
    if any(c not in _alphabet for c in number[8:]):
        raise InvalidFormat()
    if number[-1] != calc_check_digit(number):
        raise InvalidChecksum()
    return number


def is_valid(number):
    """Check if the number is a valid USCC."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    return compact(number)
