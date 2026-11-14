# gs1_128.py - functions for handling GS1-128 codes
#
# Copyright (C) 2019 Sergi Almacellas Abellana
# Copyright (C) 2020-2023 Arthur de Jong
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

"""GS1-128 (Standard to encode product information in Code 128 barcodes).

The GS1-128 (also called EAN-128, UCC/EAN-128 or UCC-128) is an international
standard for embedding data such as best before dates, weights, etc. with
Application Identifiers (AI).

The GS1-128 standard is used as a product identification code on bar codes.
It embeds data with Application Identifiers (AI) that defines the kind of
data, the type and length. The standard is also known as UCC/EAN-128, UCC-128
and EAN-128.

GS1-128 is a subset of Code 128 symbology.

More information:

* https://en.wikipedia.org/wiki/GS1-128
* https://www.gs1.org/standards/barcodes/application-identifiers
* https://www.gs1.org/docs/barcodes/GS1_General_Specifications.pdf

>>> compact('(01)38425876095074(17)181119(37)1 ')
'013842587609507417181119371'
>>> encode({'01': '38425876095074'})
'0138425876095074'
>>> info('0138425876095074')
{'01': '38425876095074'}
>>> validate('(17)181119(01)38425876095074(37)1')
'013842587609507417181119371'
"""

import datetime
import decimal
import re

from stdnum import numdb
from stdnum.exceptions import *
from stdnum.util import clean


# our open copy of the application identifier database
_gs1_aidb = numdb.get('gs1_ai')


# Extra validation modules based on the application identifier
_ai_validators = {
    '01': 'stdnum.ean',
    '02': 'stdnum.ean',
    '8007': 'stdnum.iban',
}


def compact(number):
    """Convert the GS1-128 to the minimal representation.

    This strips the number of any valid separators and removes surrounding
    whitespace. For a more consistent compact representation use
    :func:`validate()`.
    """
    return clean(number, '()').strip()


def _encode_value(fmt, _type, value):
    """Encode the specified value given the format and type."""
    if _type == 'decimal':
        if isinstance(value, (list, tuple)) and fmt.startswith('N3+'):
            number = _encode_value(fmt[3:], _type, value[1])
            return number[0] + value[0].rjust(3, '0') + number[1:]
        value = str(value)
        if fmt.startswith('N..'):
            length = int(fmt[3:])
            value = value[:length + 1]
            number, digits = (value.split('.') + [''])[:2]
            digits = digits[:9]
            return str(len(digits)) + number + digits
        else:
            length = int(fmt[1:])
            value = value[:length + 1]
            number, digits = (value.split('.') + [''])[:2]
            digits = digits[:9]
            return str(len(digits)) + (number + digits).rjust(length, '0')
    elif _type == 'date':
        if isinstance(value, (list, tuple)) and fmt == 'N6..12':
            return '%s%s' % (
                _encode_value('N6', _type, value[0]),
                _encode_value('N6', _type, value[1]))
        elif isinstance(value, datetime.date):
            if fmt in ('N6', 'N6..12'):
                return value.strftime('%y%m%d')
            elif fmt == 'N10':
                return value.strftime('%y%m%d%H%M')
            elif fmt in ('N6+N..4', 'N6[+N..4]'):
                value = value.strftime('%y%m%d%H%M')
                if value.endswith('00'):
                    value = value[:-2]
                if value.endswith('00'):
                    value = value[:-2]
                return value
            elif fmt in ('N8+N..4', 'N8[+N..4]'):
                value = value.strftime('%y%m%d%H%M%S')
                if value.endswith('00'):
                    value = value[:-2]
                if value.endswith('00'):
                    value = value[:-2]
                return value
            else:  # pragma: no cover (all formats should be covered)
                raise ValueError('unsupported format: %s' % fmt)
    return str(value)


def _max_length(fmt, _type):
    """Determine the maximum length based on the format ad type."""
    length = sum(int(re.match(r'^[NXY][0-9]*?[.]*([0-9]+)[\[\]]?$', x).group(1)) for x in fmt.split('+'))
    if _type == 'decimal':
        length += 1
    return length


def _pad_value(fmt, _type, value):
    """Pad the value to the maximum length for the format."""
    if _type in ('decimal', 'int'):
        return value.rjust(_max_length(fmt, _type), '0')
    return value.ljust(_max_length(fmt, _type))


def _decode_value(fmt, _type, value):
    """Decode the specified value given the fmt and type."""
    if _type == 'decimal':
        if fmt.startswith('N3+'):
            return (value[1:4], _decode_value(fmt[3:], _type, value[0] + value[4:]))
        digits = int(value[0])
        value = value[1:]
        if digits:
            value = value[:-digits] + '.' + value[-digits:]
        return decimal.Decimal(value)
    elif _type == 'date':
        if len(value) == 6:
            if value[4:] == '00':
                # When day == '00', it must be interpreted as last day of month
                date = datetime.datetime.strptime(value[:4], '%y%m')
                if date.month == 12:
                    date = date.replace(day=31)
                else:
                    date = date.replace(month=date.month + 1, day=1) - datetime.timedelta(days=1)
                return date.date()
            else:
                return datetime.datetime.strptime(value, '%y%m%d').date()
        elif len(value) == 12 and fmt in ('N12', 'N6..12'):
            return (_decode_value('N6', _type, value[:6]), _decode_value('N6', _type, value[6:]))
        else:
            # other lengths are interpreted as variable-length datetime values
            return datetime.datetime.strptime(value, '%y%m%d%H%M%S'[:len(value)])
    elif _type == 'int':
        return int(value)
    return value.strip()


def info(number, separator=''):
    """Return a dictionary containing the information from the GS1-128 code.

    The returned dictionary maps application identifiers to values with the
    appropriate type (`str`, `int`, `Decimal`, `datetime.date` or
    `datetime.datetime`).

    If a `separator` is provided it will be used as FNC1 to determine the end
    of variable-sized values.
    """
    number = compact(number)
    data = {}
    identifier = ''
    # skip separator
    if separator and number.startswith(separator):
        number = number[len(separator):]
    while number:
        # extract the application identifier
        ai, info = _gs1_aidb.info(number)[0]
        if not info or not number.startswith(ai):
            raise InvalidComponent()
        number = number[len(ai):]
        # figure out the value part
        value = number[:_max_length(info['format'], info['type'])]
        if separator and info.get('fnc1', False):
            idx = number.find(separator)
            if idx > 0:
                value = number[:idx]
        number = number[len(value):]
        # validate the value if we have a custom module for it
        if ai in _ai_validators:
            mod = __import__(_ai_validators[ai], globals(), locals(), ['validate'])
            mod.validate(value)
        # convert the number
        data[ai] = _decode_value(info['format'], info['type'], value)
        # skip separator
        if separator and number.startswith(separator):
            number = number[len(separator):]
    return data


def encode(data, separator='', parentheses=False):
    """Generate a GS1-128 for the application identifiers supplied.

    The provided dictionary is expected to map application identifiers to
    values. The supported value types and formats depend on the application
    identifier.

    If a `separator` is provided it will be used as FNC1 representation,
    otherwise variable-sized values will be expanded to their maximum size
    with appropriate padding.

    If `parentheses` is set the application identifiers will be surrounded
    by parentheses for readability.
    """
    ai_fmt = '(%s)' if parentheses else '%s'
    # we keep items sorted and keep fixed-sized values separate tot output
    # them first
    fixed_values = []
    variable_values = []
    for inputai, value in sorted(data.items()):
        ai, info = _gs1_aidb.info(str(inputai))[0]
        if not info:
            raise InvalidComponent()
        # validate the value if we have a custom module for it
        if ai in _ai_validators:
            mod = __import__(_ai_validators[ai], globals(), locals(), ['validate'])
            mod.validate(value)
        value = _encode_value(info['format'], info['type'], value)
        # store variable-sized values separate from fixed-size values
        if info.get('fnc1', False):
            variable_values.append((ai_fmt % ai, info['format'], info['type'], value))
        else:
            fixed_values.append(ai_fmt % ai + value)
    # we need the separator for all but the last variable-sized value
    # (or pad values if we don't have a separator)
    return ''.join(
        fixed_values + [
            ai + (value if separator else _pad_value(fmt, _type, value)) + separator
            for ai, fmt, _type, value in variable_values[:-1]
        ] + [
            ai + value
            for ai, fmt, _type, value in variable_values[-1:]
        ])


def validate(number, separator=''):
    """Check if the number provided is a valid GS1-128.

    This checks formatting of the number and values and returns a stable
    representation.

    If a separator is provided it will be used as FNC1 for both parsing the
    provided number and for encoding the returned number.
    """
    try:
        return encode(info(number, separator), separator)
    except ValidationError:
        raise
    except Exception:  # noqa: B902
        # We wrap all other exceptions to ensure that we only return
        # exceptions that are a subclass of ValidationError
        # (the info() and encode() functions expect some semblance of valid
        # input)
        raise InvalidFormat()


def is_valid(number, separator=''):
    """Check if the number provided is a valid GS1-128."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False
