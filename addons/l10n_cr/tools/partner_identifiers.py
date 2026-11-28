from stdnum.cr import cpf as cr_cpf
from stdnum.cr import cr as cr_cr
from stdnum.exceptions import (
    InvalidComponent,
    InvalidFormat,
    InvalidLength,
    ValidationError,
)
from stdnum.util import clean, isdigits

from odoo.tools.translate import LazyTranslate

_lt = LazyTranslate(__name__)

# NITE prefixes (Costa Rica TIN sheet, OECD): foreign individuals without DIMEX, entities without legal personality
NITE_INDIVIDUAL_PREFIX = '3120'
NITE_ENTITY_PREFIX = '3130'


def validate_nite(number):
    """Check a NITE (Numero de Identificacion Tributario Especial): 10 digits, 3-120-XXXXXX or 3-130-XXXXXX."""
    number = clean(number, ' -').strip()
    if len(number) != 10:
        raise InvalidLength()
    if not isdigits(number):
        raise InvalidFormat()
    if number[:4] not in (NITE_INDIVIDUAL_PREFIX, NITE_ENTITY_PREFIX):
        raise InvalidComponent()
    return number


def is_valid_nite(number):
    try:
        return bool(validate_nite(number))
    except ValidationError:
        return False


def get_vat_identifier_key(number):
    """Return the identifier a Costa Rican number held in the VAT field is.

    The VAT field accepts every Costa Rican identification: a Cedula Fisica, a DIMEX, a NITE or a Cedula Juridica.
    """
    for identifier_key, is_valid in (('CR_CN', cr_cpf.is_valid), ('CR_DIMEX', cr_cr.is_valid), ('CR_NITE', is_valid_nite)):
        if is_valid(number):
            return identifier_key
    return 'CR_CPJ'


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
        'help': _lt(
            'Special tax identification number assigned by Hacienda to foreign individuals without DIMEX (3-120) '
            'and to entities without legal personality (3-130).',
        ),
        'placeholder': '3120123456',
        'category': 'EN',
        'validation_function': validate_nite,
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
