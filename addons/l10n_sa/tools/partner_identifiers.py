from odoo.tools.translate import LazyTranslate


_lt = LazyTranslate(__name__)

COMPANY_SCHEMES = {'SA_CRN', 'SA_MOM', 'SA_MLS', 'SA_700', 'SA_SAG', 'SA_OTH'}

SA_ADDITIONAL_IDENTIFIERS_METADATA = {
    'SA_TIN': {
        'placeholder': _lt('3002707692 [Tax identification number]'),
        'help': _lt('Saudi Arabia Tax Identification Number'),
        'label': _lt('Tax Identification Number'),
        'category': 'TIN',
        'countries': ['SA'],
        'sequence': 10,
    },
    'SA_CRN': {
        'placeholder': '1010123456',
        'help': _lt('Saudi Arabia Commercial Registration Number'),
        'label': _lt('Commercial Registration Number'),
        'category': 'EN',
        'countries': ['SA'],
        'sequence': 11,
    },
    'SA_MOM': {
        'placeholder': _lt('MOMRAH License Number'),
        'help': _lt('Saudi Arabia MOMRAH License Number'),
        'label': _lt('MOMRAH License'),
        'countries': ['SA'],
        'sequence': 12,
    },
    'SA_MLS': {
        'placeholder': _lt('MHRSD License Number'),
        'help': _lt('Saudi Arabia MHRSD License Number'),
        'label': _lt('MHRSD License'),
        'countries': ['SA'],
        'sequence': 13,
    },
    'SA_700': {
        'placeholder': '7001234567',
        'help': _lt('Saudi Arabia 700 Number'),
        'label': _lt('700 Number'),
        'countries': ['SA'],
        'sequence': 14,
    },
    'SA_SAG': {
        'placeholder': _lt('MISA License Number'),
        'help': _lt('Saudi Arabia MISA License Number'),
        'label': _lt('MISA License'),
        'countries': ['SA'],
        'sequence': 15,
    },
    'SA_NAT': {
        'placeholder': '1099123456',
        'help': _lt('Saudi Arabia National ID Number'),
        'label': _lt('National ID'),
        'countries': ['SA'],
        'sequence': 16,
    },
    'SA_GCC': {
        'placeholder': _lt('GCC ID Number'),
        'help': _lt('Saudi Arabia GCC ID Number'),
        'label': _lt('GCC ID'),
        'countries': ['SA'],
        'sequence': 17,
    },
    'SA_IQA': {
        'placeholder': _lt('Iqama ID Number'),
        'help': _lt('Saudi Arabia Iqama ID Number'),
        'label': _lt('Iqama Number'),
        'countries': ['SA'],
        'sequence': 18,
    },
    'SA_PAS': {
        'placeholder': 'A00012345',
        'help': _lt('Saudi Arabia Passport ID Number'),
        'label': _lt('Passport ID'),
        'countries': ['SA'],
        'sequence': 19,
    },
    'SA_OTH': {
        'placeholder': _lt('Other ID Number'),
        'help': _lt('Saudi Arabia Other ID Number'),
        'label': _lt('Other ID'),
        'countries': ['SA'],
        'sequence': 20,
    },
}
