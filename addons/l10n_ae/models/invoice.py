# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    # Technical field to show rate on invoice report
    l10n_ae_invoice_rate = fields.Float(compute='_compute_rate', string='Rate on Invoice Date', digits=(12, 6))
    l10n_ae_amount_tax_signed = fields.Monetary(compute='_compute_rate', string='TaxAmount in AED', currency_field='company_currency_id')

    @api.depends('date_invoice', 'amount_tax')
    def _compute_rate(self):
        for invoice in self:
            rate = self.env['res.currency']._get_conversion_rate(invoice.currency_id,
                invoice.company_id.currency_id, invoice.company_id,
                invoice.date_invoice or fields.Date.today()
            )
            invoice.l10n_ae_invoice_rate = rate
            amount_tax_signed = invoice.currency_id._convert(invoice.amount_tax, invoice.company_id.currency_id,
                 invoice.company_id, invoice.date_invoice or fields.Date.today())
            invoice.l10n_ae_amount_tax_signed = amount_tax_signed
