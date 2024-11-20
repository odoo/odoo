# iban.py - functions for handling Belgian IBANs
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

"""Belgian IBAN (International Bank Account Number).

The IBAN is used to identify bank accounts across national borders. The
Belgian IBAN is built up of the IBAN prefix (BE) and check digits, followed
by a 3 digit bank identifier, a 7 digit account number and 2 more check
digits.

* https://www.nbb.be/en/payment-systems/payment-standards/bank-identification-codes

>>> validate('BE32 123-4567890-02')
'BE32123456789002'
>>> validate('BE41091811735141')  # incorrect national check digits
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> validate('BE83138811735115')  # unknown bank code
Traceback (most recent call last):
    ...
InvalidComponent: ...
>>> validate('GR1601101050000010547023795')  # not a Belgian IBAN
Traceback (most recent call last):
    ...
InvalidComponent: ...
>>> to_bic('BE 48 3200 7018 4927')
'BBRUBEBB'
>>> to_bic('BE83138811735115') is None
True
"""

from stdnum import iban
from stdnum.exceptions import *


__all__ = ['compact', 'format', 'validate', 'is_valid']


compact = iban.compact
format = iban.format


def _calc_check_digits(number):
    """Calculate the check digits over the provided part of the number."""
    check = int(number) % 97
    return '%02d' % (check or 97)


def info(number):
    """Return a dictionary of data about the supplied number. This typically
    returns the name of the bank and a BIC if it is valid."""
    number = compact(number)
    from stdnum import numdb
    return numdb.get('be/banks').info(number[4:7])[0][1]


def to_bic(number):
    """Return the BIC for the bank that this number refers to."""
    bic = info(number).get('bic')
    if bic:
        return str(bic)


def validate(number):
    """Check if the number provided is a valid Belgian IBAN."""
    number = iban.validate(number, check_country=False)
    if not number.startswith('BE'):
        raise InvalidComponent()
    if number[-2:] != _calc_check_digits(number[4:-2]):
        raise InvalidChecksum()
    if not info(number):
        raise InvalidComponent()
    return number


def is_valid(number):
    """Check if the number provided is a valid Belgian IBAN."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False
