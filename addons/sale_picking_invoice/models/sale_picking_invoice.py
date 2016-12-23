# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import models, fields, api

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    sale_invoice_status = fields.Selection(related='sale_id.invoice_status', string="Invoice Status")

    @api.multi
    def action_so_invoice_create(self):
        SaleOrders = self.mapped('sale_id')
        invoice_ids = SaleOrders.action_invoice_create(grouped=True, final=True)
        invoices = self.env['account.invoice'].browse(invoice_ids)
        invoices.signal_workflow('invoice_open')
        if len(invoices) == 1:
            return invoices.invoice_print()
        else:
            return SaleOrders.action_view_invoice()
