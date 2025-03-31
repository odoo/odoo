from odoo import _, models, api


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    @api.model
    def _get_l10n_ke_edi_tremol_warning_moves(self, moves):
        return moves.filtered(lambda m: m.country_code == 'KE' and not m._l10n_ke_fiscal_device_details_filled())

    @api.model
    def _get_l10n_ke_edi_tremol_warning_message(self, warning_moves):
        return '\n'.join([
            _("The following documents have no details related to the fiscal device."),
            *(warning_moves.mapped('name'))
        ])

    # -------------------------------------------------------------------------
    # ALERTS
    # -------------------------------------------------------------------------

    def _get_alerts(self, moves, moves_data):
        # EXTENDS 'account'
        alerts = super()._get_alerts(moves, moves_data)
        if warning_moves := self._get_l10n_ke_edi_tremol_warning_moves(moves):
            alerts['l10n_ke_edi_tremol_warning_moves'] = {
                'message': self._get_l10n_ke_edi_tremol_warning_message(warning_moves),
                'action_text': _("View Invoice(s)"),
                'action': warning_moves._get_records_action(name=_("Check Invoice(s)")),
            }
        return alerts

    # -------------------------------------------------------------------------
    # SENDING METHODS
    # -------------------------------------------------------------------------

    def _hook_invoice_document_before_pdf_report_render(self, invoice, invoice_data):
        # EXTENDS account
        super()._hook_invoice_document_before_pdf_report_render(invoice, invoice_data)
        if invoice.country_code == 'KE' and not invoice._l10n_ke_fiscal_device_details_filled():
            invoice_data['error'] = _(
                "This document does not have details related to the fiscal device, a proforma invoice will be used."
            )
