# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models


class AccountMoveSend(models.TransientModel):
    _inherit = 'account.move.send'

    l10n_it_edi_warning_message = fields.Html(compute='_compute_l10n_it_edi_xml_export')

    l10n_it_edi_enable_xml_export = fields.Boolean(compute='_compute_l10n_it_edi_xml_export')
    l10n_it_edi_readonly_xml_export = fields.Boolean(compute='_compute_l10n_it_edi_xml_export')
    l10n_it_edi_checkbox_xml_export = fields.Boolean('E-invoice XML',
        compute='_compute_l10n_it_edi_checkbox_xml_export',
        store=True,
        readonly=False,
        help="Create the e-invoice XML ready to be sent to the Italian Tax Agency.\n"
             "It is set as readonly if a report has already been created, to avoid inconsistencies.\n"
             "To re-enable it, delete the PDF attachment.")

    l10n_it_edi_enable_send = fields.Boolean(compute='_compute_l10n_it_edi_enable_readonly_send')
    l10n_it_edi_readonly_send = fields.Boolean(compute='_compute_l10n_it_edi_enable_readonly_send')
    l10n_it_edi_checkbox_send = fields.Boolean('Send To Tax Agency',
        compute='_compute_l10n_it_edi_checkbox_send',
        store=True,
        readonly=False,
        help="Send the e-invoice XML to the Italian Tax Agency.")

    def _get_wizard_values(self):
        # EXTENDS 'account'
        values = super()._get_wizard_values()
        values['l10n_it_edi_checkbox_xml_export'] = self.l10n_it_edi_checkbox_xml_export
        values['l10n_it_edi_checkbox_send'] = self.l10n_it_edi_checkbox_send
        return values

    # -------------------------------------------------------------------------
    # COMPUTE/CONSTRAINS METHODS
    # -------------------------------------------------------------------------

    @api.depends('move_ids')
    def _compute_l10n_it_edi_xml_export(self):
        for wizard in self:
            if wizard.company_id.account_fiscal_country_id.code == 'IT':
                if not wizard.company_id.l10n_it_edi_proxy_user_id:
                    wizard.l10n_it_edi_warning_message = _("You must accept the terms and conditions in the Settings to use the IT EDI.")
                else:
                    wizard.l10n_it_edi_warning_message = wizard.move_ids._l10n_it_edi_format_export_data_errors()
                has_pdf_but_no_xml = any(move.invoice_pdf_report_id and not move.l10n_it_edi_attachment_id for move in wizard.move_ids)
                all_have_xml = all(move.l10n_it_edi_attachment_id for move in wizard.move_ids)
                wizard.l10n_it_edi_enable_xml_export = any(m._l10n_it_edi_ready_for_xml_export() for m in wizard.move_ids)
                wizard.l10n_it_edi_readonly_xml_export = bool(wizard.l10n_it_edi_warning_message) or has_pdf_but_no_xml or all_have_xml
            else:
                wizard.l10n_it_edi_warning_message = False
                wizard.l10n_it_edi_enable_xml_export = False
                wizard.l10n_it_edi_readonly_xml_export = False

    @api.depends('move_ids', 'l10n_it_edi_checkbox_xml_export', 'l10n_it_edi_warning_message')
    def _compute_l10n_it_edi_enable_readonly_send(self):
        for wizard in self:
            if wizard.company_id.account_fiscal_country_id.code == 'IT':
                xml_already_sent = all(m.l10n_it_edi_state not in (False, 'rejected') for m in wizard.move_ids)
                wizard.l10n_it_edi_enable_send = wizard.l10n_it_edi_checkbox_xml_export
                wizard.l10n_it_edi_readonly_send = bool(wizard.l10n_it_edi_warning_message) or xml_already_sent
            else:
                wizard.l10n_it_edi_enable_send = False
                wizard.l10n_it_edi_readonly_send = False

    @api.depends('move_ids')
    def _compute_l10n_it_edi_checkbox_xml_export(self):
        for wizard in self:
            if wizard.company_id.account_fiscal_country_id.code == 'IT':
                all_have_xml = all(move.l10n_it_edi_attachment_id for move in wizard.move_ids)
                wizard.l10n_it_edi_checkbox_xml_export = all_have_xml or (wizard.l10n_it_edi_enable_xml_export and not wizard.l10n_it_edi_readonly_xml_export)
            else:
                wizard.l10n_it_edi_checkbox_xml_export = False

    @api.depends('move_ids', 'l10n_it_edi_checkbox_xml_export')
    def _compute_l10n_it_edi_checkbox_send(self):
        for wizard in self:
            if wizard.company_id.account_fiscal_country_id.code == 'IT':
                wizard.l10n_it_edi_checkbox_send = not wizard.l10n_it_edi_readonly_send and wizard.l10n_it_edi_checkbox_xml_export
            else:
                wizard.l10n_it_edi_checkbox_send = False

    # -------------------------------------------------------------------------
    # BUSINESS ACTIONS
    # -------------------------------------------------------------------------

    @api.model
    def _need_invoice_document(self, invoice):
        # EXTENDS 'account'
        return super()._need_invoice_document(invoice) and not invoice.l10n_it_edi_attachment_id

    @api.model
    def _get_invoice_extra_attachments(self, invoice):
        # EXTENDS 'account'
        return super()._get_invoice_extra_attachments(invoice) + invoice.l10n_it_edi_attachment_id

    @api.model
    def _hook_invoice_document_before_pdf_report_render(self, invoice, invoice_data):
        # EXTENDS 'account'
        super()._hook_invoice_document_before_pdf_report_render(invoice, invoice_data)
        if invoice_data.get('l10n_it_edi_checkbox_xml_export') and invoice._l10n_it_edi_ready_for_xml_export():
            if errors := invoice._l10n_it_edi_export_data_check():
                invoice_data['error'] = {
                    'error_title': _("Errors occurred while creating the e-invoice file:"),
                    'errors': errors,
                }

    @api.model
    def _hook_invoice_document_after_pdf_report_render(self, invoice, invoice_data):
        # EXTENDS 'account'
        super()._hook_invoice_document_after_pdf_report_render(invoice, invoice_data)
        if invoice_data.get('l10n_it_edi_checkbox_xml_export') and invoice._l10n_it_edi_ready_for_xml_export():
            invoice_data['l10n_it_edi_values'] = invoice._l10n_it_edi_get_attachment_values(
                pdf_values=invoice_data['pdf_attachment_values'])

    @api.model
    def _call_web_service_after_invoice_pdf_render(self, invoices_data):
        # EXTENDS 'account'
        super()._call_web_service_after_invoice_pdf_render(invoices_data)
        attachments_vals = {}
        moves = self.env['account.move']
        for move, move_data in invoices_data.items():
            if move_data.get('l10n_it_edi_checkbox_send') and move._l10n_it_edi_ready_for_xml_export():
                moves |= move
                if attachment := move.l10n_it_edi_attachment_id:
                    attachments_vals[move] = {'name': attachment.name, 'raw': attachment.raw}
                else:
                    attachments_vals[move] = invoices_data[move]['l10n_it_edi_values']
        moves._l10n_it_edi_send(attachments_vals)

    @api.model
    def _link_invoice_documents(self, invoice, invoice_data):
        # EXTENDS 'account'
        super()._link_invoice_documents(invoice, invoice_data)
        if attachment_vals := invoice_data.get('l10n_it_edi_values'):
            self.env['ir.attachment'].sudo().create(attachment_vals)
            invoice.invalidate_recordset(fnames=['l10n_it_edi_attachment_id', 'l10n_it_edi_attachment_file'])
