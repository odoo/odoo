# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re

from stdnum.exceptions import InvalidFormat

from odoo.tools.translate import LazyTranslate

_lt = LazyTranslate(__name__)


def pl_krs_validate(value):
    """Normalize and validate a Polish KRS number (National Court Register): 10 digits, no checksum."""
    value = re.sub(r'[\s-]', '', value)
    if not re.fullmatch(r'\d{10}', value):
        raise InvalidFormat()
    return value


PL_ADDITIONAL_IDENTIFIERS_METADATA = {
    'PL_KRS': {
        # After PL_VAT (100), so that the NIP stays the preferred legal entity identifier, e.g. in UBL
        'sequence': 200,
        'label': _lt('KRS'),
        'help': _lt('Polish National Court Register (Krajowy Rejestr Sądowy) number.'),
        'placeholder': '0000123456',
        'category': 'EN',
        'validation_function': pl_krs_validate,
        'countries': ['PL'],
    },
}
