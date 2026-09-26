# stnr.py - functions for handling German tax numbers
# coding: utf-8
#
# Copyright (C) 2017 Holvi Payment Services
# Copyright (C) 2018-2019 Arthur de Jong
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

"""St.-Nr. (Steuernummer, German tax number).

The Steuernummer (St.-Nr.) is a tax number assigned by regional tax offices
to taxable individuals and organisations. The number is being replaced by the
Steuerliche Identifikationsnummer (IdNr).

The number has 10 or 11 digits for the regional form (per Bundesland) and 13
digits for the number that is unique within Germany. The number consists of
(part of) the Bundesfinanzamtsnummer (BUFA-Nr.), a district number, a serial
number and a check digit.

More information:

* https://de.wikipedia.org/wiki/Steuernummer

>>> validate(' 181/815/0815 5')
'18181508155'
>>> validate('201/123/12340', 'Sachsen')
'20112312340'
>>> validate('4151081508156', 'Thuringen')
'4151081508156'
>>> validate('4151181508156', 'Thuringen')
Traceback (most recent call last):
    ...
InvalidFormat: ...
>>> validate('136695978')
Traceback (most recent call last):
    ...
InvalidLength: ...
"""

import re

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


# The number formats per region (regional and country-wide format)
_number_formats_per_region = {
    'Baden-Württemberg': ['FFBBBUUUUP', '28FF0BBBUUUUP'],
    'Bayern': ['FFFBBBUUUUP', '9FFF0BBBUUUUP'],
    'Berlin': ['FFBBBUUUUP', '11FF0BBBUUUUP'],
    'Brandenburg': ['0FFBBBUUUUP', '30FF0BBBUUUUP'],
    'Bremen': ['FFBBBUUUUP', '24FF0BBBUUUUP'],
    'Hamburg': ['FFBBBUUUUP', '22FF0BBBUUUUP'],
    'Hessen': ['0FFBBBUUUUP', '26FF0BBBUUUUP'],
    'Mecklenburg-Vorpommern': ['0FFBBBUUUUP', '40FF0BBBUUUUP'],
    'Niedersachsen': ['FFBBBUUUUP', '23FF0BBBUUUUP'],
    'Nordrhein-Westfalen': ['FFFBBBBUUUP', '5FFF0BBBBUUUP'],
    'Rheinland-Pfalz': ['FFBBBUUUUP', '27FF0BBBUUUUP'],
    'Saarland': ['0FFBBBUUUUP', '10FF0BBBUUUUP'],
    'Sachsen': ['2FFBBBUUUUP', '32FF0BBBUUUUP'],
    'Sachsen-Anhalt': ['1FFBBBUUUUP', '31FF0BBBUUUUP'],
    'Schleswig-Holstein': ['FFBBBUUUUP', '21FF0BBBUUUUP'],
    'Thüringen': ['1FFBBBUUUUP', '41FF0BBBUUUUP'],
}

REGIONS = sorted(_number_formats_per_region.keys())
"""Valid regions recognised by this module."""


def _clean_region(region):
    """Convert the region name to something that we can use for comparison
    without running into encoding issues."""
    return ''.join(
        x for x in region.lower()
        if x in 'abcdefghijklmnopqrstvwxyz')


class _Format():

    def __init__(self, fmt):
        self._fmt = fmt
        self._re = re.compile('^%s$' % re.sub(
            r'([FBUP])\1*',
            lambda x: r'(\d{%d})' % len(x.group(0)), fmt))

    def match(self, number):
        return self._re.match(number)

    def replace(self, f, b, u, p):
        items = iter([f, b, u, p])
        return re.sub(r'([FBUP])\1*', lambda x: next(items), self._fmt)


# Convert the structure to something that we can easily use
_number_formats_per_region = dict(
    (_clean_region(region), [
        region, _Format(formats[0]), _Format(formats[1])])
    for region, formats in _number_formats_per_region.items())


def _get_formats(region=None):
    """Return the formats for the region."""
    if region:
        region = _clean_region(region)
        if region not in _number_formats_per_region:
            raise InvalidComponent()
        return [_number_formats_per_region[region]]
    return _number_formats_per_region.values()


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, ' -./,').strip()


def validate(number, region=None):
    """Check if the number is a valid tax number. This checks the length and
    formatting. The region can be supplied to verify that the number is
    assigned in that region."""
    number = compact(number)
    if not isdigits(number):
        raise InvalidFormat()
    if len(number) not in (10, 11, 13):
        raise InvalidLength()
    if not any(region_fmt.match(number) or country_fmt.match(number)
               for _region, region_fmt, country_fmt in _get_formats(region)):
        raise InvalidFormat()
    return number


def is_valid(number, region=None):
    """Check if the number is a valid tax number. This checks the length and
    formatting. The region can be supplied to verify that the number is
    assigned in that region."""
    try:
        return bool(validate(number, region))
    except ValidationError:
        return False


def guess_regions(number):
    """Return a list of regions this number is valid for."""
    number = compact(number)
    return sorted(
        region for region, region_fmt, country_fmt in _get_formats()
        if region_fmt.match(number) or country_fmt.match(number))


def to_regional_number(number):
    """Convert the number to a regional (10 or 11 digit) number."""
    number = compact(number)
    for _region, region_fmt, country_fmt in _get_formats():
        m = country_fmt.match(number)
        if m:
            return region_fmt.replace(*m.groups())
    raise InvalidFormat()


def to_country_number(number, region=None):
    """Convert the number to the nationally unique number. The region is
    needed if the number is not only valid for one particular region."""
    number = compact(number)
    formats = (
        (region_fmt.match(number), country_fmt)
        for _region, region_fmt, country_fmt in _get_formats(region))
    formats = [
        (region_match, country_fmt)
        for region_match, country_fmt in formats
        if region_match]
    if not formats:
        raise InvalidFormat()
    if len(formats) != 1:
        raise InvalidComponent()
    return formats[0][1].replace(*formats[0][0].groups())


def format(number, region=None):
    """Reformat the passed number to the standard format."""
    number = compact(number)
    for _region, region_fmt, _country_fmt in _get_formats(region):
        m = region_fmt.match(number)
        if m:
            f, b, u, p = m.groups()
            return region_fmt.replace(f + '/', b + '/', u, p)
    return number
