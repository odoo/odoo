# nir.py - functions for handling French NIR numbers
# coding: utf-8
#
# Copyright (C) 2016 Dimitri Papadopoulos
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

"""NIR (French personal identification number).

The NIR (Numero d'Inscription au Repertoire national d'identification des
personnes physiques) is used to identify persons in France. It is popularly
known as the "social security number" and sometimes referred to as an INSEE
number. All persons born in France are registered in the Repertoire national
d'identification des personnes physiques (RNIPP) and assigned a NIR.

The number consists of 15 digits: the first digit indicates the gender,
followed by 2 digits for the year or birth, 2 for the month of birth, 5 for
the location of birth (COG), 3 for a serial and 2 check digits.

More information:

* https://www.insee.fr/en/metadonnees/definition/c1409
* https://en.wikipedia.org/wiki/INSEE_code
* http://resoo.org/docs/_docs/regles-numero-insee.pdf
* https://fr.wikipedia.org/wiki/Numéro_de_sécurité_sociale_en_France
* https://xml.insee.fr/schema/nir.html

>>> validate('2 95 10 99 126 111 93')
'295109912611193'
>>> validate('295109912611199')  # invalid check digit
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> validate('253072B07300470')
'253072B07300470'
>>> validate('253072A07300443')
'253072A07300443'
>>> validate('253072C07300443')
Traceback (most recent call last):
    ...
InvalidFormat: ...
>>> validate('6546546546546703')
Traceback (most recent call last):
    ...
InvalidLength: ...
>>> format('295109912611193')
'2 95 10 99 126 111 93'
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, ' .').strip().upper()


def calc_check_digits(number):
    """Calculate the check digits for the number."""
    department = number[5:7]
    if department == '2A':
        number = number[:5] + '19' + number[7:]
    elif department == '2B':
        number = number[:5] + '18' + number[7:]
    return '%02d' % (97 - (int(number[:13]) % 97))


def validate(number):
    """Check if the number provided is valid. This checks the length
    and check digits."""
    number = compact(number)
    if not isdigits(number[:5]) or not isdigits(number[7:]):
        raise InvalidFormat()
    if not isdigits(number[5:7]) and number[5:7] not in ('2A', '2B'):
        raise InvalidFormat()
    if len(number) != 15:
        raise InvalidLength()
    if calc_check_digits(number) != number[13:]:
        raise InvalidChecksum()
    return number


def is_valid(number):
    """Check if the number provided is valid."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number, separator=' '):
    """Reformat the number to the standard presentation format."""
    number = compact(number)
    return separator.join((
        number[:1], number[1:3], number[3:5], number[5:7], number[7:10],
        number[10:13], number[13:]))
