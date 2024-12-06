# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class AccountMoveSend(models.TransientModel):
    _inherit = 'account.move.send'

    l10n_pk_edi_enable_send = fields.Boolean(compute='_compute_l10n_pk_edi_enable_xml')
    l10n_pk_edi_readonly_send = fields.Boolean(compute='_compute_l10n_pk_edi_enable_xml')
    l10n_pk_edi_checkbox_send = fields.Boolean(
        string="Send E-Invoice to FBR.",
        default=True, readonly=False, store=True,
    )

    def _get_wizard_values(self):
        # EXTENDS 'account'
        values = super()._get_wizard_values()
        values['l10n_pk_edi_checkbox_send'] = self.l10n_pk_edi_checkbox_send
        return values

    @api.model
    def _get_wizard_vals_restrict_to(self, only_options):
        # EXTENDS 'account'
        values = super()._get_wizard_vals_restrict_to(only_options)
        return {
            'l10n_pk_edi_checkbox_send': False,
            **values,
        }

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('move_ids')
    def _compute_l10n_pk_edi_enable_xml(self):
        for wizard in self:
            if wizard.company_id.account_fiscal_country_id.code == 'PK':
                wizard.l10n_pk_edi_enable_send = any(
                    move._l10n_pk_edi_get_default_enable() for move in wizard.move_ids
                )
                wizard.l10n_pk_edi_readonly_send = all(
                    move.l10n_pk_edi_state not in (False, 'rejected') for move in wizard.move_ids
                )
            else:
                wizard.l10n_pk_edi_enable_send = False
                wizard.l10n_pk_edi_readonly_send = False

    @api.depends('l10n_pk_edi_checkbox_send')
    def _compute_mail_attachments_widget(self):
        # EXTENDS 'account' - add depends
        super()._compute_mail_attachments_widget()

    # -------------------------------------------------------------------------
    # ATTACHMENTS
    # -------------------------------------------------------------------------

    @api.model
    def _need_invoice_document(self, invoice):
        # EXTENDS 'account'
        return super()._need_invoice_document(invoice) and not invoice.l10n_pk_edi_attachment_id

    @api.model
    def _get_invoice_extra_attachments(self, invoice):
        # EXTENDS 'account'
        return super()._get_invoice_extra_attachments(invoice) + invoice.l10n_pk_edi_attachment_id

    def _get_placeholder_mail_attachments_data(self, move):
        # EXTENDS 'account'
        results = super()._get_placeholder_mail_attachments_data(move)
        if (self.mode == 'invoice_single'
            and self.l10n_pk_edi_enable_send
            and self.l10n_pk_edi_checkbox_send
        ):
            filename = f'{move.name.replace("/", "_")}_FBR.json'
            results.append({
                'id': f'placeholder_{filename}',
                'name': filename,
                'mimetype': 'application/json',
                'placeholder': True,
            })
        return results

    # -------------------------------------------------------------------------
    # BUSINESS ACTIONS
    # -------------------------------------------------------------------------

    @api.model
    def _hook_invoice_document_after_pdf_report_render(self, invoice, invoice_data):
        # EXTENDS 'account'
        super()._hook_invoice_document_after_pdf_report_render(invoice, invoice_data)
        if invoice._l10n_pk_edi_get_default_enable():
            invoice_data['l10n_pk_edi_values'] = invoice._l10n_pk_edi_get_attachment_values()

    @api.model
    def _call_web_service_after_invoice_pdf_render(self, invoices_data):
        # EXTENDS 'account'
        super()._call_web_service_after_invoice_pdf_render(invoices_data)
        attachments_vals = {}
        moves = self.env['account.move']
        for move, move_data in invoices_data.items():
            if (move_data.get('l10n_pk_edi_checkbox_send')
                and move._l10n_pk_edi_get_default_enable()
                and move.l10n_pk_edi_state != 'sent'
            ):
                moves |= move
                if attachment := move.l10n_pk_edi_attachment_id:
                    attachments_vals[move] = {'name': attachment.name, 'raw': attachment.raw}
                else:
                    attachments_vals[move] = invoices_data[move]['l10n_pk_edi_values']
        moves._l10n_pk_edi_send(attachments_vals)

    @api.model
    def _link_invoice_documents(self, invoices_data):
        # EXTENDS 'account'
        super()._link_invoice_documents(invoices_data)
        attachments_vals = [
            invoice_data.get('l10n_pk_edi_values')
            for invoice_data in invoices_data.values()
            if invoice_data.get('l10n_pk_edi_values')
        ]
        if attachments_vals:
            attachments = self.env['ir.attachment'].create(attachments_vals)
            res_ids = [attachment.res_id for attachment in attachments]
            self.env['account.move'].browse(res_ids).invalidate_recordset(
                fnames=['l10n_pk_edi_attachment_id', 'l10n_pk_edi_attachment_file']
            )
