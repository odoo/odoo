# iso6346.py - functions for handling ISO 6346
#
# Copyright (C) 2014 Openlabs Technologies & Consulting (P) Limited
# Copyright (C) 2014-2017 Arthur de Jong
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

"""ISO 6346 (International standard for container identification)

ISO 6346 is an international standard covering the coding, identification and
marking of intermodal (shipping) containers used within containerized
intermodal freight transport. The standard establishes a visual identification
system for every container that includes a unique serial number (with check
digit), the owner, a country code, a size, type and equipment category as well
as any operational marks. The standard is managed by the International
Container Bureau (BIC).

More information:

* https://en.wikipedia.org/wiki/ISO_6346

>>> validate('csqu3054383')
'CSQU3054383'
>>> validate('CSQU3054384')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> format('tasu117 000 0')
'TASU 117000 0'
"""

import re

from stdnum.exceptions import *
from stdnum.util import clean


_iso6346_re = re.compile(r'^\w{3}(U|J|Z|R)\d{7}$')


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, ' ').strip().upper()


def calc_check_digit(number):
    """Calculate check digit and return it for the 10 digit owner code and
    serial number."""
    number = compact(number)
    alphabet = '0123456789A BCDEFGHIJK LMNOPQRSTU VWXYZ'
    return str(sum(
        alphabet.index(n) * pow(2, i)
        for i, n in enumerate(number)) % 11 % 10)


def validate(number):
    """Validate the given number (unicode) for conformity to ISO 6346."""
    number = compact(number)
    if len(number) != 11:
        raise InvalidLength()
    if not _iso6346_re.match(number):
        raise InvalidFormat()
    if calc_check_digit(number[:-1]) != number[-1]:
        raise InvalidChecksum()
    return number


def is_valid(number):
    """Check whether the number conforms to the standard ISO6346. Unlike
    the validate function, this will not raise ValidationError(s)."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    number = compact(number)
    return ' '.join((number[:4], number[4:-1], number[-1:]))
