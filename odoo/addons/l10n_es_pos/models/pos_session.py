from odoo import models


class PosSession(models.Model):
    _inherit = "pos.session"

    def _loader_params_res_company(self):
        res = super()._loader_params_res_company()
        if not self.config_id.is_spanish:
            return res
        res["search_params"]["fields"] += ["street", "city", "zip"]
        return res
