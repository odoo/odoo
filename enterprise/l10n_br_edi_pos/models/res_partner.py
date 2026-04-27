# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, api


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.model
    def _load_pos_data_fields(self, config_id):
        """Override."""
        params = super()._load_pos_data_fields(config_id)
        if self.env.company.country_id.code == "BR":
            params += ["l10n_latam_identification_type_id"]
        return params
