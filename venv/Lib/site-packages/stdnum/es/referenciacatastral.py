# referenciacatastral.py - functions for handling Spanish real state ids
# coding: utf-8
#
# Copyright (C) 2016 David García Garzón
# Copyright (C) 2016-2017 Arthur de Jong
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

"""Referencia Catastral (Spanish real estate property id)

The cadastral reference code is an identifier for real estate in Spain. It is
issued by Dirección General del Catastro (General Directorate of Land
Registry) of the Ministerio de Hacienda (Tresury Ministry).

It has 20 digits and contains numbers and letters including the Spanish Ñ.
The number consists of 14 digits for the parcel, 4 for identifying properties
within the parcel and 2 check digits. The parcel digits are structured
differently for urban, non-urban or special (infrastructure) cases.

More information:

* https://www.catastro.meh.es/ (Spanish)
* https://www.catastro.meh.es/documentos/05042010_P.pdf (Spanish)
* https://es.wikipedia.org/wiki/Catastro#Referencia_catastral

>>> validate('7837301-VG8173B-0001 TT')  # Lanteira town hall
'7837301VG8173B0001TT'
>>> validate('783301 VG8173B 0001 TT')  # missing digit
Traceback (most recent call last):
    ...
InvalidLength: ...
>>> validate('7837301/VG8173B 0001 TT')  # not alphanumeric
Traceback (most recent call last):
    ...
InvalidFormat: ...
>>> validate('7837301 VG8173B 0001 NN')  # bad check digits
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> format('4A08169P03PRAT0001LR')  # BCN Airport
'4A08169 P03PRAT 0001 LR'
"""

from stdnum.exceptions import *
from stdnum.util import clean, to_unicode


alphabet = u'ABCDEFGHIJKLMNÑOPQRSTUVWXYZ0123456789'


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, ' -').strip().upper()


def format(number):
    """Reformat the number to the standard presentation format."""
    number = compact(number)
    return ' '.join([
        number[:7],
        number[7:14],
        number[14:18],
        number[18:]])


# The check digit implementation is based on the Javascript
# implementation by Vicente Sancho that can be found at
# https://trellat.es/validar-la-referencia-catastral-en-javascript/

def _check_digit(number):
    """Calculate a single check digit on the provided part of the number."""
    weights = (13, 15, 12, 5, 4, 17, 9, 21, 3, 7, 1)
    s = sum(w * (int(n) if n.isdigit() else alphabet.find(n) + 1)
            for w, n in zip(weights, number))
    return 'MQWERTYUIOPASDFGHJKLBZX'[s % 23]


def calc_check_digits(number):
    """Calculate the check digits for the number."""
    number = to_unicode(compact(number))
    return (
        _check_digit(number[0:7] + number[14:18]) +
        _check_digit(number[7:14] + number[14:18]))


def validate(number):
    """Check if the number is a valid Cadastral Reference. This checks the
    length, formatting and check digits."""
    number = compact(number)
    n = to_unicode(number)
    if not all(c in alphabet for c in n):
        raise InvalidFormat()
    if len(n) != 20:
        raise InvalidLength()
    if calc_check_digits(n) != n[18:]:
        raise InvalidChecksum()
    return number


def is_valid(number):
    """Check if the number is a valid Cadastral Reference."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False
