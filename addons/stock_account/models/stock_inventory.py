# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class StockInventory(models.Model):
    _inherit = "stock.inventory"

    accounting_date = fields.Date('Force Accounting Date', help="Choose the accounting date at which you want to value the stock moves created by the inventory instead of the default one (the inventory end date)")

    @api.model
    def post_inventory(self, invoice):
        ctx = self.env.context.copy()
        if invoice.accounting_date:
            ctx['force_period_date'] = invoice.accounting_date
        return super(StockInventory, self.with_context(ctx)).post_inventory(invoice)
