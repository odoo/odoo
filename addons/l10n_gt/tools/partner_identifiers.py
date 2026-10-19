# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re

from stdnum.exceptions import InvalidChecksum, InvalidFormat

from odoo.tools.translate import LazyTranslate

_lt = LazyTranslate(__name__)

# GT CUI: 9 check-validated chars (8 digits + check digit 0-9/K) plus 0-4 admin digits
GT_CUI_RE = re.compile(r'\d{8}[\dK]\d{0,4}')


def gt_cui_validate(value):
    """Normalize and validate a Guatemalan CUI (Código Único de Identificación)."""
    value = re.sub(r'[\s-]', '', value)
    if not GT_CUI_RE.fullmatch(value):
        raise InvalidFormat()
    cui_sum = sum(int(d) * (i + 2) for i, d in enumerate(value[:8]))
    if value[8] != '0123456789K'[cui_sum % 11]:
        raise InvalidChecksum()
    return value


GT_ADDITIONAL_IDENTIFIERS_METADATA = {
    'GT_CUI': {
        'label': _lt('CUI'),
        'help': _lt('Guatemalan unique identification code.'),
        'placeholder': '1234567890101',
        'category': 'CN',
        'validation_function': gt_cui_validate,
        'countries': ['GT'],
    },
}
