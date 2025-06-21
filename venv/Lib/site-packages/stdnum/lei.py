# lei.py - functions for handling Legal Entity Identifiers (LEIs)
# coding: utf-8
#
# Copyright (C) 2017 Arthur de Jong
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

"""LEI (Legal Entity Identifier).

The Legal Entity Identifier (LEI) is used to identify legal entities for use
in financial transactions. A LEI is a 20-character alphanumeric string that
consists of a 4-character issuing LOU (Local Operating Unit), 2 digits that
are often 0, 13 digits to identify the organisation and 2 check digits.

More information:

* https://en.wikipedia.org/wiki/Legal_Entity_Identifier
* http://www.lei-lookup.com/
* https://www.gleif.org/
* http://openleis.com/

>>> validate('213800KUD8LAJWSQ9D15')
'213800KUD8LAJWSQ9D15'
>>> validate('213800KUD8LXJWSQ9D15')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
"""

from stdnum.exceptions import *
from stdnum.iso7064 import mod_97_10
from stdnum.util import clean


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding white space."""
    return clean(number, ' -').strip().upper()


def validate(number):
    """Check if the number is valid. This checks the length, format and check
    digits."""
    number = compact(number)
    mod_97_10.validate(number)
    return number


def is_valid(number):
    """Check if the number is valid."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False
