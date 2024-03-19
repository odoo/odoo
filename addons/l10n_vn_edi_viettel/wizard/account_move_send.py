# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import json

from odoo import api, fields, models, SUPERUSER_ID, _


class AccountMoveSend(models.TransientModel):
    _inherit = 'account.move.send'

    l10n_vn_edi_enable = fields.Boolean(
        compute='_compute_l10n_vn_edi_enable',
    )
    l10n_vn_edi_send_checkbox = fields.Boolean(
        compute='_compute_l10n_vn_edi_send_checkbox',
        string='Send to SInvoice',
        readonly=False,
        store=True,
    )
    l10n_vn_edi_generate_file_checkbox = fields.Boolean(
        compute='_compute_l10n_vn_edi_generate_file_checkbox',
        string='Generate SInvoice file',
        readonly=False,
        store=True,
    )

    def _get_wizard_values(self):
        # EXTENDS 'account'
        values = super()._get_wizard_values()
        values['l10n_vn_edi_send'] = self.l10n_vn_edi_send_checkbox
        values['l10n_vn_edi_generate'] = self.l10n_vn_edi_generate_file_checkbox
        return values

    @api.depends('move_ids')
    def _compute_l10n_vn_edi_enable(self):
        for wizard in self:
            wizard.l10n_vn_edi_enable = any(move.l10n_vn_edi_invoice_state == 'ready_to_send' for move in wizard.move_ids)

    @api.depends('l10n_vn_edi_enable')
    def _compute_l10n_vn_edi_generate_file_checkbox(self):
        # E-invoicing is a legal requirement in Vietnam, so we can enable by default.
        for wizard in self:
            wizard.l10n_vn_edi_generate_file_checkbox = wizard.l10n_vn_edi_enable

    @api.depends('l10n_vn_edi_enable')
    def _compute_l10n_vn_edi_send_checkbox(self):
        # E-invoicing is a legal requirement in Vietnam, so we can enable by default.
        for wizard in self:
            wizard.l10n_vn_edi_send_checkbox = wizard.l10n_vn_edi_enable

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
            + move.l10n_vn_edi_sinvoice_file_id
            + move.l10n_vn_edi_sinvoice_xml_file_id
            + move.l10n_vn_edi_sinvoice_pdf_file_id
        )

    @api.model
    def _get_invoice_extra_attachments_data(self, move):
        # EXTENDS 'account'
        vals = super()._get_invoice_extra_attachments_data(move)

        # Ensure that we never send the sinvoice json file by mail, but we still want to allow it to be downloaded.
        for val in vals:
            if val['id'] == move.l10n_vn_edi_sinvoice_file_id.id:
                val['skip_mailing'] = 'true'

        return vals

    @api.depends('l10n_vn_edi_send_checkbox')
    def _compute_mail_attachments_widget(self):
        # EXTENDS 'account' - add depends
        super()._compute_mail_attachments_widget()

    def _needs_sinvoice_placeholder(self):
        # These should only show when sending to sinvoice, since the additional files are downloaded from sinvoice.
        return self.l10n_vn_edi_enable and self.l10n_vn_edi_generate_file_checkbox and self.l10n_vn_edi_send_checkbox

    def _get_placeholder_mail_attachments_data(self, move):
        # EXTENDS 'account'
        results = super()._get_placeholder_mail_attachments_data(move)

        if self.mode == 'invoice_single' and self._needs_sinvoice_placeholder():
            # We display all files besides the json one. The json file will only be downloaded and won't interact with the mail itself.
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

    @api.model
    def _hook_invoice_document_before_pdf_report_render(self, invoice, invoice_data):
        # EXTENDS 'account'
        super()._hook_invoice_document_before_pdf_report_render(invoice, invoice_data)
        self._generate_sinvoice_file_date(invoice, invoice_data)

    @api.model
    def _generate_sinvoice_file_date(self, invoice, invoice_data):
        # Ensure that we still generate the file if 'generate' is ul10n_vn_edi_invoice_transaction_id-checked but send it.
        need_file = invoice_data.get('l10n_vn_edi_generate') or invoice_data.get('l10n_vn_edi_send')
        # In case we already have a json file existing on the invoice, we skip regenerating it.
        if need_file and invoice.l10n_vn_edi_invoice_state == 'ready_to_send' and not invoice.l10n_vn_edi_sinvoice_file:
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

    @api.model
    def _call_web_service_before_invoice_pdf_render(self, invoices_data):
        # EXTENDS 'account'
        super()._call_web_service_before_invoice_pdf_render(invoices_data)
        for invoice, invoice_data in invoices_data.items():
            if invoice_data.get('l10n_vn_edi_send') and invoice.l10n_vn_edi_invoice_state == 'ready_to_send':
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
                        json_data = json.loads(invoice_data['sinvoice_attachments'][0]['raw'].decode('utf-8'))
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
            files_to_attach = [invoice._l10n_vn_edi_fetch_invoice_xml_file_data(), invoice._l10n_vn_edi_fetch_invoice_pdf_file_data()]

            # Not using _link_invoice_documents for these because it depends on _need_invoice_document and I can't get it to work
            # well while allowing users to download the files before sending.
            attachments_data = []
            for file_name, mimetype, file_content, field in files_to_attach:
                attachments_data.append({
                    'name': file_name,
                    'raw': file_content,
                    'mimetype': mimetype,
                    'res_model': invoice._name,
                    'res_id': invoice.id,
                    'res_field': field,  # Binary field
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
