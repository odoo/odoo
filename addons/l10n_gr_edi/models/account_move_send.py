import base64

from odoo import api, models, _
from odoo.addons.account_edi_proxy_client.models.account_edi_proxy_user import AccountEdiProxyError


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

    @api.model
    def _l10n_gr_edi_try_upload_final_pdf(self, invoice, invoice_data):
        document = invoice.l10n_gr_edi_document_ids.filtered(
            lambda document: (
                document.state == 'invoice_sent'
                and document.provider_invoice_identifier
            )
        )[:1]

        if not document or document.provider_pdf_state == 'sent':
            return

        parent_token = document._l10n_gr_edi_get_provider_parent_token()
        proxy_user = invoice.company_id._l10n_gr_edi_get_proxy_user()

        pdf_values = invoice_data.get('pdf_attachment_values')
        pdf_content = pdf_values and pdf_values.get('raw')

        # Reuse the attached final PDF so a failed provider upload can be retried without regenerating it
        if not pdf_content and invoice.invoice_pdf_report_id:
            pdf_content = invoice.invoice_pdf_report_id.sudo().raw

        error_message = self.env._(
            "The invoice was issued, but the electronic invoicing process could not be completed. "
            "Please retry Send & Print later."
        )

        upload_succeeded = False
        if pdf_content and parent_token:
            try:
                result = proxy_user._l10n_gr_edi_proxy_request(
                    'save_final_pdf',
                    {
                        'invoice_id': invoice._l10n_gr_edi_get_provider_invoice_id(),
                        'parent_token': parent_token,
                        'pdf_b64': base64.b64encode(pdf_content).decode(),
                    },
                )
            except AccountEdiProxyError as error:
                if error.code in ('invalid_request', 'e_invoo_request_failed') and error.message:
                    error_message = error.message
            else:
                upload_succeeded = 200 <= result.get('upstream_status', -1) < 300

        if upload_succeeded:
            document.write({
                'provider_pdf_state': 'sent',
                'provider_pdf_error': False,
            })
        else:
            document.write({
                'provider_pdf_state': 'error',
                'provider_pdf_error': error_message,
            })
            invoice_data['error'] = {
                'error_title': self.env._("Error when completing electronic invoicing"),
                'errors': [error_message],
            }

    @api.model
    def _call_web_service_after_invoice_pdf_render(self, invoices_data):
        # EXTENDS 'account'
        super()._call_web_service_after_invoice_pdf_render(invoices_data)

        for invoice, invoice_data in invoices_data.items():
            self._l10n_gr_edi_try_upload_final_pdf(invoice, invoice_data)
