# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models

from odoo.addons.l10n_do.tools.partner_identifiers import DO_ADDITIONAL_IDENTIFIERS_METADATA


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def _get_all_additional_identifiers_metadata(self):
        return {**super()._get_all_additional_identifiers_metadata(), **DO_ADDITIONAL_IDENTIFIERS_METADATA}

    def _l10n_do_has_rnc(self):
        """ Whether the partner is identified by an RNC, the only identification
        the DGII accepts on type 31 fiscal documents.
        """
        self.ensure_one()
        return bool(self._get_all_identifiers().get('DO_RNC'))
