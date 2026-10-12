from stdnum.cr import cpf as cr_cpf
from stdnum.cr import cr as cr_cr

from odoo.tools.translate import LazyTranslate

_lt = LazyTranslate(__name__)

CR_ADDITIONAL_IDENTIFIERS_METADATA = {
    'CR_CN': {
        'sequence': 10,
        'label': _lt('Cédula Física'),
        'help': _lt('Costa Rican identity card number for individuals.'),
        'placeholder': '101230456',
        'category': 'CN',
        'validation_function': cr_cpf.validate,
        'countries': ['CR'],
    },
    'CR_DIMEX': {
        'sequence': 20,
        'label': _lt('DIMEX'),
        'help': _lt('Migration identification document for resident foreigners.'),
        'placeholder': '122200341155',
        'category': 'CN',
        'validation_function': cr_cr.validate,
        'countries': ['CR'],
    },
    'CR_NITE': {
        'sequence': 30,
        'label': _lt('NITE'),
        'help': _lt('Special tax identification number for entities without a Cédula Jurídica.'),
        'placeholder': '2000000000',
        'category': 'EN',
        'countries': ['CR'],
    },
    'CR_NOTAXPAYER': {
        'sequence': 110,
        'label': _lt('No Contribuyente'),
        'help': _lt('Unidentified counterparty that is not a taxpayer.'),
        'category': 'CN',
        'countries': ['CR'],
    },
}
