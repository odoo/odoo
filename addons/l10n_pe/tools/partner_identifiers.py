# Part of Odoo. See LICENSE file for full copyright and licensing details.
from stdnum.pe import cui as pe_cui

from odoo.tools.translate import LazyTranslate

_lt = LazyTranslate(__name__)

PE_RUC_SUNAT_CODE = '6'
PE_FOREIGN_VAT_SUNAT_CODE = '0'  # Doc. trib. no domiciliado sin RUC
PE_FOREIGN_ID_SUNAT_CODE = '4'  # Carnet de extranjería

# SUNAT identification codes (catálogo 06)
PE_SUNAT_CODES = {
    'PE_CPP': 'H',
    'PE_DIC': 'A',
    'PE_DNI': '1',
    'PE_IDCR': 'B',
    'PE_IN': 'D',
    'PE_NDTD': '0',
    'PE_PTP': 'F',
    'PE_SP': 'G',
    'PE_TAM': 'E',
    'PE_TIN': 'C',
    'PASSPORT': '7',
}

PE_ADDITIONAL_IDENTIFIERS_METADATA = {
    'PE_CPP': {
        'label': _lt('License Permit Temp. Perman.'),
        'help': _lt('Carné Permiso Temp. Perman.'),
        'category': 'CN',
        'countries': ['PE'],
    },
    'PE_DIC': {
        'label': _lt('Diplomatic Identity Card'),
        'help': _lt('Cédula Diplomática de identidad.'),
        'category': 'CN',
        'countries': ['PE'],
    },
    'PE_DNI': {
        'label': _lt('DNI'),
        'help': _lt('National Identity Document.'),
        'placeholder': '40000004',
        'category': 'CN',
        'validation_function': pe_cui.validate,
        'countries': ['PE'],
    },
    'PE_IDCR': {
        'label': _lt('Identity document of the country of residence'),
        'category': 'CN',
        'countries': ['PE'],
    },
    'PE_IN': {
        'label': _lt('Identification Number'),
        'help': _lt('IN - Doc Trib PP. JJ.'),
        'category': 'EN',
        'countries': ['PE'],
    },
    'PE_NDTD': {
        'label': _lt('Non-Domiciled Tax Document'),
        'help': _lt('Document without RUC from another country.'),
        'category': 'EN',
        'countries': ['PE'],
    },
    'PE_PTP': {
        'label': _lt('PTP'),
        'help': _lt('Temporary Residence Permit (Permiso de residencia temporal).'),
        'category': 'CN',
        'countries': ['PE'],
    },
    'PE_SP': {
        'label': _lt('Safe Passage'),
        'help': _lt('Salvoconducto.'),
        'category': 'CN',
        'countries': ['PE'],
    },
    'PE_TAM': {
        'label': _lt('TAM'),
        'help': _lt('Andean Immigration Card.'),
        'category': 'CN',
        'countries': ['PE'],
    },
    'PE_TIN': {
        'label': _lt('Tax Identification Number'),
        'help': _lt('TIN - Doc Trib PP.NN.'),
        'category': 'CN',
        'countries': ['PE'],
    },
}
