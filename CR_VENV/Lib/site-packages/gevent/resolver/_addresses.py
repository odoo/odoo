# -*- coding: utf-8 -*-
# Copyright (c) 2019  gevent contributors. See LICENSE for details.
#
# Portions of this code taken from dnspython
#   https://github.com/rthalley/dnspython
#
# Copyright (C) Dnspython Contributors, see LICENSE for text of ISC license

# Copyright (C) 2003-2017 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
"""
Private support for parsing textual addresses.

"""
from __future__ import absolute_import, division, print_function

import binascii
import re
import struct

from gevent.resolver import hostname_types


class AddressSyntaxError(ValueError):
    pass


def _ipv4_inet_aton(text):
    """
    Convert an IPv4 address in text form to binary struct.

    *text*, a ``text``, the IPv4 address in textual form.

    Returns a ``binary``.
    """

    if not isinstance(text, bytes):
        text = text.encode()
    parts = text.split(b'.')
    if len(parts) != 4:
        raise AddressSyntaxError(text)
    for part in parts:
        if not part.isdigit():
            raise AddressSyntaxError
        if len(part) > 1 and part[0] == '0':
            # No leading zeros
            raise AddressSyntaxError(text)
    try:
        ints = [int(part) for part in parts]
        return struct.pack('BBBB', *ints)
    except:
        raise AddressSyntaxError(text)


def _ipv6_inet_aton(text,
                    _v4_ending=re.compile(br'(.*):(\d+\.\d+\.\d+\.\d+)$'),
                    _colon_colon_start=re.compile(br'::.*'),
                    _colon_colon_end=re.compile(br'.*::$')):
    """
    Convert an IPv6 address in text form to binary form.

    *text*, a ``text``, the IPv6 address in textual form.

    Returns a ``binary``.
    """
    # pylint:disable=too-many-branches

    #
    # Our aim here is not something fast; we just want something that works.
    #
    if not isinstance(text, bytes):
        text = text.encode()

    if text == b'::':
        text = b'0::'
    #
    # Get rid of the icky dot-quad syntax if we have it.
    #
    m = _v4_ending.match(text)
    if not m is None:
        b = bytearray(_ipv4_inet_aton(m.group(2)))
        text = (u"{}:{:02x}{:02x}:{:02x}{:02x}".format(m.group(1).decode(),
                                                       b[0], b[1], b[2],
                                                       b[3])).encode()
    #
    # Try to turn '::<whatever>' into ':<whatever>'; if no match try to
    # turn '<whatever>::' into '<whatever>:'
    #
    m = _colon_colon_start.match(text)
    if not m is None:
        text = text[1:]
    else:
        m = _colon_colon_end.match(text)
        if not m is None:
            text = text[:-1]
    #
    # Now canonicalize into 8 chunks of 4 hex digits each
    #
    chunks = text.split(b':')
    l = len(chunks)
    if l > 8:
        raise SyntaxError
    seen_empty = False
    canonical = []
    for c in chunks:
        if c == b'':
            if seen_empty:
                raise AddressSyntaxError(text)
            seen_empty = True
            for _ in range(0, 8 - l + 1):
                canonical.append(b'0000')
        else:
            lc = len(c)
            if lc > 4:
                raise AddressSyntaxError(text)
            if lc != 4:
                c = (b'0' * (4 - lc)) + c
            canonical.append(c)
    if l < 8 and not seen_empty:
        raise AddressSyntaxError(text)
    text = b''.join(canonical)

    #
    # Finally we can go to binary.
    #
    try:
        return binascii.unhexlify(text)
    except (binascii.Error, TypeError):
        raise AddressSyntaxError(text)


def _is_addr(host, parse=_ipv4_inet_aton):
    if not host or not isinstance(host, hostname_types):
        return False

    try:
        parse(host)
    except AddressSyntaxError:
        return False
    else:
        return True

# Return True if host is a valid IPv4 address
is_ipv4_addr = _is_addr


def is_ipv6_addr(host):
    # Return True if host is a valid IPv6 address
    if host and isinstance(host, hostname_types):
        s = '%' if isinstance(host, str) else b'%'
        host = host.split(s, 1)[0]
    return _is_addr(host, _ipv6_inet_aton)
