from odoo import api, models, _


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    @api.model
    def _is_gr_edi_applicable(self, move):
        return move.l10n_gr_edi_enable_send_invoices

    def _is_applicable_to_move(self, method, move, **move_data):
        # EXTENDS 'account'
        # For Greek invoices with Peppol in ubl_gr format, prevent sending via Peppol until myDATA mark is received
        res = super()._is_applicable_to_move(method, move, **move_data)
        if not res or method != 'peppol' or move.country_code != 'GR':
            return res
        partner = move.partner_id.commercial_partner_id.with_company(move.company_id)
        invoice_edi_format = move_data.get('invoice_edi_format') or partner._get_peppol_edi_format()
        # Block Peppol for Greek CIUS format if no mark yet
        if invoice_edi_format == 'ubl_gr' and not move.l10n_gr_edi_mark:
            return False
        return res

    def _get_all_extra_edis(self) -> dict:
        # EXTENDS 'account'
        res = super()._get_all_extra_edis()
        res['gr_edi'] = {'label': _("myDATA"), 'is_applicable': self._is_gr_edi_applicable}
        return res

    # -------------------------------------------------------------------------
    # ALERTS
    # -------------------------------------------------------------------------

    def _get_alerts(self, moves, moves_data):
        # EXTENDS 'account'
        alerts = super()._get_alerts(moves, moves_data)
        invoices_with_alert = moves.filtered('l10n_gr_edi_alerts')

        if len(invoices_with_alert) == 1:
            alerts = invoices_with_alert.l10n_gr_edi_alerts
        elif len(invoices_with_alert) > 1:
            alerts['l10n_gr_edi_not_ready_invoice'] = {
                'message': _("The following invoice(s) are not ready to be sent to myDATA: \n%s",
                             '\n'.join(f"- {move.display_name}" for move in invoices_with_alert)),
                'action_text': _("View Invoice(s)"),
                'action': invoices_with_alert._get_records_action(name=_("Check Invoice(s)")),
            }

        # Alert for Greek invoices with Peppol that haven't been sent to myDATA yet
        move_error = moves.filtered(lambda move: (move.country_code == 'GR'
            and 'peppol' in moves_data[move]['sending_methods']
            and moves_data[move]['invoice_edi_format'] == 'ubl_gr'
            and not move.l10n_gr_edi_mark
        ))
        if move_error:
            alerts['l10n_gr_edi_peppol_requires_mydata'] = {
                'message': self.env._("Invoice(s) are not yet sent to myDATA."
                             " First enable myDATA sending, then you can send via Peppol for B2G invoicing."),
                'level': 'warning',
            }
        return alerts

    # -------------------------------------------------------------------------
    # SENDING METHODS
    # -------------------------------------------------------------------------

    def _call_web_service_before_invoice_pdf_render(self, invoices_data):
        # EXTENDS 'account'
        super()._call_web_service_before_invoice_pdf_render(invoices_data)

        invoices = self.env['account.move']
        for invoice, invoice_data in invoices_data.items():
            if 'gr_edi' in invoice_data['extra_edis']:
                invoices |= invoice

        # Send multiple invoice at once (if available) in one batch
        if invoices:
            invoices.l10n_gr_edi_try_send_invoices()

        for invoice, invoice_data in invoices_data.items():
            if invoice in invoices and invoice.l10n_gr_edi_state != 'invoice_sent':
                invoice_data['error'] = {
                    'error_title': _("Error when sending invoice to myDATA"),
                    'errors': [invoice.l10n_gr_edi_document_ids.sorted()[0].message],
                }
