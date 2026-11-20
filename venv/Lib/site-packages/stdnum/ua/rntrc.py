# ubn.py - functions for handling Ukrainian RNTRC numbers
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

"""РНОКПП, RNTRC (Individual taxpayer registration number in Ukraine).

The РНОКПП (Реєстраційний номер облікової картки платника податків,
registration number of the taxpayer's registration card) is a unique
identification number that is provided to individuals within Ukraine. The
number consists of 10 digits, the last being a check digit.

More information:

* https://uk.wikipedia.org/wiki/РНОКПП

>>> validate('1759013776')
'1759013776'
>>> validate('1759013770')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> validate('12345')
Traceback (most recent call last):
    ...
InvalidLength: ...
>>> format(' 25 30 41 40 71 ')
'2530414071'
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation."""
    return clean(number, ' ').strip()


def calc_check_digit(number):
    """Calculate the check digit for number."""
    weights = (-1, 5, 7, 9, 4, 6, 10, 5, 7)
    total = sum(w * int(n) for w, n in zip(weights, number))
    return str((total % 11) % 10)


def validate(number):
    """Check if the number is a valid Ukraine RNTRC (РНОКПП) number.

    This checks the length, formatting and check digit.
    """
    number = compact(number)
    if len(number) != 10:
        raise InvalidLength()
    if not isdigits(number):
        raise InvalidFormat()
    if number[-1] != calc_check_digit(number):
        raise InvalidChecksum()
    return number


def is_valid(number):
    """Check if the number is a valid Ukraine RNTRC (РНОКПП) number."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    return compact(number)
