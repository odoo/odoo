from odoo import models


class PosSession(models.Model):
    _inherit = "pos.session"

    def _load_data_params(self, config_id):
        params = super()._load_data_params(config_id)
        if self.config_id.is_spanish:
            params["res.company"]["fields"] += ["street", "city", "zip"]
        return params
