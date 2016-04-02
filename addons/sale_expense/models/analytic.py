# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import models


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    def _get_invoice_price(self, order):
        if self.product_id.invoice_policy == 'cost' and self.product_id.expense_policy == 'sales_price':
            return self.product_id.with_context(
                partner=order.partner_id.id,
                date_order=order.date_order,
                pricelist=order.pricelist_id.id,
                uom=self.product_uom_id.id
            ).price
        else:
            return super(AccountAnalyticLine, self)._get_invoice_price(order)
