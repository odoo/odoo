# cfi.py - functions for handling ISIN numbers
#
# Copyright (C) 2022 Arthur de Jong
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

"""CFI (ISO 10962 Classification of Financial Instruments).

The CFI is a 6-character code used to classify financial instruments. It is
issued alongside an ISIN and describes category such as equity or future and
category-specific properties such as underlying asset type or payment status.

More information:

* https://en.wikipedia.org/wiki/ISO_10962
* https://www.iso.org/standard/73564.html
* https://www.six-group.com/en/products-services/financial-information/data-standards.html

>>> validate('ELNUFR')
'ELNUFR'
>>> validate('ELNUFQ')
Traceback (most recent call last):
    ...
InvalidComponent: ...
>>> import json
>>> print(json.dumps(info('ELNUFR'), indent=2, sort_keys=True))
{
  "Form": "Registered",
  "Ownership/transfer/sales restrictions": "Free",
  "Payment status": "Fully paid",
  "Voting right": "Non-voting",
  "category": "Equities",
  "group": "Limited partnership units"
}
"""

from stdnum import numdb
from stdnum.exceptions import *
from stdnum.util import clean


# our open copy of the CFI database
_cfidb = numdb.get('cfi')


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, ' -').strip().upper()


def info(number):
    """Look up information about the number."""
    number = compact(number)
    info = _cfidb.info(number)
    if len(info) != 6:
        raise InvalidComponent()
    properties = {}
    properties.update(info[0][1])
    properties.update(info[1][1])
    for nr, found in info[2:]:
        if nr != 'X' and 'v' not in found:
            raise InvalidComponent()
        if 'v' in found:
            properties[found['a']] = found['v']
    return properties


def validate(number):
    """Check if the number provided is valid. This checks the length and
    format."""
    number = compact(number)
    if not all(x in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' for x in number):
        raise InvalidFormat()
    if len(number) != 6:
        raise InvalidLength()
    info(number)
    return number


def is_valid(number):
    """Check if the number provided is valid. This checks the length and
    check digit."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False
