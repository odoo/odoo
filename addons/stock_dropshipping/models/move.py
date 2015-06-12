# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import models, api


class StockMove(models.Model):
    _inherit = "stock.move"

    @api.model
    def _create_invoice_line_from_vals(self, move, invoice_line_vals, inv_type):
        invoice_line_id = super(StockMove, self)._create_invoice_line_from_vals(move, invoice_line_vals, inv_type)

        purchase_line = move.purchase_line_id
        sale_line = move.procurement_id.sale_line_id

        if purchase_line and sale_line:
            invoice_id = invoice_line_vals['invoice_id']
            invoice = self.env['account.invoice'].browse(invoice_id)

            if invoice.type in ('out_invoice', 'out_refund'):
                # detach the customer invoice from the purchase
                purchase_line.invoice_lines = [(3, invoice_line_id)]
                purchase_line.order_id.invoice_ids = [(3, invoice_id)]
            else:
                # detach the supplier invoice from the sale
                sale_line.invoice_lines = [(3, invoice_line_id)]
                sale_line.order_id.invoice_ids = [(3, invoice_id)]

        return invoice_line_id

    @api.model
    def _get_master_data(self, move, company, inv_type):
        partner, uid, currency = super(StockMove, self)._get_master_data(move, company, inv_type)
        new_partner_id = self.env.context.get('partner_to_invoice_id')
        if new_partner_id:
            partner = self.env['res.partner'].browse(new_partner_id)
        return partner, uid, currency
