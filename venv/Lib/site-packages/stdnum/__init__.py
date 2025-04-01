# __init__.py - main module
# coding: utf-8
#
# Copyright (C) 2010-2021 Arthur de Jong
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

"""Parse, validate and reformat standard numbers and codes.

This library offers functions for parsing, validating and reformatting
standard numbers and codes in various formats.

All modules implement a common interface:

>>> from stdnum import isbn
>>> isbn.validate('978-9024538270')
'9789024538270'
>>> isbn.validate('978-9024538271')
Traceback (most recent call last):
    ...
InvalidChecksum: ...

Apart from the validate() function, many modules provide extra
parsing, validation, formatting or conversion functions.
"""

from stdnum.util import get_cc_module


__all__ = ('get_cc_module', '__version__')

# the version number of the library
__version__ = '1.16'
