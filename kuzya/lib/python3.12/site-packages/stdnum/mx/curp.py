# curp.py - functions for handling Mexican personal identifiers
# coding: utf-8
#
# Copyright (C) 2019 Arthur de Jong
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

"""CURP (Clave Única de Registro de Población, Mexican personal ID).

The Clave Única de Registro de Población (Population Registry Code) is unique
identifier for both citizens and residents of Mexico. The is an 18-character
alphanumeric that contains certain letters from the person's name, their
gender and birth date and a check digit.

More information:

* https://en.wikipedia.org/wiki/CURP
* https://www.gob.mx/curp/

>>> validate('BOXW310820HNERXN09')
'BOXW310820HNERXN09'
>>> validate('BOXW310820HNERXN08')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> get_birth_date('BOXW310820HNERXN09')
datetime.date(1931, 8, 20)
>>> get_gender('BOXW310820HNERXN09')
'M'
"""

import datetime
import re

from stdnum.exceptions import *
from stdnum.util import clean


# these values should not appear as first part
_name_blacklist = set('''
    BACA BAKA BUEI BUEY CACA CACO CAGA CAGO CAKA CAKO COGE COGI COJA COJE
    COJI COJO COLA CULO FALO FETO GETA GUEI GUEY JETA JOTO KACA KACO KAGA
    KAGO KAKA KAKO KOGE KOGI KOJA KOJE KOJI KOJO KOLA KULO LILO LOCA LOCO
    LOKA LOKO MAME MAMO MEAR MEAS MEON MIAR MION MOCO MOKO MULA MULO NACA
    NACO PEDA PEDO PENE PIPI PITO POPO PUTA PUTO QULO RATA ROBA ROBE ROBO
    RUIN SENO TETA VACA VAGA VAGO VAKA VUEI VUEY WUEI WUEY
'''.split())

# these are valid two-character states
_valid_states = set('''
    AS BC BS CC CH CL CM CS DF DG GR GT HG JC MC MN MS NE NL NT OC PL QR QT
    SL SP SR TC TL TS VZ YN ZS
'''.split())


def compact(number):
    """Convert the number to the minimal representation. This strips
    surrounding whitespace and separation dash."""
    return clean(number, '-_ ').upper().strip()


def get_birth_date(number):
    """Split the date parts from the number and return the birth date."""
    number = compact(number)
    year = int(number[4:6])
    month = int(number[6:8])
    day = int(number[8:10])
    if number[16].isdigit():
        year += 1900
    else:
        year += 2000
    try:
        return datetime.date(year, month, day)
    except ValueError:
        raise InvalidComponent()


def get_gender(number):
    """Get the gender (M/F) from the person's CURP."""
    number = compact(number)
    if number[10] == 'H':
        return 'M'
    elif number[10] == 'M':
        return 'F'
    else:
        raise InvalidComponent()


# characters used for checksum calculation,
_alphabet = '0123456789ABCDEFGHIJKLMN&OPQRSTUVWXYZ'


def calc_check_digit(number):
    """Calculate the check digit."""
    check = sum(_alphabet.index(c) * (18 - i) for i, c in enumerate(number[:17]))
    return str((10 - check % 10) % 10)


def validate(number, validate_check_digits=True):
    """Check if the number is a valid CURP."""
    number = compact(number)
    if len(number) != 18:
        raise InvalidLength()
    if not re.match(u'^[A-Z]{4}[0-9]{6}[A-Z]{6}[0-9A-Z][0-9]$', number):
        raise InvalidFormat()
    if number[:4] in _name_blacklist:
        raise InvalidComponent()
    get_birth_date(number)
    get_gender(number)
    if number[11:13] not in _valid_states:
        raise InvalidComponent()
    if validate_check_digits and number[-1] != calc_check_digit(number):
        raise InvalidChecksum()
    return number


def is_valid(number, validate_check_digits=True):
    """Check if the number provided is a valid CURP."""
    try:
        return bool(validate(number, validate_check_digits))
    except ValidationError:
        return False
