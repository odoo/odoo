# nace.py - functions for handling EU NACE classification
# coding: utf-8
#
# Copyright (C) 2017-2019 Arthur de Jong
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

"""NACE (classification for businesses in the European Union).

The NACE (nomenclature statistique des activités économiques dans la
Communauté européenne) is a 4-level (and up to 4 digit) code for classifying
economic activities. It is the European implementation of the UN
classification ISIC.

The first 4 digits are the same in all EU countries while additional levels
and digits may be vary between countries. This module validates the numbers
according to revision 2 and based on the registry as published by the EC.

More information:

* https://en.wikipedia.org/wiki/Statistical_Classification_of_Economic_Activities_in_the_European_Community
* https://ec.europa.eu/eurostat/ramon/nomenclatures/index.cfm?TargetUrl=LST_NOM_DTL&StrNom=NACE_REV2&StrLanguageCode=EN&IntPcKey=&StrLayoutCode=HIERARCHIC

>>> validate('A')
'A'
>>> validate('62.01')
'6201'
>>> str(get_label('62.01'))
'Computer programming activities'
>>> validate('62.05')
Traceback (most recent call last):
    ...
InvalidComponent: ...
>>> validate('62059')  # does not validate country-specific numbers
Traceback (most recent call last):
    ...
InvalidLength: ...
>>> format('6201')
'62.01'
"""

import warnings

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, '.').strip()


def info(number):
    """Lookup information about the specified NACE. This returns a dict."""
    number = compact(number)
    from stdnum import numdb
    info = dict()
    for _n, i in numdb.get('eu/nace').info(number):
        if not i:
            raise InvalidComponent()
        info.update(i)
    return info


def get_label(number):
    """Lookup the category label for the number."""
    return info(number)['label']


def label(number):  # pragma: no cover (deprecated function)
    """DEPRECATED: use `get_label()` instead."""  # noqa: D40
    warnings.warn(
        'label() has been to get_label()',
        DeprecationWarning, stacklevel=2)
    return get_label(number)


def validate(number):
    """Check if the number is a valid NACE. This checks the format and
    searches the registry to see if it exists."""
    number = compact(number)
    if len(number) > 4:
        raise InvalidLength()
    elif len(number) == 1:
        if not number.isalpha():
            raise InvalidFormat()
    else:
        if not isdigits(number):
            raise InvalidFormat()
    info(number)
    return number


def is_valid(number):
    """Check if the number is a valid NACE. This checks the format and
    searches the registry to see if it exists."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    return '.'.join((number[:2], number[2:])).strip('.')
