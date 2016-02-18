# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from openerp import api, models


class ChangeProductionQty(models.TransientModel):
    _inherit = 'change.production.qty'

    @api.model
    def _update_product_to_produce(self, production, qty):
        for move in production.move_created_ids:
            if move.product_id == production.product_id:
                move.write({'product_uom_qty': qty})
                continue
            for sub_product_line in production.bom_id.subproduct_ids.filtered(lambda line: line.product_id.id == move.product_id.id):
                factor = production._get_subproduct_factor(move)
                subproduct_qty = sub_product_line.subproduct_type == 'variable' and qty *\
                    factor or sub_product_line.product_qty
                move.write({'product_uom_qty': subproduct_qty})
