# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    expense_ids = fields.Many2many('hr.expense',  string="Expenses")

    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id', 'qty_delivered')
    def _compute_amount(self):
        super(SaleOrderLine, self)._compute_amount()
        for line in self.filtered(lambda l: l.product_id.invoice_policy == 'delivery' and l.expense_ids):
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.qty_delivered, product=line.product_id, partner=line.order_id.partner_shipping_id)
            line.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })
