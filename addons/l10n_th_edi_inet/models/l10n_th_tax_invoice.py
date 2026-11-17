# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class L10nThTaxInvoice(models.Model):
    _name = 'l10n_th.tax.invoice'
    _inherit = ['l10n_th.tax.invoice', 'l10n_th_edi_inet.document']

    l10n_th_edi_state = fields.Selection(compute='_compute_l10n_th_edi_state', store=True)

    @api.depends('state')
    def _compute_l10n_th_edi_state(self):
        for tax_invoice in self:
            if tax_invoice.l10n_th_edi_state in (False, 'ready_to_send', 'error'):
                # A debit note is sent as such, not through its tax invoice.
                tax_invoice.l10n_th_edi_state = (
                    tax_invoice.state == 'posted'
                    and not tax_invoice.invoice_move_id.debit_origin_id
                    and 'ready_to_send'
                )

    def _l10n_th_edi_get_document_values(self):
        self.ensure_one()
        move = self.invoice_move_id
        tax_exigibility = 'on_payment' if self.payment_move_id else 'on_invoice'
        return {
            'move': move,
            'type_code': 'T03' if self.payment_move_id else '388',
            'number': self.tax_invoice_number,
            'date': self.date,
            'partner': move.commercial_partner_id,
            'currency': self.currency_id,
            'base_lines': move._get_th_tax_invoice_base_lines(move._get_exigible_invoice_lines(tax_exigibility)),
            'tax_exigibility': tax_exigibility,
            # A receipt only covers the paid part of the invoice.
            'ratio': self.total_amount / self.total_on_payment_amount if self.payment_move_id else 1.0,
        }

    def _l10n_th_edi_get_pdf_content(self):
        return self.env['ir.actions.report']._render_qweb_pdf('l10n_th.action_report_tax_invoice', self.ids)[0]
