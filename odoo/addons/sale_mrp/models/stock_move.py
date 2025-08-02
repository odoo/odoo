# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _prepare_procurement_values(self):
        res = super()._prepare_procurement_values()
        res['analytic_account_id'] = self.sale_line_id.order_id.analytic_account_id
        if self.sale_line_id.order_id.analytic_account_id:
            res['analytic_distribution'] = {self.sale_line_id.order_id.analytic_account_id.id: 100}
        return res


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    def _compute_sale_price(self):
        kit_lines = self.filtered(lambda move_line: move_line.move_id.bom_line_id.bom_id.type == 'phantom')
        for move_line in kit_lines:
            unit_price = move_line.product_id.list_price
            qty = move_line.product_uom_id._compute_quantity(move_line.quantity, move_line.product_id.uom_id)
            move_line.sale_price = unit_price * qty
        super(StockMoveLine, self - kit_lines)._compute_sale_price()
