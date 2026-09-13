import base64
import json

from odoo import SUPERUSER_ID, api, models


class AccountMoveSend(models.AbstractModel):
    _inherit = "account.move.send"

    @api.model
    def _is_pajakio_edi_applicable(self, move):
        return (
            move.move_type == "out_invoice"
            and move.state == "posted"
            and move.company_id.account_fiscal_country_id.code == 'ID'
            and move.company_id.l10n_id_pajakio_active
            and (not move.l10n_id_coretax_document or move.l10n_id_coretax_document.document_type == 'pajakio')
            and move.l10n_id_coretax_document.l10n_id_pajakio_status in (False, 'rejected')
        )

    def _get_all_extra_edis(self):
        # EXTENDS 'account'
        res = super()._get_all_extra_edis()
        res.update({
            'id_pajakio': {
                'label': 'Send to Pajak.io',
                'is_applicable': self._is_pajakio_edi_applicable,
            },
        })
        return res

    @api.model
    def _hook_invoice_document_before_pdf_report_render(self, invoice, invoice_data):
        # EXTEND 'account'
        super()._hook_invoice_document_before_pdf_report_render(invoice, invoice_data)
        self._l10n_id_pajakio_generate_json(invoice, invoice_data)

    def _l10n_id_pajakio_generate_json(self, invoice, invoice_data):
        """ Generate an attachment containing JSON data that will be used when sending invoice data to Pajak.io """
        if 'id_pajakio' not in invoice_data['extra_edis']:
            return
        json_content = invoice._l10n_id_pajakio_prepare_invoice_payload()
        invoice_data['pajakio_attachments'] = {
            'name': f'{invoice.name}_pajakio_request.json',
            'raw': json.dumps(json_content),
            'mimetype': 'application/json',
            'res_model': invoice.l10n_id_coretax_document._name,
            'res_id': invoice.l10n_id_coretax_document.id,
            'res_field': 'l10n_id_pajakio_file',
        }

    @api.model
    def _call_web_service_before_invoice_pdf_render(self, invoices_data):
        # EXTENDS 'account'
        super()._call_web_service_before_invoice_pdf_render(invoices_data)

        pajakio_invoices = self.env['account.move']
        payload_map = {}  # l10n_id_efaktur_coretax.document -> json payload
        for invoice, invoice_data in invoices_data.items():
            if 'id_pajakio' not in invoice_data['extra_edis']:
                continue

            # load JSON payload from existing attachment/create in the spot if needed
            if 'pajakio_attachments' in invoice_data:
                json_content = json.loads(invoice_data['pajakio_attachments']['raw'])
            elif invoice.l10n_id_coretax_document.l10n_id_pajakio_file:
                json_content = json.loads(base64.b64decode(invoice.l10n_id_coretax_document.l10n_id_pajakio_file))
            else:
                self._l10n_id_pajakio_generate_json(invoice, invoice_data)
                json_content = json.loads(invoice_data['pajakio_attachments']['raw'])

            payload_map[invoice.l10n_id_coretax_document] = json_content
            pajakio_invoices |= invoice

        # batch invoices per company and send them to Pajak.io via IAP
        for company_invoices in pajakio_invoices.grouped('company_id').values():
            company_documents = company_invoices.l10n_id_coretax_document
            if errors := company_documents._l10n_id_pajakio_send_multi(payload_map):
                for document, error in errors.items():
                    invoices_data[document.invoice_ids]['error'] = {
                        'error_title': self.env._('Error when sending to Pajak.io'),
                        'errors': [error],
                    }

            if self._can_commit():
                self.env.cr.commit()

    def _call_web_service_after_invoice_pdf_render(self, invoices_data):
        # EXTENDS 'account'
        # Update status of pajak.io, one IAP call per company covering every invoice sent in this batch
        super()._call_web_service_after_invoice_pdf_render(invoices_data)

        pajakio_invoices = self.env['account.move']
        for invoice, invoice_data in invoices_data.items():
            if 'id_pajakio' in invoice_data['extra_edis']:
                pajakio_invoices |= invoice

        for company_invoices in pajakio_invoices.grouped('company_id').values():
            documents = company_invoices.l10n_id_coretax_document
            if errors := documents._l10n_id_pajakio_update_status():
                for invoice in company_invoices:
                    invoices_data[invoice]["error"] = {
                        "error_title": self.env._("Error when getting invoice data from Pajak.io"),
                        "errors": [errors],
                    }

        if pajakio_invoices and self._can_commit():
            self.env.cr.commit()

    @api.model
    def _link_invoice_documents(self, invoices_data):
        # EXTENDS 'account'
        super()._link_invoice_documents(invoices_data)

        # link the pajak.io JSON attachment to the invoice
        attachment_vals = [
            invoice_data.get('pajakio_attachments')
            for invoice_data in invoices_data.values()
            if 'pajakio_attachments' in invoice_data
        ]

        if attachment_vals:
            attachments = self.env['ir.attachment'].with_user(SUPERUSER_ID).create(attachment_vals)
            res_ids = [attachment.res_id for attachment in attachments]
            self.env['l10n_id_efaktur_coretax.document'].browse(res_ids).invalidate_recordset(fnames=['l10n_id_pajakio_file'])
