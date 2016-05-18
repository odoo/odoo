# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class change_production_qty(models.TransientModel):
    _inherit = 'change.production.qty'

    @api.model
    def _update_product_to_produce(self, prod, qty):
        Production = self.env['mrp.production']
        for move in prod.move_created_ids:
            if move.product_id == prod.product_id:
                move.write({'product_uom_qty': qty})
            else:
                for sub_product_line in prod.bom_id.sub_products:
                    if sub_product_line.product_id == move.product_id:
                        factor = Production._get_subproduct_factor(move)
                        subproduct_qty = sub_product_line.subproduct_type == 'variable' and qty * factor or sub_product_line.product_qty
                        move.write({'product_uom_qty': subproduct_qty})
