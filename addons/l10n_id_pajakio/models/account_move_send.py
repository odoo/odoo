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
            and move.company_id.country_code == 'ID'
            and move.company_id.l10n_id_pajakio_active
            and move.l10n_id_pajakio_status in (False, 'rejected')
        )

    def _get_all_extra_edis(self):
        # EXTENDS 'account'
        res = super()._get_all_extra_edis()
        res.update({
            'id_pajakio': {
                'label': 'Send to Pajak.io',
                'is_applicable': self._is_pajakio_edi_applicable,
            }
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
        json_content = invoice._prepare_invoice_payload_pajakio()
        invoice_data['pajakio_attachments'] = {
            'name': f'{invoice.name}_pajakio_request.json',
            'raw': json.dumps(json_content),
            'mimetype': 'application/json',
            'res_model': invoice._name,
            'res_id': invoice.id,
            'res_field': 'l10n_id_pajakio_file'
        }

    @api.model
    def _call_web_service_before_invoice_pdf_render(self, invoices_data):
        # EXTENDS 'account'
        super()._call_web_service_before_invoice_pdf_render(invoices_data)
        for invoice, invoice_data in invoices_data.items():
            # load JSON payload from existing attachment/create in the spot if needed
            if 'id_pajakio' in invoice_data['extra_edis']:
                if 'pajakio_attachments' in invoice_data:
                    json_content = json.loads(invoice_data['pajakio_attachments']['raw'])
                elif invoice.l10n_id_pajakio_file:
                    json_content = json.loads(base64.b64decode(invoice.l10n_id_pajakio_file))
                else:
                    self._l10n_id_pajakio_generate_json(invoice, invoice_data)
                    if 'id_pajakio' not in invoice_data['extra_edis']:
                        continue
                    json_content = json.loads(invoice_data['pajakio_attachments']['raw'])

            # Create invoice (by sending payload to Pajak.io)
            if 'id_pajakio' in invoice_data['extra_edis']:
                if errors := invoice._l10n_id_pajakio_send(json_content):
                    invoice_data['error'] = {
                        'error_title': self.env._('Error when sending to Pajak.io'),
                        'errors': [errors],
                    }

            if 'id_pajakio' in invoice_data['extra_edis']:
                if self._can_commit():
                    self.env.cr.commit()

    def _call_web_service_after_invoice_pdf_render(self, invoices_data):
        # EXTENDS 'account'
        # Update status of pajak.io
        super()._call_web_service_after_invoice_pdf_render(invoices_data)
        for invoice, invoice_data in invoices_data.items():
            if 'id_pajakio' in invoice_data['extra_edis']:
                if errors := invoice._l10n_id_pajakio_update_status():
                    invoice_data["error"] = {
                        "error_title": self.env._("Error when getting invoice data from Pajak.io"),
                        "errors": [errors],
                    }
                if self._can_commit():
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
            self.env['account.move'].browse(res_ids).invalidate_recordset(fnames=['l10n_id_pajakio_file'])
