# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    expense_id = fields.Many2one('hr.expense', string='Expense')

    @api.depends('is_expense')
    def _compute_purchase_price(self):
        date_today = fields.Date.context_today(self)
        expense_lines = self.filtered('expense_id')
        for line in expense_lines:
            if line.expense_id.product_has_cost:
                product_cost = line.expense_id.untaxed_amount / line.expense_id.quantity
            else:
                product_cost = line.expense_id.untaxed_amount

            from_currency = line.expense_id.currency_id
            to_currency = line.currency_id or line.order_id.currency_id

            if to_currency and product_cost and from_currency != to_currency:
                line.purchase_price = from_currency._convert(
                    from_amount=product_cost,
                    to_currency=to_currency,
                    company=line.company_id or self.env.company,
                    date=line.order_id.date_order or date_today,
                    round=False)
            else:
                line.purchase_price = product_cost
        return super(SaleOrderLine, self - expense_lines)._compute_purchase_price()
