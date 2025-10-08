# idnr.py - functions for handling German tax id
# coding: utf-8
#
# Copyright (C) 2017 Holvi Payment Services Oy
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

"""IdNr (Steuerliche Identifikationsnummer, German personal tax number).

The IdNr (or Steuer-IdNr) is a personal identification number that is
assigned to individuals in Germany for tax purposes and is meant to replace
the Steuernummer. The number consists of 11 digits and does not embed any
personal information.

More information:

* https://de.wikipedia.org/wiki/Steuerliche_Identifikationsnummer
* http://www.identifikationsmerkmal.de/

>>> validate('36 574 261 809')
'36574261809'
>>> validate('36574261890')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> validate('36554266806')  # more digits repeated
Traceback (most recent call last):
    ...
InvalidFormat: ...
>>> format('36574261809')
'36 574 261 809'
"""

from collections import defaultdict

from stdnum.exceptions import *
from stdnum.iso7064 import mod_11_10
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, ' -./,').strip()


def validate(number):
    """Check if the number provided is a valid tax identification number.
    This checks the length, formatting and check digit."""
    number = compact(number)
    if len(number) != 11:
        raise InvalidLength()
    if not isdigits(number):
        raise InvalidFormat()
    if number.startswith('0'):
        raise InvalidFormat()
    # In the first 10 digits exactly one digit must be repeated two or
    # three times and other digits can appear only once.
    counter = defaultdict(int)
    for n in number[:10]:
        counter[n] += 1
    counts = [c for c in counter.values() if c > 1]
    if len(counts) != 1 or counts[0] not in (2, 3):
        raise InvalidFormat()
    return mod_11_10.validate(number)


def is_valid(number):
    """Check if the number provided is a valid tax identification number.
    This checks the length, formatting and check digit."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    number = compact(number)
    return ' '.join((number[:2], number[2:5], number[5:8], number[8:]))
