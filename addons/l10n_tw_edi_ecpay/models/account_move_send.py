# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import json

from odoo import SUPERUSER_ID, api, models


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    @api.model
    def _is_tw_edi_applicable(self, move):
        return (move.move_type == 'out_invoice'
                and ('debit_origin_id' not in self.env['account.move']._fields or not move.debit_origin_id)
                and move.state == 'posted'
                and move.company_id.country_id.code == 'TW'
                and not move.l10n_tw_edi_state
                and move.company_id._is_ecpay_enabled())

    @api.model
    def _is_tw_edi_issue_allowance_applicable(self, move):
        return (move.move_type == 'out_refund'
                and move.state == 'posted'
                and move.company_id.country_id.code == 'TW'
                and move.reversed_entry_id
                and move.reversed_entry_id.l10n_tw_edi_ecpay_invoice_id
                and not move.l10n_tw_edi_refund_invoice_number
                and not move.l10n_tw_edi_refund_state
                and move.company_id._is_ecpay_enabled())

    def _get_all_extra_edis(self):
        # EXTENDS 'account'
        res = super()._get_all_extra_edis()
        res.update({
            'tw_ecpay_send': {'label': self.env._("Send to Ecpay"), 'is_applicable': self._is_tw_edi_applicable},
            'tw_ecpay_issue_allowance': {'label': self.env._("Send to Ecpay (Issue Allowance)"),
                                         'is_applicable': self._is_tw_edi_issue_allowance_applicable},
        })
        return res

    # -------------------------------------------------------------------------
    # SENDING METHODS
    # -------------------------------------------------------------------------

    @api.model
    def _l10n_tw_edi_generate_ecpay_json(self, invoice, invoice_data):
        need_file = (
            ((invoice_data['invoice_edi_format'] == 'tw_ecpay'
                or 'manual' in invoice_data['sending_methods'])
                and invoice.company_id._is_ecpay_enabled())
            or 'tw_ecpay_send' in invoice_data['extra_edis']
            or 'tw_ecpay_issue_allowance' in invoice_data['extra_edis']
        )
        file_name = ''
        json_content = {}
        # It should always be generated when sending and downloading.
        if need_file:
            if 'tw_ecpay_send' in invoice_data['extra_edis']:
                json_content = invoice._l10n_tw_edi_generate_invoice_json()
                file_name = f'{invoice.name.replace("/", "_")}_ecpay.json'
            elif 'tw_ecpay_issue_allowance' in invoice_data['extra_edis']:
                json_content = invoice._l10n_tw_edi_generate_issue_allowance_json()
                file_name = f'{invoice.name.replace("/", "_")}_ecpay_issue_allowance.json'
            invoice_data['ecpay_attachments'] = {
                'name': file_name,
                'raw': json.dumps(json_content),
                'mimetype': 'application/json',
                'res_model': invoice._name,
                'res_id': invoice.id,
                'res_field': 'l10n_tw_edi_file',  # Binary field
            }

    @api.model
    def _hook_invoice_document_before_pdf_report_render(self, invoice, invoice_data):
        # EXTENDS 'account'
        super()._hook_invoice_document_before_pdf_report_render(invoice, invoice_data)
        self._l10n_tw_edi_generate_ecpay_json(invoice, invoice_data)

    @api.model
    def _call_web_service_before_invoice_pdf_render(self, invoices_data):
        # EXTENDS 'account'
        super()._call_web_service_before_invoice_pdf_render(invoices_data)

        for invoice, invoice_data in invoices_data.items():
            if any(key in invoice_data['extra_edis'] for key in ('tw_ecpay_send', 'tw_ecpay_issue_allowance')):
                if 'ecpay_attachments' in invoice_data:
                    json_content = json.loads(invoice_data['ecpay_attachments']['raw'])
                # If the invoice was downloaded but not sent, the json file could already be there.
                elif invoice.l10n_tw_edi_file:
                    json_content = json.loads(base64.b64decode(invoice.l10n_tw_edi_file))
                # If we don't have the file data and the file, we will regenerate it.
                else:
                    self._l10n_tw_edi_generate_ecpay_json(invoice, invoice_data)
                    if 'ecpay_attachments' not in invoice_data:
                        continue  # If an error occurred, it'll be in invoice_data['error'] so we can skip this invoice
                    json_content = json.loads(invoice_data['ecpay_attachments']['raw'])

            if 'tw_ecpay_send' in invoice_data['extra_edis']:
                if errors := invoice._l10n_tw_edi_send(json_content):
                    invoice_data["error"] = {
                        "error_title": self.env._("Error when sending the invoices to ECPay."),
                        "errors": errors,
                    }
            elif 'tw_ecpay_issue_allowance' in invoice_data['extra_edis']:
                if errors := invoice._l10n_tw_edi_issue_allowance(json_content):
                    invoice_data["error"] = {
                        "error_title": self.env._("Error when sending the allowances to ECPay."),
                        "errors": errors,
                    }
            if 'tw_ecpay_send' in invoice_data['extra_edis'] or 'tw_ecpay_issue_allowance' in invoice_data['extra_edis']:
                if self._can_commit():
                    self._cr.commit()

    def _call_web_service_after_invoice_pdf_render(self, invoices_data):
        # EXTENDS 'account'
        super()._call_web_service_after_invoice_pdf_render(invoices_data)
        for invoice, invoice_data in invoices_data.items():
            # No need to check tw_ecpay_issue_allowance will go to continue since l10n_tw_edi_state is not invoiced
            if 'tw_ecpay_send' not in invoice_data['extra_edis'] or invoice.l10n_tw_edi_state != 'invoiced':
                continue
            if errors := invoice._l10n_tw_edi_update_ecpay_invoice_info():
                invoice_data["error"] = {
                    "error_title": self.env._("Error when getting the invoice data from ECPay."),
                    "errors": errors,
                }
            # We commit again if possible, to ensure that the invoice status is set in the database in case of errors later.
            if self._can_commit():
                self._cr.commit()

    @api.model
    def _link_invoice_documents(self, invoices_data):
        # EXTENDS 'account'
        super()._link_invoice_documents(invoices_data)

        attachments_vals = [
            invoice_data.get('ecpay_attachments')
            for invoice_data in invoices_data.values()
            if invoice_data.get('ecpay_attachments')
        ]

        if attachments_vals:
            attachments = self.env['ir.attachment'].with_user(SUPERUSER_ID).create(attachments_vals)
            res_ids = [attachment.res_id for attachment in attachments]
            self.env['account.move'].browse(res_ids).invalidate_recordset(fnames=['l10n_tw_edi_file_id', 'l10n_tw_edi_file'])
