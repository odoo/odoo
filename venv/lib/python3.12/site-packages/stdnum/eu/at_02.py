# at_02.py - functions for handling AT-02 (SEPA Creditor identifier)
#
# Copyright (C) 2014-2016 Sergi Almacellas Abellana
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

"""SEPA Identifier of the Creditor (AT-02).

This identifier is indicated in the ISO 20022 data element `Creditor Scheme
Identification`. The creditor can be a legal entity, or an association that
is not a legal entity, or a person.

The first two digits contain the ISO country code, the next two are check
digits for the ISO 7064 Mod 97, 10 checksum, the next tree contain the
Creditor Business Code (or `ZZZ` if no business code used) and the remainder
contains the country-specific identifier.

>>> validate('ES 23 ZZZ 47690558N')
'ES23ZZZ47690558N'
>>> validate('ES2300047690558N')
'ES2300047690558N'
>>> compact('ES++()+23ZZZ4//7690558N')
'ES23ZZZ47690558N'
>>> calc_check_digits('ESXXZZZ47690558N')
'23'
"""

from stdnum.exceptions import *
from stdnum.iso7064 import mod_97_10
from stdnum.util import clean


# the valid characters we have
_alphabet = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'


def compact(number):
    """Convert the AT-02 number to the minimal representation. This strips
    the number of any valid separators and removes invalid characters."""
    return clean(number, ' -/?:().m\'+"').strip().upper()


def _to_base10(number):
    """Prepare the number to its base10 representation so it can be checked
    with the ISO 7064 Mod 97, 10 algorithm. That means excluding positions 5
    to 7 and moving the first four digits to the end."""
    return ''.join(str(_alphabet.index(x)) for x in number[7:] + number[:4])


def validate(number):
    """Check if the number provided is a valid AT-02."""
    number = compact(number)
    try:
        test_number = _to_base10(number)
    except Exception:  # noqa: B902
        raise InvalidFormat()
    # ensure that checksum is valid
    mod_97_10.validate(test_number)
    return number


def is_valid(number):
    """Check if the number provided is a valid AT-02."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def calc_check_digits(number):
    """Calculate the check digits that should be put in the number to make it
    valid. Check digits in the supplied number are ignored."""
    number = compact(number)
    # replace check digits with placeholders
    number = ''.join((number[:2], '00', number[4:]))
    return mod_97_10.calc_check_digits(_to_base10(number)[:-2])
