# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models

from odoo.addons.l10n_uy.tools.partner_identifiers import UY_ADDITIONAL_IDENTIFIERS_METADATA


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _get_all_additional_identifiers_metadata(self):
        return {**super()._get_all_additional_identifiers_metadata(), **UY_ADDITIONAL_IDENTIFIERS_METADATA}
