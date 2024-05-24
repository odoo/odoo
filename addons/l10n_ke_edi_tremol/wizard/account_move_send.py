from odoo import _, models, api
from odoo.exceptions import UserError


class AccountMoveSend(models.TransientModel):
    _inherit = 'account.move.send'

    def _get_l10n_ke_edi_tremol_warning_moves(self):
        return self.move_ids.filtered(lambda m: m.country_code == 'KE' and not m._l10n_ke_fiscal_device_details_filled())

    @api.model
    def _get_l10n_ke_edi_tremol_warning_message(self, warning_moves):
        return '\n'.join([
            _("The following documents have no details related to the fiscal device."),
            *(warning_moves.mapped('name'))
        ])

    def _compute_warnings(self):
        # EXTENDS 'account'
        super()._compute_warnings()
        for wizard in self:
            if warning_moves := wizard._get_l10n_ke_edi_tremol_warning_moves():
                wizard.warnings = {
                    **(wizard.warnings or {}),
                    'l10n_ke_edi_tremol_warning_moves': {
                        'message': wizard._get_l10n_ke_edi_tremol_warning_message(warning_moves),
                        'action_text': _("View Invoice(s)"),
                        'action': warning_moves._get_records_action(name=_("Check Invoice(s)")),
                    }
                }

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
        if not allow_fallback_pdf:
            if warning_moves := self._get_l10n_ke_edi_tremol_warning_moves():
                raise UserError(self._get_l10n_ke_edi_tremol_warning_message(warning_moves))
        return super().action_send_and_print(force_synchronous=force_synchronous, allow_fallback_pdf=allow_fallback_pdf, **kwargs)
