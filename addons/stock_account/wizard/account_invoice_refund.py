# -*- coding: utf-8 -*-

from odoo import api, models, fields

class AccountInvoiceRefund(models.TransientModel):
    _inherit = 'account.invoice.refund'

    stock_account_linked_to_shipment = fields.Boolean(string="Linked to Shipment", help="Check to indicate that this refund stock interim accounts.")
    stock_account_anglo_saxon = fields.Boolean(string="Use anglo saxon accounting", help="Whether or not anglo saxon accounting has been activated on the company owning the invoice to refund.")

    @api.model
    def default_get(self, fields):
        rslt = super(AccountInvoiceRefund, self).default_get(fields)
        invoice_id = self.env.context.get('active_id')
        if invoice_id:
            invoice = self.env['account.invoice'].browse(invoice_id)
            rslt['stock_account_linked_to_shipment'] = invoice.anglo_saxon_interim_stock_entries
            rslt['stock_account_anglo_saxon'] = invoice.company_id.anglo_saxon_accounting
        return rslt

    def invoice_refund(self):
        return super(AccountInvoiceRefund, self.with_context(default_anglo_saxon_interim_stock_entries=self.stock_account_linked_to_shipment)).invoice_refund()