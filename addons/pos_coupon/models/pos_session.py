# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.osv.expression import OR
from odoo.addons.point_of_sale.models.pos_session import loader


class PosSession(models.Model):
    _inherit = "pos.session"

    @loader("coupon.program", [])
    def _load_coupon_program(self, lcontext):
        if not self.config_id.program_ids:
            return
        domain = [("id", "in", self.config_id.program_ids.ids), ("active", "=", True)]
        records = self.env[lcontext.model].search(domain).read(lcontext.fields, load=False)
        for record in records:
            lcontext.contents[record["id"]] = record

    def _get_product_product_domain(self):
        result = super(PosSession, self)._get_product_product_domain()
        if not self.config_id.program_ids:
            return result
        discount_product_ids = self.config_id.program_ids.mapped(lambda program: program.discount_line_product_id.id)
        reward_product_ids = self.config_id.program_ids.mapped(lambda program: program.reward_product_id.id)
        product_ids = [id for id in [*discount_product_ids, *reward_product_ids] if id]
        return OR([result, [("id", "in", product_ids)]])
