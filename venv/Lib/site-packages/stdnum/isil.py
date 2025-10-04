# isil.py - functions for handling identifiers for libraries and related
#           organizations
#
# Copyright (C) 2011-2017 Arthur de Jong
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

"""ISIL (International Standard Identifier for Libraries).

The ISIL is the International Standard Identifier for Libraries and Related
Organizations (ISO 15511) used to uniquely identify libraries, archives,
museums, and similar organisations.

The identifier can be up to 15 characters that may use digits,
letters (case insensitive) hyphens, colons and slashes. The non-alphanumeric
characters are part of the identifier and are not just for readability.

The identifier consists of two parts separated by a hyphen. The first part is
either a two-letter ISO 3166 country code or a (not two-letter) non-national
prefix that identifies the agency that issued the ISIL. The second part is
the is the identifier issued by that agency.

Only the first part can be validated since it is registered globally. There
may be some validation possible with the second parts (some agencies provide
web services for validation) but there is no common format to these services.

More information:

* https://en.wikipedia.org/wiki/ISBT_128
* https://biblstandard.dk/isil/
* https://www.iso.org/standard/57332.html

>>> validate('IT-RM0267')
'IT-RM0267'
>>> validate('OCLC-DLC')
'OCLC-DLC'
>>> validate('WW-RM0267')  # unregistered country code
Traceback (most recent call last):
    ...
InvalidComponent: ...
>>> format('it-RM0267')
'IT-RM0267'
"""

from stdnum.exceptions import *
from stdnum.util import clean


# the valid characters in an ISIL
_alphabet = set(
    '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-:/')


def compact(number):
    """Convert the ISIL to the minimal representation. This strips
    surrounding whitespace."""
    return clean(number, '').strip()


def _is_known_agency(agency):
    """Check whether the specified agency is valid."""
    # look it up in the db
    from stdnum import numdb
    results = numdb.get('isil').info(agency.upper() + '$')
    # there should be only one part and it should have properties
    return len(results) == 1 and bool(results[0][1])


def validate(number):
    """Check if the number provided is a valid ISIL."""
    number = compact(number)
    if not all(x in _alphabet for x in number):
        raise InvalidFormat()
    if len(number) > 15:
        raise InvalidLength()
    if not _is_known_agency(number.split('-')[0]):
        raise InvalidComponent()
    return number


def is_valid(number):
    """Check if the number provided is a valid ISIL."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    number = compact(number)
    parts = number.split('-')
    if len(parts) > 1 and _is_known_agency(parts[0]):
        parts[0] = parts[0].upper()
    return '-'.join(parts)
