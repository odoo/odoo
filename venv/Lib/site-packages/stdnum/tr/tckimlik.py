# tckimlik.py - functions for handling T.C. Kimlik No.
# coding: utf-8
#
# Copyright (C) 2016-2018 Arthur de Jong
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

"""T.C. Kimlik No. (Turkish personal identification number)

The Turkish Identification Number (Türkiye Cumhuriyeti Kimlik Numarası) is a
unique personal identification number assigned to every citizen of Turkey.
The number consists of 11 digits and the last two digits are check digits.

More information:

* https://en.wikipedia.org/wiki/Turkish_Identification_Number
* https://tckimlik.nvi.gov.tr/

>>> validate('17291716060')
'17291716060'
>>> validate('17291716050')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> validate('1729171606')
Traceback (most recent call last):
    ...
InvalidLength: ...
>>> validate('07291716092')  # number must not start with a 0
Traceback (most recent call last):
    ...
InvalidFormat: ...
"""

from stdnum.exceptions import *
from stdnum.util import clean, get_soap_client, isdigits


tckimlik_wsdl = 'https://tckimlik.nvi.gov.tr/Service/KPSPublic.asmx?WSDL'
"""The WSDL URL of the T.C. Kimlik validation service."""


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number).strip()


def calc_check_digits(number):
    """Calculate the check digits for the specified number. The number
    passed should not have the check digit included."""
    check1 = (10 - sum((3, 1)[i % 2] * int(n)
              for i, n in enumerate(number[:9]))) % 10
    check2 = (check1 + sum(int(n) for n in number[:9])) % 10
    return '%d%d' % (check1, check2)


def validate(number):
    """Check if the number is a valid T.C. Kimlik number. This checks the
    length and check digits."""
    number = compact(number)
    if not isdigits(number) or number[0] == '0':
        raise InvalidFormat()
    if len(number) != 11:
        raise InvalidLength()
    if calc_check_digits(number) != number[-2:]:
        raise InvalidChecksum()
    return number


def is_valid(number):
    """Check if the number is a valid T.C. Kimlik number."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def check_kps(number, name, surname, birth_year, timeout):  # pragma: no cover
    """Query the online T.C. Kimlik validation service run by the Directorate
    of Population and Citizenship Affairs. The timeout is in seconds. This
    returns a boolean but may raise a SOAP exception for missing or invalid
    values."""
    # this function isn't automatically tested because it would require
    # network access for the tests and unnecessarily load the online service
    number = compact(number)
    client = get_soap_client(tckimlik_wsdl, timeout)
    result = client.TCKimlikNoDogrula(
        TCKimlikNo=number, Ad=name, Soyad=surname, DogumYili=birth_year)
    if hasattr(result, 'get'):
        return result.get('TCKimlikNoDogrulaResult')
    return result
