# postleitzahl.py - functions for handling Austrian postal codes
#
# Copyright (C) 2018 Arthur de Jong
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

"""Postleitzahl (Austrian postal code).

The Austrian postal code consists of four digits that identifies a post
office in Austria.

More information:

* https://en.wikipedia.org/wiki/Postal_codes_in_Austria
* https://www.post.at/suche/standortsuche.php/index/selectedsearch/plz

>>> validate('5090')
'5090'
>>> import json
>>> print(json.dumps(info('5090'), indent=2, sort_keys=True))
{
  "location": "Lofer",
  "region": "Salzburg"
}
>>> validate('4231')  # not-existing postal code
Traceback (most recent call last):
    ...
InvalidComponent: ...
>>> validate('ABCD')
Traceback (most recent call last):
    ...
InvalidFormat: ...
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number).strip()


def info(number):
    """Return a dictionary of data about the supplied number. This typically
    returns the location."""
    number = compact(number)
    from stdnum import numdb
    return numdb.get('at/postleitzahl').info(number)[0][1]


def validate(number):
    """Check if the number is a valid postal code."""
    number = compact(number)
    if not isdigits(number):
        raise InvalidFormat()
    if len(number) != 4:
        raise InvalidLength()
    if not info(number):
        raise InvalidComponent()
    return number


def is_valid(number):
    """Check if the number is a valid postal code."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False
