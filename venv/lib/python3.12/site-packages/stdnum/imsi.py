# imsi.py - functions for handling International Mobile Subscriber Identity
#           (IMSI) numbers
#
# Copyright (C) 2011-2015 Arthur de Jong
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

"""IMSI (International Mobile Subscriber Identity).

The IMSI (International Mobile Subscriber Identity) is used to identify
mobile phone users (the SIM).

>>> validate('429011234567890')
'429011234567890'
>>> validate('439011234567890')  # unknown MCC
Traceback (most recent call last):
    ...
InvalidComponent: ...
>>> split('429011234567890')
('429', '01', '1234567890')
>>> split('310150123456789')
('310', '150', '123456789')
>>> info('460001234567890')['mcc']
'460'
>>> str(info('460001234567890')['country'])
'China'
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the IMSI number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, ' -').strip().upper()


def split(number):
    """Split the specified IMSI into a Mobile Country Code (MCC), a Mobile
    Network Code (MNC), a Mobile Station Identification Number (MSIN)."""
    # clean up number
    number = compact(number)
    # split the number
    from stdnum import numdb
    return tuple(numdb.get('imsi').split(number))


def validate(number):
    """Check if the number provided is a valid IMSI."""
    number = compact(number)
    if not isdigits(number):
        raise InvalidFormat()
    if len(number) not in (14, 15):
        raise InvalidLength()
    if len(split(number)) < 2:
        raise InvalidComponent()  # unknown MCC
    return number


def info(number):
    """Return a dictionary of data about the supplied number."""
    # clean up number
    number = compact(number)
    # split the number
    from stdnum import numdb
    info = dict(number=number)
    mcc_info, mnc_info, msin_info = numdb.get('imsi').info(number)
    info['mcc'] = mcc_info[0]
    info.update(mcc_info[1])
    info['mnc'] = mnc_info[0]
    info.update(mnc_info[1])
    info['msin'] = msin_info[0]
    info.update(msin_info[1])
    return info


def is_valid(number):
    """Check if the number provided is a valid IMSI."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False
