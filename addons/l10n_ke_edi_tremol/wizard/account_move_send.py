from odoo import _, models, fields, api
from odoo.exceptions import UserError


class AccountMoveSend(models.TransientModel):
    _inherit = 'account.move.send'

    l10n_ke_edi_warning_message = fields.Text(compute='_compute_l10n_ke_edi_warning_message')

    @api.depends('move_ids')
    def _compute_l10n_ke_edi_warning_message(self):
        for wizard in self:
            warning_moves = wizard.move_ids.filtered(lambda m: m.country_code == 'KE' and not m._l10n_ke_fiscal_device_details_filled())
            if warning_moves:
                wizard.l10n_ke_edi_warning_message = '\n'.join([
                    _("The following documents have no details related to the fiscal device."),
                    *(warning_moves.mapped('name'))
                ])
            else:
                wizard.l10n_ke_edi_warning_message = False

    def _hook_invoice_document_before_pdf_report_render(self, invoice, invoice_data):
        # EXTENDS account
        super()._hook_invoice_document_before_pdf_report_render(invoice, invoice_data)
        if invoice.country_code == 'KE' and not invoice._l10n_ke_fiscal_device_details_filled():
            invoice_data['error'] = _(
                "This document does not have details related to the fiscal device, a proforma invoice will be used."
            )

    def action_send_and_print(self, force_synchronous=False, allow_fallback_pdf=False, **kwargs):
        # EXTENDS account - prevent Send & Print if KE invoices aren't validated and no fallback is allowed.
        self.ensure_one()
        if not allow_fallback_pdf \
            and any(move.country_code == 'KE' and not move._l10n_ke_fiscal_device_details_filled() for move in self.move_ids):
            raise UserError(self.l10n_ke_edi_warning_message)
        return super().action_send_and_print(force_synchronous=force_synchronous, allow_fallback_pdf=allow_fallback_pdf, **kwargs)
