# ccc.py - functions for handling Spanish CCC bank account code
# coding: utf-8
#
# Copyright (C) 2016 David García Garzón
# Copyright (C) 2016 Arthur de Jong
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

"""CCC (Código Cuenta Corriente, Spanish Bank Account Code)

CCC code is the country-specific part in Spanish IBAN codes. In order to
fully validate an Spanish IBAN you have to validate as well the country
specific part as a valid CCC. It was used for home banking transactions until
February 1st 2014 when IBAN codes started to be used as an account ID.

The CCC has 20 digits, all being numbers: EEEE OOOO DD NNNNNNNNNN

* EEEE: banking entity
* OOOO: office
* DD: check digits
* NNNNN NNNNN: account identifier

This module does not check if the bank code to exist. Existing bank codes are
published on the 'Registro de Entidades' by 'Banco de España' (Spanish
Central Bank).

More information:

* https://es.wikipedia.org/wiki/Código_cuenta_cliente
* https://www.bde.es/bde/es/secciones/servicios/Particulares_y_e/Registros_de_Ent/

>>> validate('1234-1234-16 1234567890')
'12341234161234567890'
>>> validate('134-1234-16 1234567890')  # wrong length
Traceback (most recent call last):
    ...
InvalidLength: ...
>>> validate('12X4-1234-16 1234567890')  # non numbers
Traceback (most recent call last):
    ...
InvalidFormat: ...
>>> validate('1234-1234-00 1234567890')  # invalid check digits
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> format('12341234161234567890')
'1234 1234 16 12345 67890'
>>> to_iban('21000418450200051331')
'ES2121000418450200051331'
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, ' -').strip().upper()


def format(number):
    """Reformat the number to the standard presentation format."""
    number = compact(number)
    return ' '.join([
        number[0:4],
        number[4:8],
        number[8:10],
        number[10:15],
        number[15:20],
    ])


def _calc_check_digit(number):
    """Calculate a single check digit on the provided part of the number."""
    check = sum(int(n) * 2 ** i for i, n in enumerate(number)) % 11
    return str(check if check < 2 else 11 - check)


def calc_check_digits(number):
    """Calculate the check digits for the number. The supplied number should
    have check digits included but are ignored."""
    number = compact(number)
    return (
        _calc_check_digit('00' + number[:8]) + _calc_check_digit(number[10:]))


def validate(number):
    """Check if the number provided is a valid CCC."""
    number = compact(number)
    if len(number) != 20:
        raise InvalidLength()
    if not isdigits(number):
        raise InvalidFormat()
    if number[8:10] != calc_check_digits(number):
        raise InvalidChecksum()
    return number


def is_valid(number):
    """Check if the number provided is a valid CCC."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def to_iban(number):
    """Convert the number to an IBAN."""
    from stdnum import iban
    separator = ' ' if ' ' in number else ''
    return separator.join((
        'ES' + iban.calc_check_digits('ES00' + number),
        number))
