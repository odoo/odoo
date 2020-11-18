# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    @api.multi
    def _sale_determine_order(self):
        mapping = super(AccountAnalyticLine, self)._sale_determine_order()
        for analytic_line in self.sudo().filtered(lambda aal: not aal.so_line and aal.product_id and aal.product_id.expense_policy not in [False, 'no']):
            if analytic_line.move_id.expense_id.sale_order_id:
                mapping[analytic_line.id] = analytic_line.move_id.expense_id.sale_order_id
        return mapping

    def _sale_prepare_sale_order_line_values(self, order, price):
        # Add expense quantity to sales order line and update the sales order price because it will be charged to the customer in the end.
        self.ensure_one()
        res = super()._sale_prepare_sale_order_line_values(order, price)
        if self.move_id.expense_id:
            res.update({'product_uom_qty': self.move_id.expense_id.quantity})
        return res
