from odoo import api, fields, models, _


class AccountMoveSend(models.TransientModel):
    _inherit = 'account.move.send'

    l10n_ro_edi_send_enable = fields.Boolean(compute='_compute_l10n_ro_edi_send_enable')
    l10n_ro_edi_send_readonly = fields.Boolean(compute='_compute_l10n_ro_edi_send_readonly')
    l10n_ro_edi_send_checkbox = fields.Boolean(
        string='Send E-Factura to SPV',
        compute='_compute_l10n_ro_edi_send_checkbox', store=True, readonly=False,
        help='Send the CIUS-RO XML to the Romanian Government via the ANAF platform')
    l10n_ro_edi_warnings = fields.Char(compute='_compute_l10n_ro_edi_warnings')  # To be removed in master

    def _get_wizard_values(self):
        # EXTENDS 'account'
        values = super()._get_wizard_values()
        values['l10n_ro_edi_send'] = self.l10n_ro_edi_send_checkbox
        return values

    @api.depends('move_ids.l10n_ro_edi_state', 'enable_ubl_cii_xml')
    def _compute_l10n_ro_edi_send_enable(self):
        """ Enable send to SPV if we can create the XML, or
            if the XML is already created and the move already have a l10n_ro_edi.document in error """
        for wizard in self:
            wizard.l10n_ro_edi_send_enable = any(
                (move._need_ubl_cii_xml() or move.ubl_cii_xml_id) and
                move.country_code == 'RO' and
                move.l10n_ro_edi_state in (False, 'invoice_sending')
                for move in wizard.move_ids
            )

    @api.depends('move_ids.l10n_ro_edi_state', 'l10n_ro_edi_send_enable')
    def _compute_l10n_ro_edi_send_readonly(self):
        """ We shouldn't allow the user to send a new request if any move is currently waiting for an answer. """
        for wizard in self:
            wizard.l10n_ro_edi_send_readonly = (
                not wizard.l10n_ro_edi_send_enable
                or 'invoice_sending' in wizard.move_ids.mapped('l10n_ro_edi_state')
            )

    @api.depends('l10n_ro_edi_send_readonly')
    def _compute_l10n_ro_edi_send_checkbox(self):
        for wizard in self:
            wizard.l10n_ro_edi_send_checkbox = not wizard.l10n_ro_edi_send_readonly

    @api.depends('l10n_ro_edi_send_readonly')
    def _compute_l10n_ro_edi_warnings(self):
        """ TODO in master (saas-17.4): merge it with `warnings` field using `_compute_warnings`. """
        for wizard in self:
            waiting_moves = wizard.move_ids.filtered(lambda m: m.l10n_ro_edi_state == 'invoice_sending')
            wizard.l10n_ro_edi_warnings = _(
                "The following move(s) are waiting for answer from the Romanian SPV: %s",
                ', '.join(waiting_moves.mapped('name'))
            ) if waiting_moves else False

    @api.depends('l10n_ro_edi_send_checkbox')
    def _compute_checkbox_ubl_cii_xml(self):
        # EXTENDS 'account_edi_ubl_cii'
        super()._compute_checkbox_ubl_cii_xml()
        for wizard in self:
            if wizard.l10n_ro_edi_send_checkbox and wizard.enable_ubl_cii_xml and not wizard.checkbox_ubl_cii_xml:
                wizard.checkbox_ubl_cii_xml = True

    @api.model
    def _call_web_service_after_invoice_pdf_render(self, invoices_data):
        # EXTENDS 'account'
        super()._call_web_service_after_invoice_pdf_render(invoices_data)

        for invoice, invoice_data in invoices_data.items():
            if invoice_data.get('l10n_ro_edi_send') and not invoice.l10n_ro_edi_state:
                build_errors = None
                if invoice_data.get('ubl_cii_xml_attachment_values'):
                    xml_data = invoice_data['ubl_cii_xml_attachment_values']['raw']
                elif invoice.l10n_ro_edi_document_ids:
                    # If a document is on the invoice but the invoice's l10n_ro_edi_state is False,
                    # this means that the previously sent XML are invalid and have to be rebuilt
                    xml_data, build_errors = self.env['account.edi.xml.ubl_ro']._export_invoice(invoice)
                elif invoice.ubl_cii_xml_id:
                    xml_data = invoice.ubl_cii_xml_id.raw
                else:
                    xml_data, build_errors = self.env['account.edi.xml.ubl_ro']._export_invoice(invoice)

                if build_errors:
                    invoice_data['error'] = {
                        'error_title': _("Error when building the CIUS-RO E-Factura XML"),
                        'errors': build_errors,
                    }
                    continue

                invoice._l10n_ro_edi_send_invoice(xml_data)

                if self._can_commit():
                    self.env.cr.commit()

                active_document = invoice.l10n_ro_edi_document_ids.sorted()[0]

                if active_document.state == 'invoice_sending_failed':
                    invoice_data['error'] = {
                        'error_title': _("Error when sending CIUS-RO E-Factura to the SPV"),
                        'errors': active_document.message.split('\n'),
                    }
