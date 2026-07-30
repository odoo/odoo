import base64

from odoo import api, models
from odoo.addons.account_edi_proxy_client.models.account_edi_proxy_user import AccountEdiProxyError


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    @api.model
    def _l10n_gr_edi_try_upload_final_pdf(self, invoice, invoice_data):
        document = invoice.l10n_gr_edi_document_ids.filtered(
            lambda candidate: (
                candidate.state == 'invoice_sent'
                and candidate.provider_invoice_identifier
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

        if not self.env['res.company']._with_locked_records(document, allow_raising=False):
            invoice_data['error'] = {
                'error_title': self.env._("Electronic invoicing is already in progress for this invoice."),
                'errors': [error_message],
                'retry': True,
            }
            return

        # Another worker may have completed the upload before we acquired the lock
        document.invalidate_recordset(['provider_pdf_state', 'provider_pdf_error'])
        if document.provider_pdf_state == 'sent':
            return

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

        # Preserve the PDF upload status if a later send step fails
        if self._can_commit():
            self.env.cr.commit()

    @api.model
    def _call_web_service_after_invoice_pdf_render(self, invoices_data):
        # EXTENDS 'account'
        super()._call_web_service_after_invoice_pdf_render(invoices_data)

        for invoice, invoice_data in invoices_data.items():
            self._l10n_gr_edi_try_upload_final_pdf(invoice, invoice_data)
