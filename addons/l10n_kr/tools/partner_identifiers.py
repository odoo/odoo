import re

from stdnum.exceptions import InvalidFormat

from odoo.tools.translate import LazyTranslate

_lt = LazyTranslate(__name__)

# KR Sub-Business Number: 4-digit
KR_SUB_BUSINESS_NUMBER_RE = re.compile(r'\d{4}')


def kr_sub_business_number_validate(value):
    """Validate a Korean Sub-Business Number (exactly 4 digits)."""
    if not KR_SUB_BUSINESS_NUMBER_RE.fullmatch(value):
        raise InvalidFormat()
    return value


KR_ADDITIONAL_IDENTIFIERS_METADATA = {
    'KR_SUB_BUSINESS_NUMBER': {
        'sequence': 20,
        'label': _lt('Sub-Business Number'),
        'help': _lt("4-digit number the NTS assigns to each sub-business place under business-unit taxation. Not used for the head office or for branches with their own business registration number."),
        'placeholder': '0000',
        'validation_function': kr_sub_business_number_validate,
        'countries': ['KR'],
        'synced': False,
    },
}
