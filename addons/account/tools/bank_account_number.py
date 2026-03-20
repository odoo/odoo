
import re
from odoo.exceptions import ValidationError


def get_bban_from_iban(iban):
    """ Returns the basic bank account number corresponding to an IBAN.
        Note : the BBAN is not the same as the domestic bank account number !
        The relation between IBAN, BBAN and domestic can be found here : http://www.ecbs.org/iban.htm
    """
    return normalize_account_number(iban)[4:]


def get_iban_part(iban, number_kind):
    """ Get part of the iban depending on the mask
        .. code-block:: python
            # template = 'ITkk KBBB BBSS SSSC CCCC CCCC CCC'
            partner.account_number = 'IT60X0542811101000000123456'
            get_iban_part(partner.account_number, 'bank') == '05428'
            get_iban_part(partner.account_number, 'account') == '000000123456'
        Returns ``False`` in case of failure
    """
    iban_part_map = {
        # General
        'bank': 'B',             # Bank national code
        'branch': 'S',           # Branch code
        'account': 'C',          # Account number

        # Checksums
        'check': 'k',            # Check digits
        'check_national': 'K',   # National check digits

        # Custom special
        'account_type': 'T',     # Account type for Bulgaria, Guatemala
        'balance_account': 'A',  # Balance Account Number for Belarus
        'fiscal_code': 'F',      # Tax Identification Number for Iceland (Kennitala)
        'reserved': 'R',         # Zero, reserved for Turkey
    }
    if not (mask_char := iban_part_map.get(number_kind.lower())):
        return False

    iban = normalize_account_number(iban)
    country_code = iban[:2].lower()

    # Removing the country code from both the IBAN and the mask, since it can have some mask chars
    iban_nocc = iban[2:]
    template_nocc = _map_iban_template.get(country_code, '').replace(' ', '')[2:]
    return template_nocc and "".join(c for c, t in zip(iban_nocc, template_nocc) if t == mask_char)


def validate_iban(env, iban):
    iban = normalize_account_number(iban)
    if not iban:
        raise ValidationError(env._("There is no IBAN code."))

    country_code = iban[:2].lower()
    if country_code not in _map_iban_template:
        raise ValidationError(env._("The IBAN is invalid, it should begin with the country code"))

    iban_template = _map_iban_template[country_code]
    if len(iban) != len(iban_template.replace(' ', '')) or not re.fullmatch(r"[a-zA-Z0-9]+", iban):
        raise ValidationError(env._("The IBAN does not seem to be correct. You should have entered something like this %s\n"
                                    "Where B = National bank code, S = Branch code, C = Account No, k = Check digit", iban_template))

    check_chars = iban[4:] + iban[:4]
    digits = int(''.join(str(int(char, 36)) for char in check_chars))  # BASE 36: 0..9,A..Z -> 0..35
    if digits % 97 != 1:
        raise ValidationError(env._("This IBAN does not pass the validation check, please verify it."))

    return iban


def validate_clabe(env, clabe):
    clabe = normalize_account_number(clabe)

    if not isinstance(clabe, str) or len(clabe) != 18 or not clabe.isdigit():
        raise ValidationError(env._("CLABE should be a string of 18 digits."))

    factors = [3, 7, 1]
    total = 0
    for i in range(17):
        digit = int(clabe[i])
        factor = factors[i % 3]
        total += (digit * factor) % 10

    expected = (10 - (total % 10)) % 10
    actual = int(clabe[17])  # checksum

    if expected != actual:
        raise ValidationError(env._("This CLABE does not pass the checksum check, please verify it."))

    return clabe


def normalize_account_number(account_number):
    return re.sub(r'[\W_]', '', account_number or '')


def format_account_number(env, account_number):
    def format_iban(iban):
        return ' '.join([iban[i:i + 4] for i in range(0, len(iban), 4)])

    def format_clabe(clabe):
        return f"{clabe[:3]} {clabe[3:6]} {clabe[6:17]} {clabe[17]}"

    for validator, formatter in (
            (validate_iban, format_iban),
            (validate_clabe, format_clabe),
        ):
        try:
            account_number = validator(env, account_number)
            return formatter(account_number)
        except ValidationError:
            pass
    return account_number


# Map ISO 3166-1 -> IBAN template, as described here :
# http://en.wikipedia.org/wiki/International_Bank_Account_Number#IBAN_formats_by_country
_map_iban_template = {
    'ad': 'ADkk BBBB SSSS CCCC CCCC CCCC',  # Andorra
    'ae': 'AEkk BBBC CCCC CCCC CCCC CCC',  # United Arab Emirates
    'al': 'ALkk BBBS SSSK CCCC CCCC CCCC CCCC',  # Albania
    'at': 'ATkk BBBB BCCC CCCC CCCC',  # Austria
    'az': 'AZkk BBBB CCCC CCCC CCCC CCCC CCCC',  # Azerbaijan
    'ba': 'BAkk BBBS SSCC CCCC CCKK',  # Bosnia and Herzegovina
    'be': 'BEkk BBBC CCCC CCKK',  # Belgium
    'bg': 'BGkk BBBB SSSS TTCC CCCC CC',  # Bulgaria
    'bh': 'BHkk BBBB CCCC CCCC CCCC CC',  # Bahrain
    'br': 'BRkk BBBB BBBB SSSS SCCC CCCC CCCT N',  # Brazil
    'by': 'BYkk BBBB AAAA CCCC CCCC CCCC CCCC',  # Belarus
    'ch': 'CHkk BBBB BCCC CCCC CCCC C',  # Switzerland
    'cr': 'CRkk BBBC CCCC CCCC CCCC CC',  # Costa Rica
    'cy': 'CYkk BBBS SSSS CCCC CCCC CCCC CCCC',  # Cyprus
    'cz': 'CZkk BBBB SSSS SSCC CCCC CCCC',  # Czech Republic
    'de': 'DEkk BBBB BBBB CCCC CCCC CC',  # Germany
    'dk': 'DKkk BBBB CCCC CCCC CC',  # Denmark
    'do': 'DOkk BBBB CCCC CCCC CCCC CCCC CCCC',  # Dominican Republic
    'ee': 'EEkk BBSS CCCC CCCC CCCK',  # Estonia
    'es': 'ESkk BBBB SSSS KKCC CCCC CCCC',  # Spain
    'fi': 'FIkk BBBB BBCC CCCC CK',  # Finland
    'fo': 'FOkk CCCC CCCC CCCC CC',  # Faroe Islands
    'fr': 'FRkk BBBB BSSS SSCC CCCC CCCC CKK',  # France
    'gb': 'GBkk BBBB SSSS SSCC CCCC CC',  # United Kingdom
    'ge': 'GEkk BBCC CCCC CCCC CCCC CC',  # Georgia
    'gi': 'GIkk BBBB CCCC CCCC CCCC CCC',  # Gibraltar
    'gl': 'GLkk BBBB CCCC CCCC CC',  # Greenland
    'gr': 'GRkk BBBS SSSC CCCC CCCC CCCC CCC',  # Greece
    'gt': 'GTkk BBBB MMTT CCCC CCCC CCCC CCCC',  # Guatemala
    'hr': 'HRkk BBBB BBBC CCCC CCCC C',  # Croatia
    'hu': 'HUkk BBBS SSSC CCCC CCCC CCCC CCCC',  # Hungary
    'ie': 'IEkk BBBB SSSS SSCC CCCC CC',  # Ireland
    'il': 'ILkk BBBS SSCC CCCC CCCC CCC',  # Israel
    'is': 'FSkk BBBB SSCC CCCC FFFF FFFF FF',  # Iceland
    'it': 'ITkk KBBB BBSS SSSC CCCC CCCC CCC',  # Italy
    'jo': 'JOkk BBBB SSSS CCCC CCCC CCCC CCCC CC',  # Jordan
    'kw': 'KWkk BBBB CCCC CCCC CCCC CCCC CCCC CC',  # Kuwait
    'kz': 'KZkk BBBC CCCC CCCC CCCC',  # Kazakhstan
    'lb': 'LBkk BBBB CCCC CCCC CCCC CCCC CCCC',  # Lebanon
    'li': 'LIkk BBBB BCCC CCCC CCCC C',  # Liechtenstein
    'lt': 'LTkk BBBB BCCC CCCC CCCC',  # Lithuania
    'lu': 'LUkk BBBC CCCC CCCC CCCC',  # Luxembourg
    'lv': 'LVkk BBBB CCCC CCCC CCCC C',  # Latvia
    'mc': 'MCkk BBBB BSSS SSCC CCCC CCCC CKK',  # Monaco
    'md': 'MDkk BBCC CCCC CCCC CCCC CCCC',  # Moldova
    'me': 'MEkk BBBC CCCC CCCC CCCC KK',  # Montenegro
    'mk': 'MKkk BBBC CCCC CCCC CKK',  # Macedonia
    'mr': 'MRkk BBBB BSSS SSCC CCCC CCCC CKK',  # Mauritania
    'mt': 'MTkk BBBB SSSS SCCC CCCC CCCC CCCC CCC',  # Malta
    'mu': 'MUkk BBBB BBSS CCCC CCCC CCCC CCCC CC',  # Mauritius
    'nl': 'NLkk BBBB CCCC CCCC CC',  # Netherlands
    'no': 'NOkk BBBB CCCC CCK',  # Norway
    'om': 'OMkk BBBC CCCC CCCC CCCC CCC',  # Oman
    'pk': 'PKkk BBBB CCCC CCCC CCCC CCCC',  # Pakistan
    'pl': 'PLkk BBBS SSSK CCCC CCCC CCCC CCCC',  # Poland
    # Palestinian territories: Wikipedia has no 'X's, just uses 'C', Harvard reference does the same.
    'ps': 'PSkk BBBB CCCC CCCC CCCC CCCC CCCC C',  # Palestinian
    'pt': 'PTkk BBBB SSSS CCCC CCCC CCCK K',  # Portugal
    'qa': 'QAkk BBBB CCCC CCCC CCCC CCCC CCCC C',  # Qatar
    'ro': 'ROkk BBBB CCCC CCCC CCCC CCCC',  # Romania
    'rs': 'RSkk BBBC CCCC CCCC CCCC KK',  # Serbia
    'sa': 'SAkk BBCC CCCC CCCC CCCC CCCC',  # Saudi Arabia
    'se': 'SEkk BBBB CCCC CCCC CCCC CCCC',  # Sweden
    'si': 'SIkk BBSS SCCC CCCC CKK',  # Slovenia
    'sk': 'SKkk BBBB SSSS SSCC CCCC CCCC',  # Slovakia
    'sm': 'SMkk KBBB BBSS SSSC CCCC CCCC CCC',  # San Marino
    'tn': 'TNkk BBSS SCCC CCCC CCCC CCCC',  # Tunisia
    'tr': 'TRkk BBBB BRCC CCCC CCCC CCCC CC',  # Turkey
    'ua': 'UAkk BBBB BBCC CCCC CCCC CCCC CCCC C',  # Ukraine
    'vg': 'VGkk BBBB CCCC CCCC CCCC CCCC',  # Virgin Islands
    'xk': 'XKkk BBBB CCCC CCCC CCCC',  # Kosovo
}
