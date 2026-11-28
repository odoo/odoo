from odoo import api, models

from odoo.addons.l10n_mg.tools.partner_identifiers import (
    MG_ADDITIONAL_IDENTIFIERS_METADATA,
)


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.model
    def _get_all_additional_identifiers_metadata(self) -> dict:
        return {
            **super()._get_all_additional_identifiers_metadata(),
            **MG_ADDITIONAL_IDENTIFIERS_METADATA,
        }

    def _l10n_mg_get_nif(self) -> str | None:
        """NIF of the commercial partner: the dedicated identifier, else the Tax ID that holds it."""
        self.ensure_one()
        partner = self.commercial_partner_id
        return partner._get_additional_identifier("MG_NIF") or partner.vat or None
