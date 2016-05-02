# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import osv


class change_production_qty(osv.osv_memory):
    _inherit = 'change.production.qty'

    def _update_product_to_produce(self, cr, uid, prod, qty, context=None):
        move_lines_obj = self.pool.get('stock.move')
        prod_obj = self.pool.get('mrp.production')
        for m in prod.move_created_ids:
            if m.product_id.id == prod.product_id.id:
                move_lines_obj.write(cr, uid, [m.id], {'product_uom_qty': qty})
            else:
                for sub_product_line in prod.bom_id.sub_products:
                    if sub_product_line.product_id.id == m.product_id.id:
                        factor = prod_obj._get_subproduct_factor(cr, uid, m, context=context)
                        subproduct_qty = sub_product_line.subproduct_type == 'variable' and qty * factor or sub_product_line.product_qty
                        move_lines_obj.write(cr, uid, [m.id], {'product_uom_qty': subproduct_qty})