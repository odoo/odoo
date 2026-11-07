# esr.py - functions for handling Swiss EinzahlungsSchein mit Referenznummer
# coding: utf-8
#
# Copyright (C) 2019 Kurt Keller
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

"""ESR, ISR, QR-reference (reference number on Swiss payment slips).

The ESR (Eizahlungsschein mit Referenznummer), ISR (In-payment Slip with
Reference Number) or QR-reference refers to the orange payment slip in
Switzerland with which money can be transferred to an account. The slip
contains a machine-readable part that contains a participant number and
reference number. The participant number ensures the crediting to the
corresponding account. The reference number enables the creditor to identify
the invoice recipient. In this way, the payment process can be handled
entirely electronically.

The number consists of 26 numerical characters followed by a Modulo 10
recursive check digit. It is printed in blocks of 5 characters (beginning
with 2 characters, then 5x5-character groups). Leading zeros digits can be
omitted.

More information:

* https://www.paymentstandards.ch/dam/downloads/ig-qr-bill-en.pdf

>>> validate('21 00000 00003 13947 14300 09017')
'210000000003139471430009017'
>>> validate('210000000003139471430009016')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> format('18 78583')
'00 00000 00000 00000 00018 78583'
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips
    surrounding whitespace and separators."""
    return clean(number, ' ').lstrip('0')


def calc_check_digit(number):
    """Calculate the check digit for number. The number passed should
    not have the check digit included."""
    _digits = (0, 9, 4, 6, 8, 2, 7, 1, 3, 5)
    c = 0
    for n in compact(number):
        c = _digits[(int(n) + c) % 10]
    return str((10 - c) % 10)


def validate(number):
    """Check if the number is a valid ESR. This checks the length, formatting
    and check digit."""
    number = compact(number)
    if len(number) > 27:
        raise InvalidLength()
    if not isdigits(number):
        raise InvalidFormat()
    if number[-1] != calc_check_digit(number[:-1]):
        raise InvalidChecksum()
    return number


def is_valid(number):
    """Check if the number is a valid ESR."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    number = 27 * '0' + compact(number)
    number = number[-27:]
    return number[:2] + ' ' + ' '.join(
        number[i:i + 5] for i in range(2, len(number), 5))
