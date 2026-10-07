import base64

from odoo import api, models
from odoo.addons.l10n_gr_edi_e_invoo.lib import e_invoo_client


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
        api_token = invoice.company_id.sudo().l10n_gr_edi_methodoos_api_token

        pdf_values = invoice_data.get('pdf_attachment_values')
        pdf_content = pdf_values and pdf_values.get('raw')

        # Reuse the attached final PDF so a failed provider upload can be retried without regenerating it
        if not pdf_content and invoice.invoice_pdf_report_id:
            pdf_content = invoice.invoice_pdf_report_id.sudo().raw

        error_message = self.env._(
            "The invoice was issued, but the electronic invoicing process could not be completed. "
            "Please send it again."
        )

        upload_succeeded = False
        if not api_token:
            error_message = self.env._("The Methodoos API token is not configured. Please configure it in the settings.")
        elif pdf_content and parent_token:
            try:
                result = e_invoo_client.upload_final_pdf(
                    api_token,
                    test_env=invoice.company_id.l10n_gr_edi_test_env,
                    invoice_id=invoice._l10n_gr_edi_get_provider_invoice_id(),
                    parent_token=parent_token,
                    pdf_b64=base64.b64encode(pdf_content).decode(),
                )
            except e_invoo_client.EInvooAuthenticationError:
                error_message = self.env._("The Methodoos API token is invalid. Please check it in the settings.")
            except e_invoo_client.EInvooRequestError:
                pass
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
