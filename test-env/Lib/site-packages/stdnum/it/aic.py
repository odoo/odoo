# aic.py - functions for handling Italian AIC codes
# coding: utf-8
#
# This file is based on pyAIC Python library.
# https://github.com/FabrizioMontanari/pyAIC
#
# Copyright (C) 2020 Fabrizio Montanari
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

"""AIC (Italian code for identification of drugs).

AIC codes are used to identify drugs allowed to be sold in Italy. Codes are
issued by the Italian Drugs Agency (AIFA, Agenzia Italiana del Farmaco), the
government authority responsible for drugs regulation in Italy.

The number consists of 9 digits and includes a check digit.

More information:

* https://www.gazzettaufficiale.it/do/atto/serie_generale/caricaPdf?cdimg=14A0566800100010110001&dgu=2014-07-18&art.dataPubblicazioneGazzetta=2014-07-18&art.codiceRedazionale=14A05668&art.num=1&art.tiposerie=SG

>>> validate('000307052')  # BASE10 format
'000307052'
>>> validate('009CVD')  # BASE32 format is converted
'000307052'
>>> validate_base10('000307052')
'000307052'
>>> validate_base32('009CVD')
'000307052'
>>> to_base32('000307052')
'009CVD'
>>> from_base32('009CVD')
'000307052'
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


# the table of AIC BASE32 allowed chars.
_base32_alphabet = '0123456789BCDFGHJKLMNPQRSTUVWXYZ'


def compact(number):
    """Convert the number to the minimal representation."""
    return clean(number, ' ').upper().strip()


def from_base32(number):
    """Convert a BASE32 representation of an AIC to a BASE10 one."""
    number = compact(number)
    if not all(x in _base32_alphabet for x in number):
        raise InvalidFormat()
    s = sum(_base32_alphabet.index(n) * 32 ** i
            for i, n in enumerate(reversed(number)))
    return str(s).zfill(9)


def to_base32(number):
    """Convert a BASE10 representation of an AIC to a BASE32 one."""
    number = compact(number)
    if not isdigits(number):
        raise InvalidFormat()
    res = ''
    remainder = int(number)
    while remainder > 31:
        res = _base32_alphabet[remainder % 32] + res
        remainder = remainder // 32
    res = _base32_alphabet[remainder] + res
    return res.zfill(6)


def calc_check_digit(number):
    """Calculate the check digit for the BASE10 AIC code."""
    number = compact(number)
    weights = (1, 2, 1, 2, 1, 2, 1, 2)
    return str(sum((x // 10) + (x % 10)
               for x in (w * int(n) for w, n in zip(weights, number))) % 10)


def validate_base10(number):
    """Check if a string is a valid BASE10 representation of an AIC."""
    number = compact(number)
    if len(number) != 9:
        raise InvalidLength()
    if not isdigits(number):
        raise InvalidFormat()
    if number[0] != '0':
        raise InvalidComponent()
    if calc_check_digit(number) != number[-1]:
        raise InvalidChecksum()
    return number


def validate_base32(number):
    """Check if a string is a valid BASE32 representation of an AIC."""
    number = compact(number)
    if len(number) != 6:
        raise InvalidLength()
    return validate_base10(from_base32(number))


def validate(number):
    """Check if a string is a valid AIC. BASE10 is the canonical form and
    is 9 chars long, while BASE32 is 6 chars."""
    number = compact(number)
    if len(number) == 6:
        return validate_base32(number)
    else:
        return validate_base10(number)


def is_valid(number):
    """Check if the given string is a valid AIC code."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False
