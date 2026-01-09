# tin.py - functions for handling TINs
#
# Copyright (C) 2013 Arthur de Jong
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

"""TIN (U.S. Taxpayer Identification Number).

The Taxpayer Identification Number is used used for tax purposes in the
United States. A TIN may be:

* a Social Security Number (SSN)
* an Individual Taxpayer Identification Number (ITIN)
* an Employer Identification Number (EIN)
* a Preparer Tax Identification Number (PTIN)
* an Adoption Taxpayer Identification Number (ATIN)

>>> compact('123-45-6789')
'123456789'
>>> validate('123-45-6789')
'123456789'
>>> validate('07-3456789')
Traceback (most recent call last):
    ...
InvalidFormat: ...
>>> guess_type('536-90-4399')
['ssn', 'atin']
>>> guess_type('04-2103594')
['ein']
>>> guess_type('042103594')
['ssn', 'ein', 'atin']
>>> format('042103594')
'042-10-3594'
>>> format('123-456')  # invalid numbers are not reformatted
'123-456'
"""

from stdnum.exceptions import *
from stdnum.us import atin, ein, itin, ptin, ssn
from stdnum.util import clean


_tin_modules = (ssn, itin, ein, ptin, atin)


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, '-').strip()


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
    """Check if the number is a valid TIN."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def guess_type(number):
    """Return a list of possible TIN types for which this number is
    valid.."""
    return [mod.__name__.rsplit('.', 1)[-1]
            for mod in _tin_modules
            if mod.is_valid(number)]


def format(number):
    """Reformat the number to the standard presentation format."""
    for mod in _tin_modules:
        if mod.is_valid(number) and hasattr(mod, 'format'):
            return mod.format(number)
    return number
