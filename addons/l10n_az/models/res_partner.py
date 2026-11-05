from odoo import api, models
from odoo.tools.translate import LazyTranslate

_lt = LazyTranslate(__name__)

AZ_ADDITIONAL_IDENTIFIERS_METADATA = {
    'AZ_EQF_LOCATION': {
        'label': _lt('EQF Business Location Code'),
        'help': _lt(
            'Code of the business location (branch/object) issuing the electronic invoices (EQF), '
            'as registered with the State Tax Service.'
        ),
        'countries': ['AZ'],
        'synced': False,
    },
}


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def _get_all_additional_identifiers_metadata(self):
        return {**super()._get_all_additional_identifiers_metadata(), **AZ_ADDITIONAL_IDENTIFIERS_METADATA}
