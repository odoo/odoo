# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tools.translate import LazyTranslate

_lt = LazyTranslate(__name__)

CO_NIT_DIAN_CODE = '31'
CO_FOREIGN_VAT_DIAN_CODE = '50'  # NIT de otro país
CO_FOREIGN_ID_DIAN_CODE = '42'  # Documento de identificación extranjero

CO_DIAN_CODES = {
    'CO_CC': '13',
    'CO_CE': '22',
    'CO_NIUP': '91',
    'CO_PEP': '47',
    'CO_PPT': '48',
    'CO_RC': '11',
    'CO_TE': '21',
    'CO_TI': '12',
    'PASSPORT': '41',
}

CO_ADDITIONAL_IDENTIFIERS_METADATA = {
    'CO_CC': {
        'label': _lt('Cédula de ciudadanía'),
        'help': _lt('Colombian citizenship ID card (Cédula de ciudadanía).'),
        'category': 'CN',
        'countries': ['CO'],
    },
    'CO_CE': {
        'label': _lt('Cédula de extranjería'),
        'help': _lt('Colombian foreigner ID card (Cédula de extranjería).'),
        'category': 'CN',
        'countries': ['CO'],
    },
    'CO_NIUP': {
        'label': _lt('NIUP'),
        'help': _lt('Número de Identificación Único Personal.'),
        'category': 'CN',
        'countries': ['CO'],
    },
    'CO_PEP': {
        'label': _lt('PEP'),
        'help': _lt('Permiso Especial de Permanencia.'),
        'category': 'CN',
        'countries': ['CO'],
    },
    'CO_PPT': {
        'label': _lt('PPT'),
        'help': _lt('Permiso por Protección Temporal.'),
        'category': 'CN',
        'countries': ['CO'],
    },
    'CO_RC': {
        'label': _lt('Registro Civil'),
        'help': _lt('Colombian civil registration document (Registro Civil).'),
        'category': 'CN',
        'countries': ['CO'],
    },
    'CO_TE': {
        'label': _lt('Tarjeta de extranjería'),
        'help': _lt('Colombian foreigner card (Tarjeta de extranjería).'),
        'category': 'CN',
        'countries': ['CO'],
    },
    'CO_TI': {
        'label': _lt('Tarjeta de Identidad'),
        'help': _lt('Colombian identity card for minors (Tarjeta de Identidad).'),
        'category': 'CN',
        'countries': ['CO'],
    },
}
