# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.osv.expression import OR


class PosSession(models.Model):
    _inherit = "pos.session"

    def _pos_ui_models_to_load(self):
        result = super()._pos_ui_models_to_load()
        result.append("coupon.program")
        return result

    def _loader_info_coupon_program(self):
        if not self.config_id.program_ids:
            return
        return {'domain': [("id", "in", self.config_id.program_ids.ids), ("active", "=", True)], "fields": []}

    def _get_pos_ui_coupon_program(self, params):
        if params:
            return self.env["coupon.program"].search_read(params["domain"], params["fields"])

    def _loader_info_product_product(self):
        result = super(PosSession, self)._loader_info_product_product()
        if len(self.config_id.program_ids) != 0:
            discount_product_ids = self.config_id.program_ids.mapped(lambda program: program.discount_line_product_id.id)
            reward_product_ids = self.config_id.program_ids.mapped(lambda program: program.reward_product_id.id)
            product_ids = [id for id in [*discount_product_ids, *reward_product_ids] if id]
            result["domain"] = OR([result["domain"], [("id", "in", product_ids)]])
        return result
