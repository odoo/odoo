# tin.py - functions for handling Austrian tax identification numbers
# coding: utf-8
#
# Copyright (C) 2017 Holvi Payment Services Oy
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

r"""Abgabenkontonummer (Austrian tax identification number).

The Austrian tax identification number (Abgabenkontonummer) consists of 2
digits for the issuing tax office (Finanzamtsnummer) and 7 digits for the
subject and a check digit (Steuernummer).

More information:

* https://de.wikipedia.org/wiki/Abgabenkontonummer
* https://service.bmf.gv.at/Service/Anwend/Behoerden/show_mast.asp

>>> validate('59-119/9013')
'591199013'
>>> validate('59-119/9013', office='St. Veit Wolfsberg')
'591199013'
>>> import json
>>> print(json.dumps(info('59-119/9013'), indent=2, sort_keys=True))
{
  "office": "St. Veit Wolfsberg",
  "region": "K\u00e4rnten"
}
>>> format('591199013')
'59-119/9013'
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, ' -./,').strip()


def _min_fa(office):
    """Convert the tax office name to something that we can use for
    comparison without running into encoding issues."""
    return ''.join(
        x for x in office.lower()
        if x in 'bcdefghijklmnopqrstvwxyz')


def calc_check_digit(number):
    """Calculate the check digit."""
    number = compact(number)
    s = sum(
        int('0246813579'[int(n)]) if i % 2 else int(n)
        for i, n in enumerate(number[:8]))
    return str((10 - s) % 10)


def info(number):
    """Return a dictionary of data about the supplied number. This typically
    returns the the tax office and region."""
    number = compact(number)
    from stdnum import numdb
    return numdb.get('at/fa').info(number[:2])[0][1]


def validate(number, office=None):
    """Check if the number is a valid tax identification number. This checks
    the length and formatting. The tax office can be supplied to check that
    the number was issued in the specified tax office."""
    number = compact(number)
    if len(number) != 9:
        raise InvalidLength()
    if not isdigits(number):
        raise InvalidFormat()
    if calc_check_digit(number) != number[-1]:
        raise InvalidChecksum()
    i = info(number)
    if not i:
        raise InvalidComponent()
    if office and _min_fa(i.get('office')) != _min_fa(office):
        raise InvalidComponent()
    return number


def is_valid(number, office=None):
    """Check if the number is a valid tax identification number. This checks
    the length, formatting and check digit."""
    try:
        return bool(validate(number, office))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    number = compact(number)
    return '%s-%s/%s' % (number[:2], number[2:5], number[5:])
