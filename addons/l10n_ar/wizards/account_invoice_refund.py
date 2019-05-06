# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class AccountInvoiceRefund(models.TransientModel):

    _inherit = 'account.invoice.refund'

    @api.multi
    def compute_refund(self, mode='refund'):
        res = super(AccountInvoiceRefund, self).compute_refund(mode=mode)
        if isinstance(res, dict):
            domain = res.get('domain', [])
            refund_invoices = self.env['account.invoice'].search(domain)
            # invoice = self.env['account.invoice'].browse(invoice_ids)
            invoice = self.l10n_ar_invoice_id
            refund_invoices.write({
                # TODO this origin should be set on l10n_latam_document module
                'origin': invoice.l10n_latam_document_number or invoice.number,
                'l10n_ar_afip_service_start': invoice.l10n_ar_afip_service_start,
                'l10n_ar_afip_service_end': invoice.l10n_ar_afip_service_end,
            })
        return res
