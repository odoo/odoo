# isin.py - functions for handling ISIN numbers
#
# Copyright (C) 2015-2017 Arthur de Jong
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

"""ISIN (International Securities Identification Number).

The ISIN is a 12-character alpha-numerical code specified in ISO 6166 used to
identify exchange listed securities such as bonds, commercial paper, stocks
and warrants. The number is formed of a two-letter country code, a nine
character national security identifier and a single check digit.

This module does not currently separately validate the embedded national
security identifier part (e.g. when it is a CUSIP).

More information:

* https://en.wikipedia.org/wiki/International_Securities_Identification_Number

>>> validate('US0378331005')
'US0378331005'
>>> validate('US0378331003')
Traceback (most recent call last):
    ...
InvalidChecksum: ...
>>> from_natid('gb', 'BYXJL75')
'GB00BYXJL758'
"""

from stdnum.exceptions import *
from stdnum.util import clean


# all valid ISO 3166-1 alpha-2 country codes
_iso_3116_1_country_codes = [
    'AD', 'AE', 'AF', 'AG', 'AI', 'AL', 'AM', 'AN', 'AO', 'AQ', 'AR', 'AS',
    'AT', 'AU', 'AW', 'AX', 'AZ', 'BA', 'BB', 'BD', 'BE', 'BF', 'BG', 'BH',
    'BI', 'BJ', 'BL', 'BM', 'BN', 'BO', 'BQ', 'BR', 'BS', 'BT', 'BV', 'BW',
    'BY', 'BZ', 'CA', 'CC', 'CD', 'CF', 'CG', 'CH', 'CI', 'CK', 'CL', 'CM',
    'CN', 'CO', 'CR', 'CS', 'CU', 'CV', 'CW', 'CX', 'CY', 'CZ', 'DE', 'DJ',
    'DK', 'DM', 'DO', 'DZ', 'EC', 'EE', 'EG', 'EH', 'ER', 'ES', 'ET', 'FI',
    'FJ', 'FK', 'FM', 'FO', 'FR', 'GA', 'GB', 'GD', 'GE', 'GF', 'GG', 'GH',
    'GI', 'GL', 'GM', 'GN', 'GP', 'GQ', 'GR', 'GS', 'GT', 'GU', 'GW', 'GY',
    'HK', 'HM', 'HN', 'HR', 'HT', 'HU', 'ID', 'IE', 'IL', 'IM', 'IN', 'IO',
    'IQ', 'IR', 'IS', 'IT', 'JE', 'JM', 'JO', 'JP', 'KE', 'KG', 'KH', 'KI',
    'KM', 'KN', 'KP', 'KR', 'KW', 'KY', 'KZ', 'LA', 'LB', 'LC', 'LI', 'LK',
    'LR', 'LS', 'LT', 'LU', 'LV', 'LY', 'MA', 'MC', 'MD', 'ME', 'MF', 'MG',
    'MH', 'MK', 'ML', 'MM', 'MN', 'MO', 'MP', 'MQ', 'MR', 'MS', 'MT', 'MU',
    'MV', 'MW', 'MX', 'MY', 'MZ', 'NA', 'NC', 'NE', 'NF', 'NG', 'NI', 'NL',
    'NO', 'NP', 'NR', 'NU', 'NZ', 'OM', 'PA', 'PE', 'PF', 'PG', 'PH', 'PK',
    'PL', 'PM', 'PN', 'PR', 'PS', 'PT', 'PW', 'PY', 'QA', 'RE', 'RO', 'RS',
    'RU', 'RW', 'SA', 'SB', 'SC', 'SD', 'SE', 'SG', 'SH', 'SI', 'SJ', 'SK',
    'SL', 'SM', 'SN', 'SO', 'SR', 'SS', 'ST', 'SV', 'SX', 'SY', 'SZ', 'TC',
    'TD', 'TF', 'TG', 'TH', 'TJ', 'TK', 'TL', 'TM', 'TN', 'TO', 'TR', 'TT',
    'TV', 'TW', 'TZ', 'UA', 'UG', 'UM', 'US', 'UY', 'UZ', 'VA', 'VC', 'VE',
    'VG', 'VI', 'VN', 'VU', 'WF', 'WS', 'YE', 'YT', 'ZA', 'ZM', 'ZW']

# These special code are allowed for ISIN
_country_codes = set(_iso_3116_1_country_codes + [
    'EU',  # European Union
    'QS',  # internally used by Euroclear France
    'QS',  # temporarily assigned in Germany
    'QT',  # internally used in Switzerland
    'XA',  # CUSIP Global Services substitute agencies
    'XB',  # NSD Russia substitute agencies
    'XC',  # WM Datenservice Germany substitute agencies
    'XD',  # SIX Telekurs substitute agencies
    'XF',  # internally assigned, not unique numbers
    'XK',  # temporary country code for Kosovo
    'XS',  # international securities
])

# the letters allowed in an ISIN
_alphabet = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, ' ').strip().upper()


def calc_check_digit(number):
    """Calculate the check digits for the number."""
    # convert to numeric first, then double some, then sum individual digits
    number = ''.join(str(_alphabet.index(n)) for n in number)
    number = ''.join(
        str((2, 1)[i % 2] * int(n)) for i, n in enumerate(reversed(number)))
    return str((10 - sum(int(n) for n in number)) % 10)


def validate(number):
    """Check if the number provided is valid. This checks the length and
    check digit."""
    number = compact(number)
    if not all(x in _alphabet for x in number):
        raise InvalidFormat()
    if len(number) != 12:
        raise InvalidLength()
    if number[:2] not in _country_codes:
        raise InvalidComponent()
    if calc_check_digit(number[:-1]) != number[-1]:
        raise InvalidChecksum()
    return number


def is_valid(number):
    """Check if the number provided is valid. This checks the length and
    check digit."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def from_natid(country_code, number):
    """Generate an ISIN from a national security identifier."""
    number = compact(number)
    number = country_code.upper() + (9 - len(number)) * '0' + number
    return number + calc_check_digit(number)
