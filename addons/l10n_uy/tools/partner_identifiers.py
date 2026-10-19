# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re

from stdnum.exceptions import InvalidChecksum, InvalidFormat

from odoo.tools.translate import LazyTranslate

_lt = LazyTranslate(__name__)

# Algorithms taken from Uruware's Technical Manual (sections 9.2 and 9.3).
_UY_CI_NIE_VECTOR = (2, 9, 8, 7, 6, 3, 4)


def _uy_ci_nie_validate(value, *, is_nie):
    digits = re.sub(r"[\s.,:-]", "", value)
    if not re.fullmatch(r"\d+", digits):
        raise InvalidFormat()
    verif_digit = int(digits[-1])
    body = digits[1:-1] if is_nie else digits[:-1]
    body = "%07d" % int(body or 0)
    if len(body) > 7:
        raise InvalidFormat()
    num_sum = sum(int(body[i]) * _UY_CI_NIE_VECTOR[i] for i in range(7))
    if -num_sum % 10 != verif_digit:
        raise InvalidChecksum()
    return digits


def uy_ci_validate(value):
    """Validate a Uruguayan Cédula de Identidad number."""
    return _uy_ci_nie_validate(value, is_nie=False)


def uy_nie_validate(value):
    """Validate a Uruguayan NIE (Foreigner Identity Number)."""
    return _uy_ci_nie_validate(value, is_nie=True)


UY_ADDITIONAL_IDENTIFIERS_METADATA = {
    'UY_CI': {
        'label': _lt('CI'),
        'help': _lt('Cédula de Identidad (Uruguayan ID card).'),
        'placeholder': '3:402.010-1',
        'category': 'CN',
        'validation_function': uy_ci_validate,
        'countries': ['UY'],
    },
    'UY_DNI': {
        'label': _lt('DNI'),
        'help': _lt('Documento Nacional de Identidad (AR, BR, CL or PY).'),
        'category': 'CN',
        'countries': ['UY'],
    },
    'UY_NIE': {
        'label': _lt('NIE'),
        'help': _lt('Foreigner Identity Number.'),
        'placeholder': '93:402.010-1',
        'category': 'CN',
        'validation_function': uy_nie_validate,
        'countries': ['UY'],
    },
    'UY_NIFE': {
        'label': _lt('NIFE'),
        'help': _lt('Foreign tax identification number.'),
        'category': 'EN',
        'countries': ['UY'],
    },
    'UY_OTR': {
        'label': _lt('Otros'),
        'help': _lt('Other identification document.'),
        'countries': ['UY'],
    },
}
