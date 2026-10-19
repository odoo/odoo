# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tools.translate import LazyTranslate

_lt = LazyTranslate(__name__)

PA_ADDITIONAL_IDENTIFIERS_METADATA = {
    'PA_CEDULA': {
        'sequence': 2,
        'label': _lt('Cédula'),
        'help': _lt('Panama national identification number for individuals.'),
        'category': 'CN',
        'countries': ['PA'],
    },
}
