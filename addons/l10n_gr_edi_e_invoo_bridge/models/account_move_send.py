import base64

from odoo import api, models
from odoo.addons.l10n_gr_edi_e_invoo_bridge.models.account_move import E_INVOO_TOKEN_NOT_SET
from odoo.addons.l10n_gr_edi_e_invoo_bridge.exceptions import EInvooRequestError


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    @api.model
    def _l10n_gr_edi_try_upload_final_pdf(self, invoice, invoice_data):
        # OVERRIDE 'l10n_gr_edi_e_invoo'
        document = invoice.l10n_gr_edi_document_ids.filtered(
            lambda candidate: (candidate.state == 'invoice_sent' and candidate.provider_invoice_identifier)
        )[:1]

        if not document or document.provider_pdf_state == 'sent':
            return

        parent_token = document._l10n_gr_edi_get_provider_parent_token()
        api_token = invoice.company_id.sudo().l10n_gr_edi_methodoos_api_token

        pdf_values = invoice_data.get('pdf_attachment_values')
        pdf_content = pdf_values and pdf_values.get('raw')

        # Reuse the attached PDF so a failed upload can be retried without regenerating it
        if not pdf_content and invoice.invoice_pdf_report_id:
            pdf_content = invoice.invoice_pdf_report_id.sudo().raw

        if not api_token:
            error_message = str(E_INVOO_TOKEN_NOT_SET)
        elif not pdf_content or not parent_token:
            error_message = self.env._("Missing invoice PDF content or provider parent token.")
        else:
            try:
                result = invoice._l10n_gr_edi_post_e_invoo(
                    api_token,
                    endpoint='save_invoice_fpdf',
                    test_env=invoice.company_id.l10n_gr_edi_test_env,
                    json={
                        'invoice_id': invoice._l10n_gr_edi_get_provider_invoice_id(),
                        'parent_token': parent_token,
                        'pdf_b64': base64.b64encode(pdf_content).decode(),
                    },
                )
                if 200 <= (result.get('upstream_status') or -1) < 300:
                    # In case of success we change the document values and return
                    document.write({
                        'provider_pdf_state': 'sent',
                        'provider_pdf_error': False,
                    })
                    return

                provider_response = result.get('response') or {}
                error_message = provider_response.get('error') or self.env._("The invoice was issued, but the electronic invoicing process could not be completed.")

            except EInvooRequestError as e:
                error_message = str(e)

        document.write({
            'provider_pdf_state': 'error',
            'provider_pdf_error': error_message,
        })
        invoice_data['error'] = {
            'error_title': self.env._("Error when completing electronic invoicing"),
            'errors': [error_message],
        }
