# exceptions.py - collection of stdnum exceptions
# coding: utf-8
#
# Copyright (C) 2013 Arthur de Jong
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

"""Collection of exceptions.

The validation functions of stdnum should raise one of the below exceptions
when validation of the number fails.
"""


__all__ = ['ValidationError', 'InvalidFormat', 'InvalidChecksum',
           'InvalidLength', 'InvalidComponent']


class ValidationError(Exception):
    """Top-level error for validating numbers.

    This exception should normally not be raised, only subclasses of this
    exception."""

    def __str__(self):
        """Return the exception message."""
        return ''.join(self.args[:1]) or getattr(self, 'message', '')


class InvalidFormat(ValidationError):  # noqa N818
    """Something is wrong with the format of the number.

    This generally means characters or delimiters that are not allowed are
    part of the number or required parts are missing."""

    message = 'The number has an invalid format.'


class InvalidChecksum(ValidationError):  # noqa N818
    """The number's internal checksum or check digit does not match."""

    message = "The number's checksum or check digit is invalid."


class InvalidLength(InvalidFormat):  # noqa N818
    """The length of the number is wrong."""

    message = 'The number has an invalid length.'


class InvalidComponent(ValidationError):  # noqa N818
    """One of the parts of the number has an invalid reference.

    Some part of the number refers to some external entity like a country
    code, a date or a predefined collection of values. The number contains
    some invalid reference."""

    message = 'One of the parts of the number are invalid or unknown.'
