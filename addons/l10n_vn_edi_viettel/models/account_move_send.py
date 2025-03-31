# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import json

from odoo import SUPERUSER_ID, _, api, models


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    @api.model
    def _is_vn_edi_applicable(self, move):
        return bool(move.l10n_vn_edi_invoice_state == 'ready_to_send' and move._l10n_vn_edi_get_credentials_company())

    def _get_all_extra_edis(self) -> dict:
        # EXTENDS 'account'
        res = super()._get_all_extra_edis()
        res.update({'vn_sinvoice_send': {'label': _("Send to SInvoice"), 'is_applicable': self._is_vn_edi_applicable}})
        return res

    # -------------------------------------------------------------------------
    # ATTACHMENTS
    # -------------------------------------------------------------------------

    @api.model
    def _get_invoice_extra_attachments(self, move):
        # EXTENDS 'account'
        # we require these to be downloadable for a better UX. It was also said that the xml and pdf files are
        # important files that needs to be shared with the customer.
        return (
            super()._get_invoice_extra_attachments(move)
            + move.l10n_vn_edi_sinvoice_xml_file_id
            + move.l10n_vn_edi_sinvoice_pdf_file_id
        )

    def _get_placeholder_mail_attachments_data(self, move, extra_edis=None):
        # EXTENDS 'account'
        results = super()._get_placeholder_mail_attachments_data(move, extra_edis=extra_edis)
        partner_edi_format = self._get_default_invoice_edi_format(move)
        if partner_edi_format == 'vn_sinvoice' and move._l10n_vn_edi_get_credentials_company():
            results.extend([{
                'id': 'placeholder_sinvoice.pdf',
                'name': f'{move.company_id.vat}-{move.l10n_vn_edi_invoice_symbol.name}101.pdf',
                'mimetype': 'application/pdf',
                'placeholder': True,
            }, {
                'id': 'placeholder_sinvoice.xml',
                'name': f'{move.company_id.vat}-{move.l10n_vn_edi_invoice_symbol.name}101.xml',
                'mimetype': 'application/xml',
                'placeholder': True,
            }])

        return results

    # -------------------------------------------------------------------------
    # SENDING METHODS
    # -------------------------------------------------------------------------

    @api.model
    def _generate_sinvoice_file_date(self, invoice, invoice_data):
        # Ensure that we still generate the file if 'generate' is ul10n_vn_edi_invoice_transaction_id-checked but send it.
        need_file = (
            (invoice_data['invoice_edi_format'] == 'vn_sinvoice' and invoice._l10n_vn_edi_get_credentials_company())
            or 'vn_sinvoice_send' in invoice_data['extra_edis']
        )
        # In case we already have a json file existing on the invoice, we skip regenerating it.
        if need_file and not invoice.l10n_vn_edi_sinvoice_file:
            errors = invoice._l10n_vn_edi_check_invoice_configuration()
            if not errors:
                json_data = invoice._l10n_vn_edi_generate_invoice_json()
                invoice_data['sinvoice_attachments'] = [{
                    'name': f'{invoice.name.replace("/", "_")}_sinvoice.json',
                    'raw': json.dumps(json_data, ensure_ascii=False).encode('utf8'),
                    'mimetype': 'application/json',
                    'res_model': invoice._name,
                    'res_id': invoice.id,
                    'res_field': 'l10n_vn_edi_sinvoice_file',  # Binary field
                }]
            else:
                invoice_data['error'] = {
                    'error_title': _('Error when generating SInvoice file.'),
                    'errors': errors,
                }

    def _hook_invoice_document_before_pdf_report_render(self, invoice, invoice_data):
        # EXTENDS 'account'
        super()._hook_invoice_document_before_pdf_report_render(invoice, invoice_data)
        self._generate_sinvoice_file_date(invoice, invoice_data)

    def _call_web_service_before_invoice_pdf_render(self, invoices_data):
        # EXTENDS 'account'
        super()._call_web_service_before_invoice_pdf_render(invoices_data)
        for invoice, invoice_data in invoices_data.items():
            if 'vn_sinvoice_send' in invoice_data['extra_edis']:
                errors = invoice._l10n_vn_edi_check_invoice_configuration()
                if not errors:
                    if 'sinvoice_attachments' in invoice_data:
                        json_data = json.loads(invoice_data['sinvoice_attachments'][0]['raw'].decode('utf-8'))
                    # If the invoice was downloaded but not sent, the json file could already be there.
                    elif invoice.l10n_vn_edi_sinvoice_file:
                        json_data = json.loads(base64.b64decode(invoice.l10n_vn_edi_sinvoice_file).decode('utf-8'))
                    # If we don't have the file data and the file, we will regenerate it.
                    else:
                        self._generate_sinvoice_file_date(invoice, invoice_data)
                        # In case the above call ended in an error, we skip setting json_data
                        if 'sinvoice_attachments' not in invoice_data:
                            continue
                        json_data = json.loads(invoice_data['sinvoice_attachments'][0]['raw'].decode('utf-8'))
                    if json_data:
                        errors = invoice._l10n_vn_edi_send_invoice(json_data)

                if errors:
                    invoice_data['error'] = {
                        'error_title': _('Error when sending to SInvoice'),
                        'errors': errors,
                    }

                if self._can_commit():
                    self._cr.commit()

    def _call_web_service_after_invoice_pdf_render(self, invoices_data):
        # EXTENDS 'account'
        super()._call_web_service_after_invoice_pdf_render(invoices_data)
        for invoice, invoice_data in invoices_data.items():
            # Handle the json file, and create it if it does not yet exist. This can be done without sending to the EDI.
            json_file_data = [file for file in invoice_data.get('sinvoice_attachments', []) if file['mimetype'] == 'application/json']

            if not invoice.l10n_vn_edi_sinvoice_file and json_file_data:
                self.env['ir.attachment'].with_user(SUPERUSER_ID).create(json_file_data)
                invoice.invalidate_recordset(fnames=[
                    'l10n_vn_edi_sinvoice_file_id',
                    'l10n_vn_edi_sinvoice_file',
                ])

            if invoice.l10n_vn_edi_invoice_state != 'sent':
                continue

            # Download SInvoice documents in order to attach them to the email we sent to the customer.
            # If the email is not being sent, we will still get the files and attach them to the invoice.
            xml_data, xml_error_message = invoice._l10n_vn_edi_fetch_invoice_xml_file_data()
            pdf_data, pdf_error_message = invoice._l10n_vn_edi_fetch_invoice_pdf_file_data()
            if xml_error_message or pdf_error_message:
                invoice_data['error'] = {
                    'error_title': _('Error when receiving SInvoice files.'),
                    'errors': [error_message for error_message in [xml_error_message, pdf_error_message] if error_message],
                }

            # Not using _link_invoice_documents for these because it depends on _need_invoice_document and I can't get it to work
            # well while allowing users to download the files before sending.
            attachments_data = []
            for file, error in [(xml_data, xml_error_message), (pdf_data, pdf_error_message)]:
                if error:
                    continue

                attachments_data.append({
                    'name': file['name'],
                    'raw': file['raw'],
                    'mimetype': file['mimetype'],
                    'res_model': invoice._name,
                    'res_id': invoice.id,
                    'res_field': file['res_field'],  # Binary field
                })

            if attachments_data:
                attachments = self.env['ir.attachment'].with_user(SUPERUSER_ID).create(attachments_data)
                invoice.invalidate_recordset(fnames=[
                    'l10n_vn_edi_sinvoice_xml_file_id',
                    'l10n_vn_edi_sinvoice_xml_file',
                    'l10n_vn_edi_sinvoice_pdf_file_id',
                    'l10n_vn_edi_sinvoice_pdf_file',
                ])

                # Log the new attachment in the chatter for reference. Make sure to add the JSON file.
                invoice.with_context(no_new_invoice=True).message_post(
                    body=_('Invoice sent to SInvoice'),
                    attachment_ids=attachments.ids + invoice.l10n_vn_edi_sinvoice_file_id.ids,
                )

            if self._can_commit():
                self._cr.commit()
