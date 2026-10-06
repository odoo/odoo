# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re

from stdnum.exceptions import InvalidFormat

from odoo.tools.translate import LazyTranslate

_lt = LazyTranslate(__name__)

BD_TIN_RE = re.compile(r'\d{12}')


def bd_tin_validate(value):
    """Normalize and validate a Bangladeshi TIN (12 digits, written 1234-5678-9012)."""
    value = value.replace('-', '').replace(' ', '')
    if not BD_TIN_RE.fullmatch(value):
        raise InvalidFormat()
    return f'{value[:4]}-{value[4:8]}-{value[8:]}'


BD_ADDITIONAL_IDENTIFIERS_METADATA = {
    'BD_TIN': {
        'sequence': 20,
        'label': _lt('TIN'),
        'help': _lt('Bangladeshi Taxpayer Identification Number (e-TIN), 12 digits.'),
        'placeholder': '1234-5678-9012',
        'category': 'TIN',
        'validation_function': bd_tin_validate,
        'countries': ['BD'],
    },
}
