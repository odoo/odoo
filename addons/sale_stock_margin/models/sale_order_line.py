# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.depends('move_ids', 'move_ids.value', 'move_ids.picking_id.state')
    def _compute_purchase_price(self):
        line_ids_to_pass = set()
        for line in self:
            product = line.product_id.with_company(line.company_id)
            if not line.has_valued_move_ids():
                line_ids_to_pass.add(line.id)
            elif line.product_id and line.product_id.categ_id and line.product_id.categ_id.property_cost_method != 'standard':
                # don't overwrite any existing value unless non-standard cost method
                purch_price = sum(line.move_ids.mapped('value'))
                line.purchase_price = line._convert_to_sol_currency(
                    purch_price,
                    product.cost_currency_id,
                )
            elif not line.product_uom_qty and line.qty_delivered:
                # if line added from delivery and standard price, pass to super
                line_ids_to_pass.add(line.id)
        return super(SaleOrderLine, self.browse(line_ids_to_pass))._compute_purchase_price()
