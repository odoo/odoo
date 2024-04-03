# bankaccount.py - functions for handling New Zealand bank account numbers
# coding: utf-8
#
# Copyright (C) 2019 Arthur de Jong
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

"""New Zealand bank account number

The New Zealand bank account numbers consist of 16 digits. The first two
represent the bank, followed by four for the branch, seven digits for the
account base number and three for the account type.

More information:

* https://en.wikipedia.org/wiki/New_Zealand_bank_account_number

>>> validate('01-0242-0100194-00')
'0102420100194000'
>>> validate('01-0242-0100195-00')  # invalid check digits
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> validate('01-9999-0100197-00')  # invalid branch
Traceback (most recent call last):
    ...
InvalidComponent: ...
>>> format('0102420100194000')
'01-0242-0100194-000'
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


# The following algorithms and weights were taken from:
# https://www.ird.govt.nz/software-providers/explore-products-contents/reporting/withholding-taxes/rwt-and-nrwt-certificate-filing-options.html#02
# with the modification to use max 7 digits for the account base
# instead of 8 (and leaving out algorithm C).

# The algorithm to choose based on the bank
_algorithms = {
    '01': 'A', '02': 'A', '03': 'A', '04': 'A', '06': 'A', '08': 'D',
    '09': 'E', '10': 'A', '11': 'A', '12': 'A', '13': 'A', '14': 'A',
    '15': 'A', '16': 'A', '17': 'A', '18': 'A', '19': 'A', '20': 'A',
    '21': 'A', '22': 'A', '23': 'A', '24': 'A', '25': 'F', '26': 'G',
    '27': 'A', '28': 'G', '29': 'G', '30': 'A', '31': 'X', '33': 'F',
    '35': 'A', '38': 'A',
}

# The different weights for the different checksum algorithms
_weights = {
    'A': (0, 0, 6, 3, 7, 9, 0, 10, 5, 8, 4, 2, 1, 0, 0, 0),
    'B': (0, 0, 0, 0, 0, 0, 0, 10, 5, 8, 4, 2, 1, 0, 0, 0),
    'D': (0, 0, 0, 0, 0, 0, 7, 6, 5, 4, 3, 2, 1, 0, 0, 0),
    'E': (0, 0, 0, 0, 0, 0, 0, 0, 0, 5, 4, 3, 2, 0, 0, 1),
    'F': (0, 0, 0, 0, 0, 0, 1, 7, 3, 1, 7, 3, 1, 0, 0, 0),
    'G': (0, 0, 0, 0, 0, 0, 1, 3, 7, 1, 3, 7, 1, 3, 7, 1),
    'X': (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
}

# The moduli to use per algorithm
_moduli = {
    'A': (11, 11),
    'B': (11, 11),
    'D': (11, 11),
    'E': (9, 11),
    'F': (10, 10),
    'G': (9, 10),
    'X': (1, 1),
}


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    number = clean(number).strip().replace(' ', '-').split('-')
    if len(number) == 4:
        # zero pad the different sections if they are found
        lengths = (2, 4, 7, 3)
        return ''.join(n.zfill(l) for n, l in zip(number, lengths))
    else:
        # otherwise zero pad the account type
        number = ''.join(number)
        return number[:13] + number[13:].zfill(3)


def info(number):
    """Return a dictionary of data about the supplied number. This typically
    returns the name of the bank and branch and a BIC if it is valid."""
    number = compact(number)
    from stdnum import numdb
    info = {}
    for nr, found in numdb.get('nz/banks').info(number):
        info.update(found)
    return info


def _calc_checksum(number):
    # pick the algorithm and parameters
    algorithm = _algorithms.get(number[:2], 'X')
    if algorithm == 'A' and number[6:13] >= '0990000':
        algorithm = 'B'
    weights = _weights[algorithm]
    mod1, mod2 = _moduli[algorithm]
    # calculate the checksum
    return sum(
        c % mod1 if c > mod1 else c for c in
        (w * int(n) for w, n in zip(weights, number))) % mod2


def validate(number):
    """Check if the number provided is a valid bank account number."""
    number = compact(number)
    if not isdigits(number):
        raise InvalidFormat()
    if len(number) != 16:
        raise InvalidLength()
    if _calc_checksum(number) != 0:
        raise InvalidChecksum()
    i = info(number)
    if 'bank' not in i or 'branch' not in i:
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
    number = compact(number)
    return '-'.join([
        number[:2],
        number[2:6],
        number[6:13],
        number[13:]])
