# isan.py - functions for handling International Standard Audiovisual Numbers
#           (ISANs)
#
# Copyright (C) 2010, 2011, 2012, 2013 Arthur de Jong
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

"""ISAN (International Standard Audiovisual Number).

The ISAN (International Standard Audiovisual Number) is used to identify
audiovisual works.

The number is hexadecimal and can consists of at least a root identifier,
and an episode or part. After that an optional check digit, optional
version and optionally another check digit can be provided. The check
digits are validated using the ISO 7064 Mod 37, 36 algorithm.

>>> validate('000000018947000000000000')
'000000018947000000000000'
>>> compact('0000-0000-D07A-0090-Q-0000-0000-X')
'00000000D07A009000000000'
>>> validate('0000-0001-8CFA-0000-I-0000-0000-K')
'000000018CFA0000I00000000K'
>>> validate('0000-0001-8CFA-0000-A-0000-0000-K')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> format('000000018947000000000000')
'0000-0001-8947-0000-8-0000-0000-D'

>>> to_urn('00000000D07A009000000000')
'URN:ISAN:0000-0000-D07A-0090-Q-0000-0000-X'
>>> to_xml('1881-66C7-3420-6541-Y-9F3A-0245-O')
'<ISAN root="1881-66C7-3420" episode="6541" version="9F3A-0245" />'
"""

from stdnum.exceptions import *
from stdnum.iso7064 import mod_37_36
from stdnum.util import clean


def split(number):
    """Split the number into a root, an episode or part, a check digit a
    version and another check digit. If any of the parts are missing an empty
    string is returned."""
    number = clean(number, ' -').strip().upper()
    if len(number) == 17 or len(number) == 26:
        return number[0:12], number[12:16], number[16], number[17:25], number[25:]
    elif len(number) > 16:
        return number[0:12], number[12:16], '', number[16:24], number[24:]
    else:
        return number[0:12], number[12:16], number[16:], '', ''


def compact(number, strip_check_digits=True):
    """Convert the ISAN to the minimal representation. This strips the number
    of any valid separators and removes surrounding whitespace. The check
    digits are removed by default."""
    number = list(split(number))
    if strip_check_digits:
        number[2] = number[4] = ''
    return ''.join(number)


def validate(number, strip_check_digits=False, add_check_digits=False):
    """Check if the number provided is a valid ISAN. If check digits are
    present in the number they are validated. If strip_check_digits is True
    any existing check digits will be removed (after checking). If
    add_check_digits is True the check digit will be added if they are not
    present yet."""
    (root, episode, check1, version, check2) = split(number)
    # check digits used
    for x in root + episode + version:
        if x not in '0123456789ABCDEF':
            raise InvalidFormat()
    # check length of all components
    if len(root) != 12 or len(episode) != 4 or len(check1) not in (0, 1) or \
       len(version) not in (0, 8) or len(check1) not in (0, 1):
        raise InvalidLength()
    # allow removing check digits
    if strip_check_digits:
        check1 = check2 = ''
    # check check digits
    if check1:
        mod_37_36.validate(root + episode + check1)
    if check2:
        mod_37_36.validate(root + episode + version + check2)
    # add check digits
    if add_check_digits and not check1:
        check1 = mod_37_36.calc_check_digit(root + episode)
    if add_check_digits and not check2 and version:
        check2 = mod_37_36.calc_check_digit(root + episode + version)
    return root + episode + check1 + version + check2


def is_valid(number):
    """Check if the number provided is a valid ISAN. If check digits are
    present in the number they are validated."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number, separator='-', strip_check_digits=False, add_check_digits=True):
    """Reformat the number to the standard presentation format. If
    add_check_digits is True the check digit will be added if they are not
    present yet. If both strip_check_digits and add_check_digits are True the
    check digits will be recalculated."""
    (root, episode, check1, version, check2) = split(number)
    if strip_check_digits:
        check1 = check2 = ''
    if add_check_digits and not check1:
        check1 = mod_37_36.calc_check_digit(root + episode)
    if add_check_digits and not check2 and version:
        check2 = mod_37_36.calc_check_digit(root + episode + version)
    number = [root[i:i + 4] for i in range(0, 12, 4)] + [episode]
    if check1:
        number.append(check1)
    if version:
        number.extend((version[0:4], version[4:]))
    if check2:
        number.append(check2)
    return separator.join(number)


def to_binary(number):
    """Convert the number to its binary representation (without the check
    digits)."""
    from binascii import a2b_hex
    return a2b_hex(compact(number, strip_check_digits=True))


def to_xml(number):
    """Return the XML form of the ISAN as a string."""
    number = format(number, strip_check_digits=True, add_check_digits=False)
    return '<ISAN root="%s" episode="%s" version="%s" />' % (
        number[0:14], number[15:19], number[20:])


def to_urn(number):
    """Return the URN representation of the ISAN."""
    return 'URN:ISAN:' + format(number, add_check_digits=True)
