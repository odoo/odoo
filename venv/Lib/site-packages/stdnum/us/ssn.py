# ssn.py - functions for handling SSNs
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

"""SSN (U.S. Social Security Number).

The Social Security Number is used to identify individuals for taxation
purposes. It is a 9-digit number that consists of a 3-digit area number, a
2-digit group number and a 4-digit serial number. The number does not use a
check digit.

Some validation options are available but with the introduction of Social
Security Number Randomization it is no longer possible to validate using the
High Group History List. Some areas, groups and ranges can be blacklisted
though.

There are several on-line verification facilities available, either for
Employers or at a fee but validation requires more information than just the
number (e.g. name, date of birth, etc). Another means of validation is the
Death Master File which can be ordered on DVD.

More information:

* https://en.wikipedia.org/wiki/Social_Security_number
* https://www.ssa.gov/employer/verifySSN.htm
* https://en.wikipedia.org/wiki/Death_Master_File

>>> validate('536-90-4399')
'536904399'
>>> validate('1112-23333')  # dash in the wrong place
Traceback (most recent call last):
    ...
InvalidFormat: ...
>>> validate('666-00-0000')  # invalid area
Traceback (most recent call last):
    ...
InvalidComponent: ...
>>> validate('078-05-1120')  # blacklisted entry
Traceback (most recent call last):
    ...
InvalidComponent: ...
>>> compact('1234-56-789')
'123456789'
>>> format('111223333')
'111-22-3333'
"""

import re

from stdnum.exceptions import *
from stdnum.util import clean


# regular expression for matching SSN
_ssn_re = re.compile(
    r'^(?P<area>[0-9]{3})-?(?P<group>[0-9]{2})-?(?P<serial>[0-9]{4})$')

# blacklist of SSNs
_ssn_blacklist = set(('078-05-1120', '457-55-5462', '219-09-9999'))


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, '-').strip()


def validate(number):
    """Check if the number is a valid SSN. This checks the length, groups and
    formatting if it is present."""
    match = _ssn_re.search(clean(number, '').strip())
    if not match:
        raise InvalidFormat()
    area = match.group('area')
    group = match.group('group')
    serial = match.group('serial')
    # check for all-0 or some unused areas
    # (9xx also won't be issued which includes the advertising range)
    if area == '000' or area == '666' or area[0] == '9' or \
       group == '00' or serial == '0000':
        raise InvalidComponent()
    # check blacklists
    if format(number) in _ssn_blacklist:
        raise InvalidComponent()
    return compact(number)


def is_valid(number):
    """Check if the number is a valid SSN."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def format(number):
    """Reformat the number to the standard presentation format."""
    if len(number) == 9:
        number = number[:3] + '-' + number[3:5] + '-' + number[5:]
    return number
