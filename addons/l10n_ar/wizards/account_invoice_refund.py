# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class AccountInvoiceRefund(models.TransientModel):

    _inherit = 'account.invoice.refund'

    @api.multi
    def compute_refund(self, mode='refund'):
        # TODO when moving to master check if we could fix modify option
        res = super().compute_refund(mode=mode)
        if isinstance(res, dict) and self.refund_only != 'modify':
            domain = res.get('domain', [])
            refund_invoices = self.env['account.invoice'].search(domain)
            invoice = self.l10n_latam_invoice_id
            # TODO we should set same currency_rate as original invoice
            refund_invoices.write({'origin': invoice.number,
                                   'l10n_ar_afip_service_start': invoice.l10n_ar_afip_service_start,
                                   'l10n_ar_afip_service_end': invoice.l10n_ar_afip_service_end})
        return res
