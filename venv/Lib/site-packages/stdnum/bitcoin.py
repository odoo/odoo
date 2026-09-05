# bitcoin.py - functions for handling Bitcoin addresses
#
# Copyright (C) 2018 Arthur de Jong
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

"""Bitcoin address.

A Bitcoin address is an identifier that is used as destination in a Bitcoin
transaction. It is based on a hash of the public portion of a key pair.

There are currently three address formats in use:

* P2PKH: pay to pubkey hash
* P2SH: pay to script hash
* Bech32

More information:

* https://en.bitcoin.it/wiki/Address

>>> validate('1NEDqZPvTWRaoho48qXuLLsrYomMXPABfD')
'1NEDqZPvTWRaoho48qXuLLsrYomMXPABfD'
>>> validate('BC1QARDV855YJNGSPVXUTTQ897AQCA3LXJU2Y69JCE')
'bc1qardv855yjngspvxuttq897aqca3lxju2y69jce'
>>> validate('1NEDqZPvTWRaoho48qXuLLsrYomMXPABfX')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
"""

import hashlib
import struct
from functools import reduce

from stdnum.exceptions import *
from stdnum.util import clean


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    number = clean(number, ' ').strip()
    if number[:3].lower() == 'bc1':
        number = number.lower()
    return number


# Base58 encoding character set as used in Bitcoin addresses
_base58_alphabet = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'


def b58decode(s):
    """Decode a Base58 encoded string to a bytestring."""
    value = reduce(lambda a, c: a * 58 + _base58_alphabet.index(c), s, 0)
    result = b''
    while value >= 256:
        value, mod = divmod(value, 256)
        result = struct.pack('B', mod) + result
    result = struct.pack('B', value) + result
    return struct.pack('B', 0) * (len(s) - len(s.lstrip('1'))) + result


# Bech32 character set as used in Bitcoin addresses
_bech32_alphabet = 'qpzry9x8gf2tvdw0s3jn54khce6mua7l'


# The Bech32 generator tests and values for checksum calculation
_bech32_generator = (
    (1 << 0, 0x3b6a57b2), (1 << 1, 0x26508e6d), (1 << 2, 0x1ea119fa),
    (1 << 3, 0x3d4233dd), (1 << 4, 0x2a1462b3))


def bech32_checksum(values):
    """Calculate the Bech32 checksum."""
    chk = 1
    for value in values:
        top = chk >> 25
        chk = (chk & 0x1ffffff) << 5 | value
        for t, v in _bech32_generator:
            chk ^= v if top & t else 0
    return chk


def b32decode(data):
    """Decode a list of Base32 values to a bytestring."""
    acc, bits = 0, 0
    result = b''
    for value in data:
        acc = ((acc << 5) | value) & 0xfff
        bits += 5
        if bits >= 8:
            bits -= 8
            result = result + struct.pack('B', (acc >> bits) & 0xff)
    if bits >= 5 or acc & ((1 << bits) - 1):
        raise InvalidComponent()
    return result


def _expand_hrp(hrp):
    """Convert the human-readable part to format for checksum calculation."""
    return [ord(c) >> 5 for c in hrp] + [0] + [ord(c) & 31 for c in hrp]


def validate(number):
    """Check if the number provided is valid. This checks the length and
    check digit."""
    number = compact(number)
    if number.startswith('1') or number.startswith('3'):
        # P2PKH (pay to pubkey hash) or P2SH (pay to script hash) address
        if not all(x in _base58_alphabet for x in number):
            raise InvalidFormat()
        address = b58decode(number)
        if len(address) != 25:
            raise InvalidLength()
        if hashlib.sha256(hashlib.sha256(address[:-4]).digest()).digest()[:4] != address[-4:]:
            raise InvalidChecksum()
    elif number.startswith('bc1'):
        # Bech32 type address
        if not all(x in _bech32_alphabet for x in number[3:]):
            raise InvalidFormat()
        if len(number) < 11 or len(number) > 90:
            raise InvalidLength()
        data = [_bech32_alphabet.index(x) for x in number[3:]]
        if bech32_checksum(_expand_hrp('bc') + data) != 1:
            raise InvalidChecksum()
        witness_version = data[0]
        witness_program = b32decode(data[1:-6])
        if witness_version > 16:
            raise InvalidComponent()
        if len(witness_program) < 2 or len(witness_program) > 40:
            raise InvalidLength()
        if witness_version == 0 and len(witness_program) not in (20, 32):
            raise InvalidLength()
    else:
        raise InvalidComponent()
    return number


def is_valid(number):
    """Check if the number provided is valid. This checks the length and
    check digit."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False
