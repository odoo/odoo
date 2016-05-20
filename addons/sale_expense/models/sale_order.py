# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.multi
    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        for order in self.filtered(lambda order: not order.project_id):
            if any(line.product_id.can_be_expensed for line in order.order_line):
                order._create_analytic_account()
        return res


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.model
    def create(self, values):
        line = super(SaleOrderLine, self).create(values)
        if line.state == 'sale' and not line.order_id.project_id and line.product_id.can_be_expensed:
            line.order_id._create_analytic_account()
        return line
