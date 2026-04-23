# Part of Odoo. See LICENSE file for full copyright and licensing details.
from stdnum.cl import rut as cl_rut

from odoo.tools.translate import LazyTranslate

_lt = LazyTranslate(__name__)

CL_ADDITIONAL_IDENTIFIERS_METADATA = {
    'CL_RUN': {
        'label': _lt('RUN'),
        'help': _lt('Chilean national ID number.'),
        'placeholder': '12345678-5',
        'category': 'CN',
        # the RUN and the RUT validate the same according to stdnum
        'validation_function': cl_rut.validate,
        'countries': ['CL'],
    },
}
