# cc.py - functions for handling Portuguese Identity numbers
# coding: utf-8
#
# Copyright (C) 2021 David Vaz
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

"""CC (Número de Cartão de Cidadão, Portuguese Identity number).

The Portuguese Identity Number is alphanumeric and consists of the numeric
Número de Identificação Civil, a two-letter version and a check digit.

More information:

* https://pt.wikipedia.org/wiki/Cartão_de_cidadão
* https://www.autenticacao.gov.pt/documents/20126/115760/Validação+de+Número+de+Documento+do+Cartão+de+Cidadão.pdf

>>> validate('00000000 0 ZZ4')
'000000000ZZ4'
>>> validate('00000000 A ZZ4')  # invalid format
Traceback (most recent call last):
    ...
InvalidFormat: ...
>>> validate('00000000 0 ZZ3')  # invalid check digits
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> format('000000000ZZ4')
'00000000 0 ZZ4'
"""

import re

from stdnum.exceptions import *
from stdnum.util import clean


_cc_re = re.compile(r'^\d*[A-Z0-9]{2}\d$')


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    number = clean(number, ' ').upper().strip()
    return number


def calc_check_digit(number):
    """Calculate the check digit for the number."""
    alphabet = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    cutoff = lambda x: x - 9 if x > 9 else x
    s = sum(
        cutoff(alphabet.index(n) * 2) if i % 2 == 0 else alphabet.index(n)
        for i, n in enumerate(number[::-1]))
    return str((10 - s) % 10)


def validate(number):
    """Check if the number is a valid cartao de cidadao number."""
    number = compact(number)
    if not _cc_re.match(number):
        raise InvalidFormat()
    if calc_check_digit(number[:-1]) != number[-1]:
        raise InvalidChecksum()
    return number


def is_valid(number):
    """Check if the number is a valid cartao de cidadao number."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    number = compact(number)
    return ' '.join([number[:-4], number[-4], number[-3:]])
