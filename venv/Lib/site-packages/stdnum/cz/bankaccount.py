# bankaccount.py - functions for handling Czech bank account numbers
# coding: utf-8
#
# Copyright (C) 2022 Petr Přikryl
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

"""Czech bank account number.

The Czech bank account numbers consist of up to 20 digits:
    UUUUUK-MMMMMMMMKM/XXXX

The first part is prefix that is up to 6 digits. The following part is from 2 to 10 digits.
Both parts could be filled with zeros from left if missing.
The final 4 digits represent the bank code.

More information:

* https://www.penize.cz/osobni-ucty/424173-tajemstvi-cisla-uctu-klicem-pro-banky-je-11
* https://www.zlatakoruna.info/zpravy/ucty/cislo-uctu-v-cr

>>> validate('34278-0727558021/0100')
'034278-0727558021/0100'
>>> validate('4278-727558021/0100')  # invalid check digits (prefix)
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> validate('34278-727558021/0000')  # invalid bank
Traceback (most recent call last):
    ...
InvalidComponent: ...
>>> format('34278-727558021/0100')
'034278-0727558021/0100'
>>> to_bic('34278-727558021/0100')
'KOMBCZPP'
"""

import re

from stdnum.exceptions import *
from stdnum.util import clean


_bankaccount_re = re.compile(
    r'((?P<prefix>[0-9]{0,6})-)?(?P<root>[0-9]{2,10})\/(?P<bank>[0-9]{4})')


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    number = clean(number).strip()
    match = _bankaccount_re.match(number)
    if match:
        # zero-pad valid numbers
        prefix = (match.group('prefix') or '').zfill(6)
        root = match.group('root').zfill(10)
        number = ''.join((prefix, '-', root, '/', match.group('bank')))
    return number


def _split(number):
    """Split valid numbers into prefix, root and bank parts of the number."""
    match = _bankaccount_re.match(number)
    if not match:
        raise InvalidFormat()
    return match.group('prefix'), match.group('root'), match.group('bank')


def _info(bank):
    """Look up information for the bank."""
    from stdnum import numdb
    info = {}
    for _nr, found in numdb.get('cz/banks').info(bank):
        info.update(found)
    return info


def info(number):
    """Return a dictionary of data about the supplied number. This typically
    returns the name of the bank and branch and a BIC if it is valid."""
    prefix, root, bank = _split(compact(number))
    return _info(bank)


def to_bic(number):
    """Return the BIC for the bank that this number refers to."""
    bic = info(number).get('bic')
    if bic:
        return str(bic)


def _calc_checksum(number):
    weights = (6, 3, 7, 9, 10, 5, 8, 4, 2, 1)
    return sum(w * int(n) for w, n in zip(weights, number.zfill(10))) % 11


def validate(number):
    """Check if the number provided is a valid bank account number."""
    number = compact(number)
    prefix, root, bank = _split(number)
    if _calc_checksum(prefix) != 0:
        raise InvalidChecksum()
    if _calc_checksum(root) != 0:
        raise InvalidChecksum()
    if 'bank' not in _info(bank):
        raise InvalidComponent()
    return number


def is_valid(number):
    """Check if the number provided is a valid bank account number."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    return compact(number)
