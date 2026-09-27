# Part of Odoo. See LICENSE file for full copyright and licensing details.
from stdnum.ec import ci as ec_ci

from odoo.tools.translate import LazyTranslate

_lt = LazyTranslate(__name__)

EC_ADDITIONAL_IDENTIFIERS_METADATA = {
    'EC_DNI': {
        'label': _lt('Cédula'),
        'help': _lt('Citizenship card or Identity Card.'),
        'placeholder': '1714616123',
        'category': 'CN',
        'validation_function': ec_ci.validate,
        'countries': ['EC'],
    },
}
