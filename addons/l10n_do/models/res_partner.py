# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models

from odoo.addons.l10n_do.tools.partner_identifiers import DO_ADDITIONAL_IDENTIFIERS_METADATA


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def _get_all_additional_identifiers_metadata(self):
        return {**super()._get_all_additional_identifiers_metadata(), **DO_ADDITIONAL_IDENTIFIERS_METADATA}
