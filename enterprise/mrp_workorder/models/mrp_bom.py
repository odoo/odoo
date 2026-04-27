# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class MrpBom(models.Model):
    _name = 'mrp.bom'
    _inherit = ['mail.activity.mixin', 'mrp.bom']

    def write(self, vals):
        res = super().write(vals)
        if 'product_id' in vals or 'product_tmpl_id' in vals:
            self.operation_ids.quality_point_ids._change_product_ids_for_bom(self)
        return res
