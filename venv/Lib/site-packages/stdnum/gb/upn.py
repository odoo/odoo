# upn.py - functions for handling English UPNs
#
# Copyright (C) 2017 Arthur de Jong
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

"""UPN (English Unique Pupil Number).

The Unique Pupil Number (UPN) is a 13-character code that identifies pupils
in English state schools and is designed to aid tracking pupil progress
through the school system.

The number consists of a check letter, a 3-digit LA (Local Authority) number
for the issuing school, a 4-digit DfE number (School Establishment Number),
2 digits for the issue year and 3 digits for a serial number. Temporary
numbers have a 2-digit serial and a letter.

More information:

* https://www.gov.uk/government/publications/unique-pupil-numbers

>>> validate('B801200005001')
'B801200005001'
>>> validate('A801200005001')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> validate('X80120000A001')  # middle part must be numeric
Traceback (most recent call last):
    ...
InvalidFormat: ...
>>> validate('E000200005001')  # LA number must be known
Traceback (most recent call last):
    ...
InvalidComponent: ...
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


# The allowed characters in an UPN.
_alphabet = 'ABCDEFGHJKLMNPQRTUVWXYZ0123456789'


# The known values for the LA (Local Authority) number.
# https://www.gov.uk/government/statistics/new-local-authority-codes-january-2011
_la_numbers = set((
    201, 202, 203, 204, 205, 206, 207, 208, 209, 210, 211, 212, 213, 301,
    302, 303, 304, 305, 306, 307, 308, 309, 310, 311, 312, 313, 314, 315,
    316, 317, 318, 319, 320, 330, 331, 332, 333, 334, 335, 336, 340, 341,
    342, 343, 344, 350, 351, 352, 353, 354, 355, 356, 357, 358, 359, 370,
    371, 372, 373, 380, 381, 382, 383, 384, 390, 391, 392, 393, 394, 420,
    800, 801, 802, 803, 805, 806, 807, 808, 810, 811, 812, 813, 815, 816,
    821, 822, 823, 825, 826, 830, 831, 835, 836, 837, 840, 841, 845, 846,
    850, 851, 852, 855, 856, 857, 860, 861, 865, 866, 867, 868, 869, 870,
    871, 872, 873, 874, 876, 877, 878, 879, 880, 881, 882, 883, 884, 885,
    886, 887, 888, 889, 890, 891, 892, 893, 894, 895, 896, 908, 909, 916,
    919, 921, 925, 926, 928, 929, 931, 933, 935, 936, 937, 938))


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, ' ').upper().strip()


def calc_check_digit(number):
    """Calculate the check digit for the number."""
    check = sum(i * _alphabet.index(n)
                for i, n in enumerate(number[-12:], 2)) % 23
    return _alphabet[check]


def validate(number):
    """Check if the number is a valid UPN. This checks length, formatting and
    check digits."""
    number = compact(number)
    if len(number) != 13:
        raise InvalidLength()
    if not isdigits(number[1:-1]) or number[-1] not in _alphabet:
        raise InvalidFormat()
    if int(number[1:4]) not in _la_numbers:
        raise InvalidComponent()
    if calc_check_digit(number[1:]) != number[0]:
        raise InvalidChecksum()
    return number


def is_valid(number):
    """Check if the number is a valid UPN."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False
