# Part of Odoo. See LICENSE file for full copyright and licensing details.
from stdnum.do import cedula as do_cedula

from odoo.tools.translate import LazyTranslate

_lt = LazyTranslate(__name__)

DO_ADDITIONAL_IDENTIFIERS_METADATA = {
    'DO_CEDULA': {
        'label': _lt('Cédula'),
        'help': _lt('Dominican Republic national identification number.'),
        'placeholder': '00113918205',
        'category': 'CN',
        'validation_function': do_cedula.validate,
        'countries': ['DO'],
    },
}
