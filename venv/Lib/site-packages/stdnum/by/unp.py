# unp.py - functions for handling Belarusian UNP numbers
# coding: utf-8
#
# Copyright (C) 2020 Arthur de Jong
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

"""УНП, UNP (Учетный номер плательщика, the Belarus VAT number).

The УНП (UNP) or Учетный номер плательщика (Uchetniy nomer platel'shika,
Payer account number) is issued to organisations and individuals for tax
purposes. The number consists of 9 digits (numeric for organisations,
alphanumeric for individuals) and contains a region identifier, a serial per
region and a check digit.

More information:

* https://be.wikipedia.org/wiki/Уліковы_нумар_плацельшчыка
* http://pravo.levonevsky.org/bazaby09/sbor37/text37892/index3.htm

>>> validate('200988541')
'200988541'
>>> validate('УНП MA1953684')
'MA1953684'
>>> validate('200988542')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits, to_unicode


# Mapping of Cyrillic letters to Latin letters
_cyrillic_to_latin = dict(zip(
    u'АВЕКМНОРСТ',
    u'ABEKMHOPCT',
))


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    number = clean(number, ' ').upper().strip()
    for prefix in ('УНП', u'УНП', 'UNP', u'UNP'):
        if type(number) == type(prefix) and number.startswith(prefix):
            number = number[len(prefix):]
    # Replace Cyrillic letters with Latin letters
    cleaned = ''.join(_cyrillic_to_latin.get(x, x) for x in to_unicode(number))
    if type(cleaned) != type(number):  # pragma: no cover (Python2 only)
        cleaned = cleaned.encode('utf-8')
    return cleaned


def calc_check_digit(number):
    """Calculate the check digit for the number."""
    number = compact(number)
    alphabet = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    weights = (29, 23, 19, 17, 13, 7, 5, 3)
    if not isdigits(number):
        number = number[0] + str('ABCEHKMOPT'.index(number[1])) + number[2:]
    c = sum(w * alphabet.index(n) for w, n in zip(weights, number)) % 11
    if c > 9:
        raise InvalidChecksum()
    return str(c)


def validate(number):
    """Check if the number is a valid number. This checks the length,
    formatting and check digit."""
    number = compact(number)
    if len(number) != 9:
        raise InvalidLength()
    if not isdigits(number[2:]):
        raise InvalidFormat()
    if not isdigits(number[:2]) and not all(x in 'ABCEHKMOPT' for x in number[:2]):
        raise InvalidFormat()
    if number[0] not in '1234567ABCEHKM':
        raise InvalidComponent()
    if number[-1] != calc_check_digit(number):
        raise InvalidChecksum()
    return number


def is_valid(number):
    """Check if the number is a valid number."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def check_nalog(number, timeout=30):  # pragma: no cover (not part of normal test suite)
    """Retrieve registration information from the portal.nalog.gov.by web site.

    This basically returns the JSON response from the web service as a dict.
    Will return ``None`` if the number is invalid or unknown.
    """
    # this function isn't automatically tested because it would require
    # network access for the tests and unnecessarily load the web service
    # Since the nalog.gov.by web site currently provides an incomplete
    # certificate chain, we provide our own.
    import requests
    from pkg_resources import resource_filename
    certificate = resource_filename(__name__, 'portal.nalog.gov.by.crt')
    response = requests.get(
        'https://www.portal.nalog.gov.by/grp/getData',
        params={
            'unp': compact(number),
            'charset': 'UTF-8',
            'type': 'json'},
        timeout=timeout,
        verify=certificate)
    if response.ok:
        return response.json()['ROW']
