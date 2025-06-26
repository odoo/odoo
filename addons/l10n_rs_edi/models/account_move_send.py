from odoo import _, api, models, SUPERUSER_ID


class AccountMoveSend(models.AbstractModel):
    _inherit = "account.move.send"

    @api.model
    def _is_rs_edi_applicable(self, move):
        return move.l10n_rs_edi_is_eligible

    def _get_all_extra_edis(self) -> dict:
        # EXTENDS 'account'
        res = super()._get_all_extra_edis()
        res.update({'rs_edi': {'label': 'eFaktura', 'is_applicable': self._is_rs_edi_applicable, 'help': 'Send the E-Invoice to Government via eFaktura'}})
        res.update({'rs_cir_checkbox': {'is_applicable': self._is_rs_edi_applicable, 'label': _("Send to CIR"), 'help': _("Send to Central Invoice Register(For B2G and the public sector)")}})
        return res

    @api.model
    def _get_invoice_extra_attachments(self, invoice):
        # EXTENDS 'account'
        return super()._get_invoice_extra_attachments(invoice) + invoice.l10n_rs_edi_attachment_id

    @api.model
    def _call_web_service_after_invoice_pdf_render(self, invoices_data):
        # EXTENDS 'account'
        super()._call_web_service_after_invoice_pdf_render(invoices_data)
        for invoice, invoice_data in invoices_data.items():
            # Not all invoices may need EDI.
            if 'rs_edi' not in invoice_data['extra_edis']:
                continue
            if not invoice.company_id.l10n_rs_edi_api_key:
                invoice_data["error"] = {
                    "error_title": _("eFaktura API Key is missing."),
                    "errors": [_("Please configure the eFaktura API Key in the company settings.")],
                }
                continue
            send_to_cir = 'rs_cir_checkbox' in invoice_data['extra_edis']
            xml, error = invoice._l10n_rs_edi_send(send_to_cir)
            if error:
                invoice_data["error"] = {
                    "error_title": _("Errors when submitting the e-invoice to eFaktura:"),
                    "errors": [error],
                }
                continue
            invoice_data['l10n_rs_edi_attachment_values'] = invoice._l10n_rs_edi_get_attachment_values(xml)

            if self._can_commit():
                self.env.cr.commit()

    @api.model
    def _link_invoice_documents(self, invoices_data):
        # EXTENDS 'account'
        super()._link_invoice_documents(invoices_data)
        attachments_vals = [
            invoice_data.get('l10n_rs_edi_attachment_values')
            for invoice_data in invoices_data.values()
            if invoice_data.get('l10n_rs_edi_attachment_values')
        ]
        if attachments_vals:
            attachments = self.env['ir.attachment'].with_user(SUPERUSER_ID).create(attachments_vals)
            res_ids = [attachment.res_id for attachment in attachments]
            self.env['account.move'].browse(res_ids).invalidate_recordset(fnames=['l10n_rs_edi_attachment_id', 'l10n_rs_edi_attachment_file'])
