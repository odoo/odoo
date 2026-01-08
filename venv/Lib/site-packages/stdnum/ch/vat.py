# vat.py - functions for handling Swiss VAT numbers
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

"""VAT, MWST, TVA, IVA, TPV (Mehrwertsteuernummer, the Swiss VAT number).

The Swiss VAT number is based on the UID but is followed by either "MWST"
(Mehrwertsteuer, the German abbreviation for VAT), "TVA" (Taxe sur la valeur
ajoutée in French), "IVA" (Imposta sul valore aggiunto in Italian) or "TPV"
(Taglia sin la plivalur in Romanian).

This module only supports the "new" format that was introduced in 2011 which
completely replaced the "old" 6-digit format in 2014.

More information:

* https://www.ch.ch/en/value-added-tax-number-und-business-identification-number/
* https://www.uid.admin.ch/

>>> validate('CHE-107.787.577 IVA')
'CHE107787577IVA'
>>> validate('CHE-107.787.578 IVA')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> format('CHE107787577IVA')
'CHE-107.787.577 IVA'
"""

from stdnum.ch import uid
from stdnum.exceptions import *


def compact(number):
    """Convert the number to the minimal representation. This strips
    surrounding whitespace and separators."""
    return uid.compact(number)


def validate(number):
    """Check if the number is a valid VAT number. This checks the length,
    formatting and check digit."""
    number = compact(number)
    if len(number) not in (15, 16):
        raise InvalidLength()
    uid.validate(number[:12])
    if number[12:] not in ('MWST', 'TVA', 'IVA', 'TPV'):
        raise InvalidComponent()
    return number


def is_valid(number):
    """Check if the number is a valid VAT number."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    number = compact(number)
    return uid.format(number[:12]) + ' ' + number[12:]
