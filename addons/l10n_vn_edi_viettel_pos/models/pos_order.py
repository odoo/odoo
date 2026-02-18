# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class PosOrder(models.Model):
    _inherit = 'pos.order'

    credit_note_reason = fields.Char(string='Credit Note Reason', copy=False)
    l10n_vn_has_sinvoice_pdf = fields.Boolean(compute="_compute_sinvoice_has_pdf", string="SInvoice PDF Available")
    l10n_vn_sinvoice_state = fields.Selection(related='account_move.l10n_vn_edi_invoice_state')

    @api.depends("account_move.l10n_vn_edi_sinvoice_pdf_file")
    def _compute_sinvoice_has_pdf(self):
        for pos_order in self:
            pos_order.l10n_vn_has_sinvoice_pdf = bool(pos_order.account_move.l10n_vn_edi_sinvoice_pdf_file)

    def _prepare_invoice_vals(self):
        vals = super()._prepare_invoice_vals()

        if self.country_code != 'VN' or not self.config_id.l10n_vn_auto_send_to_sinvoice:
            return vals

        sinvoice_symbol = self.config_id.l10n_vn_pos_symbol or self.config_id.company_id.l10n_vn_pos_default_symbol
        if sinvoice_symbol:
            vals['l10n_vn_edi_invoice_symbol'] = sinvoice_symbol.id

            # Refund Invoice (Credit Note)
            if self.amount_total < 0:
                vals['l10n_vn_edi_adjustment_type'] = '1'  # Money Adjustment

                reason = self.credit_note_reason
                current_ref = vals.get('ref')
                if current_ref and reason:
                    vals['ref'] = f"{current_ref}, {reason}"

        return vals

    def _create_invoice(self, move_vals):
        if self.country_code == 'VN' and self.config_id.l10n_vn_auto_send_to_sinvoice:
            # When auto-sending to SInvoice, we want to skip fetching the SInvoice files
            # right after sending the invoice to reduce the time spent in the POS checkout flow.
            # The SInvoice files will be fetched by printing the invoice from the POS order page
            # or fetched manually in the backend.
            return super()._create_invoice(move_vals).with_context(skip_fetch_sinvoice_files=True)
        return super()._create_invoice(move_vals)
