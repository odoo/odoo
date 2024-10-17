# brn.py - functions for handling South Korean BRN
# coding: utf-8
#
# Copyright (C) 2020 Leandro Regueiro
# Copyright (C) 2020 Arthur de Jong
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

"""BRN (사업자 등록 번호, South Korea Business Registration Number).

The Business Registration Number is issued by the district tax office in the
local jurisdiction for tax purposes. The number consists of 10 digits and
contain the tax office number (3 digits), the type of business (2 digits), a
serially assigned value (4 digits) and a single check digit.

More information:

* https://www.oecd.org/tax/automatic-exchange/crs-implementation-and-assistance/tax-identification-numbers/Korea-TIN.pdf

>>> validate('116-82-00276')
'1168200276'
>>> validate('1168200276')
'1168200276'
>>> validate(' 116 - 82 - 00276  ')
'1168200276'
>>> validate('123456789')
Traceback (most recent call last):
    ...
InvalidLength: ...
>>> format('1348672683')
'134-86-72683'
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation.

    This strips the number of any valid separators and removes surrounding
    whitespace.
    """
    return clean(number, ' -').strip()


def validate(number):
    """Check if the number is a valid South Korea BRN number.

    This checks the length and formatting.
    """
    number = compact(number)
    if len(number) != 10:
        raise InvalidLength()
    if not isdigits(number):
        raise InvalidFormat()
    if number[:3] < '101' or number[3:5] == '00' or number[5:-1] == '0000':
        raise InvalidComponent()
    return number


def is_valid(number):
    """Check if the number is a valid South Korea BRN number."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    number = compact(number)
    return '-'.join([number[:3], number[3:5], number[5:]])


def check_ftc(number, timeout=30):  # pragma: no cover
    """Check the number against the Korea Fair Trade Commission website."""
    import lxml.html
    import requests
    number = compact(number)
    url = 'https://www.ftc.go.kr/bizCommPop.do'
    document = lxml.html.fromstring(
        requests.get(url, params={'wrkr_no': number}, timeout=timeout).text)
    data = dict(zip(
        [(x.text or '').strip() for x in document.findall('.//th')],
        [(x.text or '').strip() for x in document.findall('.//td')]))
    return data or None
