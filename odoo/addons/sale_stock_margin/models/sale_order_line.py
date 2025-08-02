# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.depends('move_ids', 'move_ids.stock_valuation_layer_ids', 'move_ids.picking_id.state')
    def _compute_purchase_price(self):
        line_ids_to_pass = set()
        for line in self:
            product = line.product_id.with_company(line.company_id)
            if not line.has_valued_move_ids():
                line_ids_to_pass.add(line.id)
            elif (
                # don't overwrite any existing value unless non-standard cost method
                (line.product_id and line.product_id.categ_id.property_cost_method != 'standard') or
                # if line added from delivery, allow recomputation
                (not line.product_uom_qty and line.qty_delivered)
            ):
                purch_price = product._compute_average_price(0, line.product_uom_qty or line.qty_to_invoice, line.move_ids)
                if line.product_uom != product.uom_id:
                    purch_price = product.uom_id._compute_price(purch_price, line.product_uom)
                line.purchase_price = line._convert_to_sol_currency(
                    purch_price,
                    product.cost_currency_id,
                )
        return super(SaleOrderLine, self.browse(line_ids_to_pass))._compute_purchase_price()
