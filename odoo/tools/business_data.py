from stdnum import get_cc_module
from stdnum.util import clean


def split_vat(vat, default_country_code=''):
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
