# Part of Odoo. See LICENSE file for full copyright and licensing details.
from stdnum.br import cpf as br_cn

from odoo.tools.translate import LazyTranslate

_lt = LazyTranslate(__name__)

BR_ADDITIONAL_IDENTIFIERS_METADATA = {
    'BR_CN': {  # CPF
        'label': _lt('CPF'),
        'placeholder': _lt('390.533.447-05'),
        'help': _lt('Brazilian individual identification number.'),
        'validation_function': br_cn.validate,
        'category': 'CN',
        'countries': ['BR'],
    },
}
