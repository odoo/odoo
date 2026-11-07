# tin.py - functions for handling Thailand TINs
#
# Copyright (C) 2021 Piruin Panichphol
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

"""TIN (Thailand Taxpayer Identification Number).

The Taxpayer Identification Number is used for tax purposes in the Thailand.
This number consists of 13 digits which the last is a check digit.

Personal income taxpayers use Personal Identification Number (PIN) while
companies use Memorandum of Association (MOA).

>>> validate('1-2345-45678-78-1')
'1234545678781'
>>> validate('0-99-4-000-61772-1')
'0994000617721'
>>> validate('1234545678789')
Traceback (most recent call last):
    ...
InvalidFormat: ...
>>> tin_type('1-2345-45678-78-1')
'pin'
>>> tin_type('0-99-4-000-61772-1')
'moa'
>>> format('3100600445635')
'3-1006-00445-63-5'
>>> format('0993000133978')
'0-99-3-000-13397-8'
"""

from stdnum.exceptions import *
from stdnum.th import moa, pin
from stdnum.util import clean


_tin_modules = (moa, pin)


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, ' -').strip()


def tin_type(number):
    """Return a TIN type which this number is valid."""
    number = compact(number)
    for mod in _tin_modules:
        if mod.is_valid(number):
            return mod.__name__.rsplit('.', 1)[-1]
    # fallback
    return None


def validate(number):
    """Check if the number is a valid TIN. This searches for the proper
    sub-type and validates using that."""
    for mod in _tin_modules:
        try:
            return mod.validate(number)
        except ValidationError:
            pass  # try next module
    # fallback
    raise InvalidFormat()


def is_valid(number):
    """Check whether the number is valid."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    for mod in _tin_modules:
        if mod.is_valid(number):
            return mod.format(number)
    return number
