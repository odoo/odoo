import re

from odoo.tools.translate import LazyTranslate

_lt = LazyTranslate(__name__)

# The ETA rejects foreign buyer ids longer than 9 characters, despite its schema allowing 30.
FOREIGN_ID_RE = re.compile(r'[A-Za-z0-9]{1,9}')


def _validate_foreign_id(value):
    if not FOREIGN_ID_RE.fullmatch(value):
        raise ValueError
    return value


EG_ADDITIONAL_IDENTIFIERS_METADATA = {
    'EG_FID': {
        'sequence': 20,
        'category': 'CN',
        'label': _lt('Foreign ID'),
        'help': _lt('Identification number of a non-Egyptian individual (e.g a standard 9-character alphanumeric passport number).'),
        'placeholder': 'L898902C',
        'validation_function': _validate_foreign_id,
        'countries': ['EG'],
    },
}
