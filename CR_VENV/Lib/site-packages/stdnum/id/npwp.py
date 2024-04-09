# npwp.py - functions for handling Indonesian NPWP numbers
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

"""NPWP (Nomor Pokok Wajib Pajak, Indonesian VAT Number).

The Nomor Pokok Wajib Pajak (NPWP) is assigned to organisations and
individuals (families) by the Indonesian Tax Office after registration by the
tax payers.

The number consists of 15 digits of which the first 2 denote the type of
entity, 6 digits to identify the tax payer, a check digit over the first 8
digits followed by 3 digits to identify the local tax office and 3 digits for
branch code.

More information:

* https://www.oecd.org/tax/automatic-exchange/crs-implementation-and-assistance/tax-identification-numbers/Indonesia-TIN.pdf
* https://metacpan.org/pod/Business::ID::NPWP
* https://wiki.scn.sap.com/wiki/display/CRM/Indonesia

>>> validate('01.312.166.0-091.000')
'013121660091000'
>>> validate('016090524017000')
'016090524017000'
>>> validate('123456789')
Traceback (most recent call last):
    ...
InvalidLength: ...
>>> format('013000666091000')
'01.300.066.6-091.000'
"""

from stdnum import luhn
from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation.

    This strips the number of any valid separators and removes
    surrounding whitespace.
    """
    return clean(number, ' -.').strip()


def validate(number):
    """Check if the number is a valid Indonesia NPWP number."""
    number = compact(number)
    if len(number) != 15:
        raise InvalidLength()
    if not isdigits(number):
        raise InvalidFormat()
    luhn.validate(number[:9])
    return number


def is_valid(number):
    """Check if the number is a valid Indonesia NPWP number."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    number = compact(number)
    return '%s.%s.%s.%s-%s.%s' % (
        number[:2], number[2:5], number[5:8], number[8], number[9:12], number[12:])
