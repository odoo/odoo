# mac.py - functions for handling MAC (Ethernet) addresses
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

"""MAC address (Media Access Control address).

A media access control address (MAC address, sometimes Ethernet address) of a
device is meant as a unique identifier within a network at the data link
layer.

More information:

* https://en.wikipedia.org/wiki/MAC_address
* https://en.wikipedia.org/wiki/Organizationally_unique_identifier
* https://standards.ieee.org/faqs/regauth.html#2

>>> validate('D0-50-99-84-A2-A0')
'd0:50:99:84:a2:a0'
>>> to_eui48('d0:50:99:84:a2:a0')
'D0-50-99-84-A2-A0'
>>> is_multicast('d0:50:99:84:a2:a0')
False
>>> str(get_manufacturer('d0:50:99:84:a2:a0'))
'ASRock Incorporation'
>>> get_oui('d0:50:99:84:a2:a0')
'D05099'
>>> get_iab('d0:50:99:84:a2:a0')
'84A2A0'
"""

import re

from stdnum import numdb
from stdnum.exceptions import *
from stdnum.util import clean


_mac_re = re.compile('^([0-9a-f]{2}:){5}[0-9a-f]{2}$')


def compact(number):
    """Convert the MAC address to the minimal, consistent representation."""
    number = clean(number, ' ').strip().lower().replace('-', ':')
    # zero-pad single-digit elements
    return ':'.join('0' + n if len(n) == 1 else n for n in number.split(':'))


def _lookup(number):
    """Look up the manufacturer in the IEEE OUI registry."""
    number = compact(number).replace(':', '').upper()
    info = numdb.get('oui').info(number)
    try:
        return (
            ''.join(n[0] for n in info[:-1]),
            info[-2][1]['o'].replace('%', '"'))
    except IndexError:
        raise InvalidComponent()


def get_manufacturer(number):
    """Look up the manufacturer in the IEEE OUI registry."""
    return _lookup(number)[1]


def get_oui(number):
    """Return the OUI (organization unique ID) part of the address."""
    return _lookup(number)[0]


def get_iab(number):
    """Return the IAB (individual address block) part of the address."""
    number = compact(number).replace(':', '').upper()
    return number[len(get_oui(number)):]


def is_unicast(number):
    """Check whether the number is a unicast address.

    Unicast addresses are received by one node in a network (LAN)."""
    number = compact(number)
    return int(number[:2], 16) & 1 == 0


def is_multicast(number):
    """Check whether the number is a multicast address.

    Multicast addresses are meant to be received by (potentially) multiple
    nodes in a network (LAN)."""
    return not is_unicast(number)


def is_broadcast(number):
    """Check whether the number is the broadcast address.

    Broadcast addresses are meant to be received by all nodes in a network."""
    number = compact(number)
    return number == 'ff:ff:ff:ff:ff:ff'


def is_universally_administered(number):
    """Check if the address is supposed to be assigned by the manufacturer."""
    number = compact(number)
    return int(number[:2], 16) & 2 == 0


def is_locally_administered(number):
    """Check if the address is meant to be configured by an administrator."""
    return not is_universally_administered(number)


def validate(number, validate_manufacturer=None):
    """Check if the number provided is a valid MAC address.

    The existence of the manufacturer is by default only checked for
    universally administered addresses but can be explicitly set with the
    `validate_manufacturer` argument.
    """
    number = compact(number)
    if len(number) != 17:
        raise InvalidLength()
    if not _mac_re.match(number):
        raise InvalidFormat()
    if validate_manufacturer is not False:
        if validate_manufacturer or is_universally_administered(number):
            get_manufacturer(number)
    return number


def is_valid(number, validate_manufacturer=None):
    """Check if the number provided is a valid IBAN."""
    try:
        return bool(validate(number, validate_manufacturer=validate_manufacturer))
    except ValidationError:
        return False


def to_eui48(number):
    """Convert the MAC address to EUI-48 format."""
    return compact(number).upper().replace(':', '-')
