# rfc.py - functions for handling Mexican tax numbers
# coding: utf-8
#
# Copyright (C) 2015 Arthur de Jong
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

"""RFC (Registro Federal de Contribuyentes, Mexican tax number).

This number is used to identify individuals and companies for tax purposes.

The company number is 12 digits where the first 3 letters or digits are
derived from the name of the company, the following 6 contain the date of
incorporation, followed by 3 check digits.

Personal numbers consist of 13 digits where the first 4 characters from the
person's name, followed by their birth date and 3 check digits.

The first two check digits are calculated based on the person's or company's
full name. The last check digit is calculated over all the preceding digits
in the number. However, it seems a lot of numbers (estimated at around 1.5%
of all numbers) are in use with invalid check digits so this test is disabled
by default.

More information:

* https://www.infomex.org.mx/jspsi/documentos/2005/seguimiento/06101/0610100162005_065.doc
* https://es.wikipedia.org/wiki/Registro_Federal_de_Contribuyentes_(M%C3%A9xico)

An online validation service is available at:

* https://portalsat.plataforma.sat.gob.mx/ConsultaRFC/

>>> validate('GODE 561231 GR8')  # personal number
'GODE561231GR8'
>>> validate('MAB-930714-8T4')  # company number
'MAB9307148T4'
>>> validate('COMG-600703')  # personal number without serial
'COMG600703'
>>> validate('VACE-460910-SX6')
'VACE460910SX6'
>>> validate('VACE-460910-SX6', validate_check_digits=True)
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> format('GODE561231GR8')
'GODE 561231 GR8'
"""

import datetime
import re

from stdnum.exceptions import *
from stdnum.util import clean, to_unicode


# these values should not appear as first part of a personal number
_name_blacklist = set([
    'BUEI', 'BUEY', 'CACA', 'CACO', 'CAGA', 'CAGO', 'CAKA', 'CAKO', 'COGE',
    'COJA', 'COJE', 'COJI', 'COJO', 'CULO', 'FETO', 'GUEY', 'JOTO', 'KACA',
    'KACO', 'KAGA', 'KAGO', 'KAKA', 'KOGE', 'KOJO', 'KULO', 'MAME', 'MAMO',
    'MEAR', 'MEAS', 'MEON', 'MION', 'MOCO', 'MULA', 'PEDA', 'PEDO', 'PENE',
    'PUTA', 'PUTO', 'QULO', 'RATA', 'RUIN',
])


# characters used for checksum calculation,
_alphabet = u'0123456789ABCDEFGHIJKLMN&OPQRSTUVWXYZ Ñ'


def compact(number):
    """Convert the number to the minimal representation. This strips
    surrounding whitespace and separation dash."""
    return clean(number, '-_ ').upper().strip()


def _get_date(number):
    """Convert the part of the number that represents a date into a
    datetime. Note that the century may be incorrect."""
    year = int(number[0:2])
    month = int(number[2:4])
    day = int(number[4:6])
    try:
        return datetime.date(year + 2000, month, day)
    except ValueError:
        raise InvalidComponent()


def calc_check_digit(number):
    """Calculate the check digit. The number passed should not have the
    check digit included."""
    number = to_unicode(number)
    number = ('   ' + number)[-12:]
    check = sum(_alphabet.index(n) * (13 - i) for i, n in enumerate(number))
    return _alphabet[(11 - check) % 11]


def validate(number, validate_check_digits=False):
    """Check if the number is a valid RFC."""
    number = compact(number)
    n = to_unicode(number)
    if len(n) in (10, 13):
        # number assigned to person
        if not re.match(u'^[A-Z&Ñ]{4}[0-9]{6}[0-9A-Z]{0,3}$', n):
            raise InvalidFormat()
        if n[:4] in _name_blacklist:
            raise InvalidComponent()
        _get_date(n[4:10])
    elif len(n) == 12:
        # number assigned to company
        if not re.match(u'^[A-Z&Ñ]{3}[0-9]{6}[0-9A-Z]{3}$', n):
            raise InvalidFormat()
        _get_date(n[3:9])
    else:
        raise InvalidLength()
    if validate_check_digits and len(n) >= 12:
        if not re.match(u'^[1-9A-V][1-9A-Z][0-9A]$', n[-3:]):
            raise InvalidComponent()
        if n[-1] != calc_check_digit(n[:-1]):
            raise InvalidChecksum()
    return number


def is_valid(number, validate_check_digits=False):
    """Check if the number provided is a valid RFC."""
    try:
        return bool(validate(number, validate_check_digits))
    except ValidationError:
        return False


def format(number, separator=' '):
    """Reformat the number to the standard presentation format."""
    number = compact(number)
    if len(number) == 12:
        return separator.join((
            number[:3], number[3:9], number[9:])).strip(separator)
    return separator.join((
        number[:4], number[4:10], number[10:])).strip(separator)
