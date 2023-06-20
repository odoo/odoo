from odoo import _, api, fields, models, SUPERUSER_ID

class AccountMoveSend(models.Model):
    _inherit = 'account.move.send'

    l10n_es_edi_facturae_enable_xml = fields.Boolean(compute='_compute_send_mail_extra_fields')
    l10n_es_edi_facturae_checkbox_xml = fields.Boolean(
        string="Generate Facturae edi file",
        default=True,
    )

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    def _compute_send_mail_extra_fields(self):
        # EXTENDS 'account'
        super()._compute_send_mail_extra_fields()
        for wizard in self:
            wizard.l10n_es_edi_facturae_enable_xml = any(move._l10n_es_edi_facturae_get_default_enable() for move in wizard.move_ids)

    @api.depends('l10n_es_edi_facturae_checkbox_xml')
    def _compute_mail_attachments_widget(self):
        # EXTENDS 'account' - add depends
        super()._compute_mail_attachments_widget()

    # -------------------------------------------------------------------------
    # ATTACHMENTS
    # -------------------------------------------------------------------------

    @api.model
    def _get_invoice_extra_attachments(self, move):
        # EXTENDS 'account'
        return super()._get_invoice_extra_attachments(move) + move.l10n_es_edi_facturae_xml_id

    def _get_placeholder_mail_attachments_data(self, move):
        # EXTENDS 'account'
        results = super()._get_placeholder_mail_attachments_data(move)

        if self.mode == 'invoice_single' and self.l10n_es_edi_facturae_enable_xml and self.l10n_es_edi_facturae_checkbox_xml:
            filename = f'{move.name.replace("/", "_")}_facturae_signed.xml'
            results.append({
                'id': f'placeholder_{filename}',
                'name': filename,
                'mimetype': 'application/xml',
                'placeholder': True,
            })

        return results

    # -------------------------------------------------------------------------
    # BUSINESS ACTIONS
    # -------------------------------------------------------------------------

    def _hook_invoice_document_before_pdf_report_render(self, invoice, invoice_data):
        # EXTENDS 'account'
        super()._hook_invoice_document_before_pdf_report_render(invoice, invoice_data)

        if self.l10n_es_edi_facturae_checkbox_xml and invoice._l10n_es_edi_facturae_get_default_enable():
            try:
                xml_content = invoice._l10n_es_edi_facturae_render_facturae()
            except Exception as error:
                invoice_data['error'] = "".join((
                    _("Errors occured while creating the EDI document (format: %s):", "Facturae"),
                    "\n",
                    str(error),
                ))

            invoice_data['l10n_es_edi_facturae_attachment_values'] = {
                'name': invoice._l10n_es_edi_facturae_get_filename(),
                'raw': xml_content,
                'mimetype': 'application/xml',
                'res_model': invoice._name,
                'res_id': invoice.id,
                'res_field': 'l10n_es_edi_facturae_xml_file',  # Binary field
            }

    def _link_invoice_documents(self, invoice, invoice_data):
        # EXTENDS 'account'
        super()._link_invoice_documents(invoice, invoice_data)

        attachment_vals = invoice_data.get('l10n_es_edi_facturae_attachment_values')
        if attachment_vals:
            self.env['ir.attachment'].with_user(SUPERUSER_ID).create(attachment_vals)
            invoice.invalidate_recordset(fnames=['l10n_es_edi_facturae_xml_id', 'l10n_es_edi_facturae_xml_file'])
