# -*- coding: utf-8 -*-

from odoo import models


class PosSession(models.Model):
    _inherit = "pos.session"

    def _loader_params_res_company(self):
        res = super()._loader_params_res_company()
        if self.config_id.khmer_receipt:
            res['search_params']['fields'] += ["address_full", "rate_to_khr", "name_khmer", "address_khmer"]
        return res
