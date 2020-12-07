# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.osv.expression import OR


class PosSession(models.Model):
    _inherit = "pos.session"

    def _get_product_product_domain(self):
        result = super(PosSession, self)._get_product_product_domain()
        if not self.config_id.module_pos_discount:
            return result
        return OR([result, [("id", "=", self.config_id.discount_product_id.id)]])
