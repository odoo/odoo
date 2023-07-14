# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models


class AccountMoveSend(models.Model):
    _inherit = 'account.move.send'

    l10n_it_edi_enable_send = fields.Boolean(compute='_compute_send_mail_extra_fields')
    l10n_it_edi_checkbox_send = fields.Boolean('Tax Agency (Italy)', compute='_compute_l10n_it_edi_checkbox_send',
        store=True, readonly=False, help=(
            "Send the invoice to the Italian Tax Agency.\n"
            "It is set as readonly if a report has already been created, to avoid inconsistencies.\n"
            "To re-enable it, delete the PDF attachment."))
    l10n_it_edi_readonly = fields.Boolean(compute='_compute_send_mail_extra_fields')
    l10n_it_edi_warning_message = fields.Html(compute='_compute_send_mail_extra_fields')

    def _get_available_field_values_in_multi(self, move):
        # EXTENDS 'account'
        values = super()._get_available_field_values_in_multi(move)
        values['l10n_it_edi_checkbox_send'] = self.l10n_it_edi_checkbox_send and self._get_default_l10n_it_edi_enable_send(move)
        return values

    # -------------------------------------------------------------------------
    # COMPUTE/CONSTRAINS METHODS
    # -------------------------------------------------------------------------

    @api.depends('l10n_it_edi_enable_send')
    def _compute_send_mail_extra_fields(self):
        # EXTENDS account
        super()._compute_send_mail_extra_fields()
        for wizard in self:
            wizard.l10n_it_edi_enable_send = any(
                wizard._get_default_l10n_it_edi_enable_send(m)
                and not m.l10n_it_edi_attachment_id
                for m in wizard.move_ids)

            if not wizard.company_id.l10n_it_edi_proxy_user_id:
                wizard.l10n_it_edi_warning_message = _("You must accept the terms and conditions in the Settings to use the IT EDI.")
            else:
                wizard.l10n_it_edi_warning_message = wizard.move_ids._l10n_it_edi_format_export_data_errors()

            already_has_pdf = any(wizard.move_ids.mapped("invoice_pdf_report_id"))
            already_has_xml = any(x._is_l10n_it_edi_import_file() for x in wizard.move_ids.mapped("attachment_ids"))
            wizard.l10n_it_edi_readonly = wizard.l10n_it_edi_warning_message or already_has_pdf or already_has_xml

    @api.depends('l10n_it_edi_readonly', 'l10n_it_edi_enable_send')
    def _compute_l10n_it_edi_checkbox_send(self):
        for wizard in self:
            wizard.l10n_it_edi_checkbox_send = wizard.l10n_it_edi_enable_send and not wizard.l10n_it_edi_readonly

    @api.depends('move_ids')
    def _get_default_l10n_it_edi_enable_send(self, move):
        return (
            move.company_id.account_fiscal_country_id.code == 'IT'
            and move.journal_id.type == 'sale'
            and move.l10n_it_edi_state in (False, 'rejected')
        )

    # -------------------------------------------------------------------------
    # BUSINESS ACTIONS
    # -------------------------------------------------------------------------

    @api.model
    def _get_invoice_extra_attachments(self, move):
        # EXTENDS 'account'
        return super()._get_invoice_extra_attachments(move) + move.l10n_it_edi_attachment_id

    def _hook_invoice_document_before_pdf_report_render(self, invoice, invoice_data):
        # EXTENDS 'account'
        super()._hook_invoice_document_before_pdf_report_render(invoice, invoice_data)
        if self.l10n_it_edi_checkbox_send and self._get_default_l10n_it_edi_enable_send(invoice):
            if errors := invoice._l10n_it_edi_export_data_check():
                message = _("Errors occured while creating the e-invoice file.")
                message += "\n- " + "\n- ".join(errors)
                invoice_data['error'] = message

    def _hook_invoice_document_after_pdf_report_render(self, invoice, invoice_data):
        # EXTENDS 'account'
        super()._hook_invoice_document_after_pdf_report_render(invoice, invoice_data)
        if self.l10n_it_edi_checkbox_send and self._get_default_l10n_it_edi_enable_send(invoice):
            invoice_data['l10n_it_edi_values'] = invoice._l10n_it_edi_get_attachment_values(
                pdf_values=invoice_data['pdf_attachment_values'])

    def _call_web_service_after_invoice_pdf_render(self, invoices_data):
        # EXTENDS 'account'
        super()._call_web_service_after_invoice_pdf_render(invoices_data)
        if self.l10n_it_edi_checkbox_send:
            attachments_vals = {}
            moves = self.env['account.move']
            for move in invoices_data:
                if self._get_default_l10n_it_edi_enable_send(move):
                    moves |= move
                    attachments_vals[move] = invoices_data[move]['l10n_it_edi_values']
            moves._l10n_it_edi_send(attachments_vals)

    def _link_invoice_documents(self, invoice, invoice_data):
        # EXTENDS 'account'
        super()._link_invoice_documents(invoice, invoice_data)
        if attachment_vals := invoice_data.get('l10n_it_edi_values'):
            self.env['ir.attachment'].sudo().create(attachment_vals)
            invoice.invalidate_recordset(fnames=['l10n_it_edi_attachment_id', 'l10n_it_edi_attachment_file'])
