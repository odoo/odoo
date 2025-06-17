from odoo import api, models


class ResCompany(models.Model):
    _inherit = "res.company"

    @api.model
    def _load_pos_data_fields(self, config):
        params = super()._load_pos_data_fields(config)
        if self.env.company.country_id.code == "ES":
            params += ["street", "city", "zip", "l10n_es_simplified_invoice_limit"]
        return params
