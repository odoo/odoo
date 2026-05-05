from odoo import models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _compute_available_additional_identifiers_metadata(self):
        # Turkey relies on its own national identifiers (Mersis, Trade Registry, Branch...);
        # keep only the Turkish ones and drop the globally-available identifiers (e.g. DUNS).
        super()._compute_available_additional_identifiers_metadata()
        for partner in self:
            metadata = partner.available_additional_identifiers_metadata
            if partner.country_code == 'TR' and metadata:
                partner.available_additional_identifiers_metadata = {
                    key: vals for key, vals in metadata.items()
                    if 'TR' in (vals.get('countries') or [])
                }
