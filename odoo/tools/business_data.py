import re

from stdnum import get_cc_module
from stdnum.util import clean

_ADDRESS_REGEXES = [
    # Same as regex bellow, but match if the building number is at the start of the string
    re.compile(r'''^
        (?P<building_number>[0-9][a-zA-Z0-9/-]*)[,\s]+
        (?P<street>.*?)
        # We want to capture the door number after the last comma of the string, as we could
        # have commas in the street name
        (?:\s*[-,/]\s*(?P<door_number>(?=.*\d)(?:(?!\s*,\s*|\s+-\s+).)+))?
    $''', flags=re.DOTALL | re.VERBOSE),
    # Match addresses where building number is between street name and door number
    re.compile(r'''^
        # Non greedy match on street name, so it will stops as soon as it faces a digit
        (?P<street>.*?)\s*
        # We will use this comma for a condition later
        (?P<comma>,)?\s*
        # Match the building number, it must starts with a digit, and it stops when facing
        # a blank space, a comma or end of string
        (?P<building_number>[0-9][a-zA-Z0-9/-]*)?
        # If we didn't capture a comma in the comma group, we do a positive lookahead to check
        # if we have a door number after
        (?(comma)|(?=\s+[,-/]|\s*$))
        # Door number group has to starts with '-', ',' or '/'
        (?:\s*[-,/]\s*(?P<door_number>(?=.*\d)(?:(?!\s*,\s*|\s+-\s+).)+))?
    ''', flags=re.DOTALL | re.VERBOSE),
]
_REGIONAL_INDICATOR_OFFSET = ord('\N{Regional Indicator Symbol Letter A}') - ord('A')


def split_vat(vat: str, default_country_code: str = '') -> tuple[str, str]:
    """
    Return Country Code and VAT number without country prefix.

    This method is a generic utility that:
    - Accepts a VAT number as input
    - Uses the provided default country code when available.
      Otherwise, extracts the country code from the VAT prefix if present.
    - Uses stdnum when possible for normalization
    - Falls back to simple prefix stripping

    :param vat: VAT number (string)
    :param country_code: ISO country code (string, optional)
    :return: VAT without country prefix (string) and Country Code (String)
    """
    country_code = default_country_code or (vat[:2] if vat and vat[:2].isalpha() else '')
    country_code = country_code.upper()

    if not vat or vat in {'/', 'na', 'NA'}:
        return country_code, ''

    excluded_country_codes = ['CH', 'RO', 'RS', 'SM', 'US']

    # Try stdnum normalization
    if country_code and country_code not in excluded_country_codes:
        # Some countries (e.g., 'SM') are not fully supported by stdnum VAT modules and
        # may fail normalization, so we skip compact and use simple prefix stripping.
        try:
            return country_code, get_cc_module(country_code, 'vat').compact(vat)
        except Exception:  # noqa: BLE001
            pass

    # Normalize VAT (Remove spaces, dots, and hyphens from the VAT number and convert it to uppercase)
    vat = clean(vat, ' .-').upper()

    # Fallback: strip prefix
    if country_code:
        vat = vat.removeprefix(country_code)

    return country_code, vat


def get_flag(country_code: str) -> str:
    """Get the emoji representing the flag linked to the country code.

    This emoji is composed of the two regional indicator emoji of the country code.
    """
    if not re.fullmatch(r'[A-Z]{2}', country_code):
        return ""
    return "".join(chr(_REGIONAL_INDICATOR_OFFSET + ord(c)) for c in country_code)


def mod10r(number: str) -> str:
    """
    Input number: account or invoice number
    Output return: the same number completed with the recursive mod10 key
    """
    codec = [0, 9, 4, 6, 8, 2, 7, 1, 3, 5]
    report = 0
    for digit in number:
        if digit.isdigit():
            report = codec[(int(digit) + report) % 10]
    return number + str((10 - report) % 10)


def street_split(street: str) -> dict[str, str]:
    for regex in _ADDRESS_REGEXES:
        match = regex.match(street or '')
        results = match.groupdict() if match else {}
        if results:
            return {
                'street_name': (results.get('street') or '').strip(),
                'street_number': (results.get('building_number') or '').strip(),
                'street_number2': (results.get('door_number') or '').strip(),
            }

    return {
        'street_name': '',
        'street_number': '',
        'street_number2': '',
    }
