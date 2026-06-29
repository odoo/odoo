# isbn.py - functions for handling ISBNs
#
# Copyright (C) 2010-2017 Arthur de Jong
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

"""ISBN (International Standard Book Number).

The ISBN is the International Standard Book Number, used to identify
publications. An ISBN is used to identify books. Numbers can either have 10
digits (in ISBN-10 format) or 13 digits (in ISBN-13, EAN compatible format).
An ISBN has the following components:

* 3-digit (only in ISBN-13) Bookland code
* 1 to 5-digit group identifier (identifies country or language)
* 1 to 7-digit publisher code
* 1 to 8-digit item number (identifies the book)
* a check digit

More information:

* https://en.wikipedia.org/wiki/International_Standard_Book_Number
* https://www.isbn-international.org/range_file_generation

This module also offers functions for converting to ISBN-13 and formatting
based on how the number should be split into a bookland code, group
identifier, publisher code, item number and check digit.

>>> validate('978-9024538270')
'9789024538270'
>>> validate('978-9024538271')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> compact('1-85798-218-5')
'1857982185'
>>> format('9780471117094')
'978-0-471-11709-4'
>>> format('1857982185')
'1-85798-218-5'
>>> isbn_type('1-85798-218-5')
'ISBN10'
>>> isbn_type('978-0-471-11709-4')
'ISBN13'
>>> to_isbn13('1-85798-218-5')
'978-1-85798-218-3'
>>> to_isbn10('978-1-85798-218-3')
'1-85798-218-5'
"""

from stdnum import ean
from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number, convert=False):
    """Convert the ISBN to the minimal representation. This strips the number
    of any valid ISBN separators and removes surrounding whitespace. If the
    convert parameter is True the number is also converted to ISBN-13
    format."""
    number = clean(number, ' -').strip().upper()
    if len(number) == 9:
        number = '0' + number
    if convert:
        return to_isbn13(number)
    return number


def _calc_isbn10_check_digit(number):
    """Calculate the ISBN check digit for 10-digit numbers. The number passed
    should not have the check digit included."""
    check = sum((i + 1) * int(n)
                for i, n in enumerate(number)) % 11
    return 'X' if check == 10 else str(check)


def validate(number, convert=False):
    """Check if the number provided is a valid ISBN (either a legacy 10-digit
    one or a 13-digit one). This checks the length and the check digit but does
    not check if the group and publisher are valid (use split() for that)."""
    number = compact(number, convert=False)
    if not isdigits(number[:-1]):
        raise InvalidFormat()
    if len(number) == 10:
        if _calc_isbn10_check_digit(number[:-1]) != number[-1]:
            raise InvalidChecksum()
    elif len(number) == 13:
        ean.validate(number)
        if number[:3] not in ('978', '979'):
            raise InvalidComponent()
    else:
        raise InvalidLength()
    if convert:
        number = to_isbn13(number)
    return number


def isbn_type(number):
    """Check the passed number and return 'ISBN13', 'ISBN10' or None (for
    invalid) for checking the type of number passed."""
    try:
        number = validate(number, convert=False)
    except ValidationError:
        return None
    if len(number) == 10:
        return 'ISBN10'
    else:  # len(number) == 13:
        return 'ISBN13'


def is_valid(number):
    """Check if the number provided is a valid ISBN (either a legacy 10-digit
    one or a 13-digit one). This checks the length and the check digit but does
    not check if the group and publisher are valid (use split() for that)."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def to_isbn13(number):
    """Convert the number to ISBN-13 format."""
    number = number.strip()
    min_number = clean(number, ' -')
    if len(min_number) == 13:
        return number  # nothing to do, already ISBN-13
    if len(min_number) == 9:
        number = '0' + number  # convert from 9 to 10 digits
    # put new check digit in place
    number = number[:-1] + ean.calc_check_digit('978' + min_number[:-1])
    # add prefix
    if ' ' in number:
        return '978 ' + number
    elif '-' in number:
        return '978-' + number
    else:
        return '978' + number


def to_isbn10(number):
    """Convert the number to ISBN-10 format."""
    number = number.strip()
    min_number = compact(number, convert=False)
    if len(min_number) == 10:
        return number  # nothing to do, already ISBN-10
    elif isbn_type(min_number) != 'ISBN13':
        raise InvalidFormat('Not a valid ISBN13.')
    elif not number.startswith('978'):
        raise InvalidComponent('Does not use 978 Bookland prefix.')
    # strip EAN prefix
    number = number[3:-1].strip().strip('-')
    digit = _calc_isbn10_check_digit(min_number[3:-1])
    # append the new check digit
    if ' ' in number:
        return number + ' ' + digit
    elif '-' in number:
        return number + '-' + digit
    else:
        return number + digit


def split(number, convert=False):
    """Split the specified ISBN into an EAN.UCC prefix, a group prefix, a
    registrant, an item number and a check digit. If the number is in ISBN-10
    format the returned EAN.UCC prefix is '978'. If the convert parameter is
    True the number is converted to ISBN-13 format first."""
    # clean up number
    number = compact(number, convert)
    # get Bookland prefix if any
    delprefix = False
    if len(number) == 10:
        number = '978' + number
        delprefix = True
    # split the number
    from stdnum import numdb
    result = numdb.get('isbn').split(number[:-1])
    itemnr = result.pop() if result else ''
    prefix = result.pop(0) if result else ''
    group = result.pop(0) if result else ''
    publisher = result.pop(0) if result else ''
    # return results
    return ('' if delprefix else prefix, group, publisher, itemnr, number[-1])


def format(number, separator='-', convert=False):
    """Reformat the number to the standard presentation format with the
    EAN.UCC prefix (if any), the group prefix, the registrant, the item
    number and the check digit separated (if possible) by the specified
    separator. Passing an empty separator should equal compact() though this
    is less efficient. If the convert parameter is True the number is
    converted to ISBN-13 format first."""
    return separator.join(x for x in split(number, convert) if x)
