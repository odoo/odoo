from odoo import api, fields, models, _


class AccountMoveSend(models.TransientModel):
    _inherit = 'account.move.send'

    l10n_ro_edi_send_enable = fields.Boolean(compute='_compute_l10n_ro_edi_send_enable')
    l10n_ro_edi_send_readonly = fields.Boolean(compute='_compute_l10n_ro_edi_send_readonly')
    l10n_ro_edi_send_checkbox = fields.Boolean(
        string='Send E-Factura to SPV',
        compute='_compute_l10n_ro_edi_send_checkbox', store=True, readonly=False,
        help='Send the CIUS-RO XML to the Romanian Government via the ANAF platform')
    l10n_ro_edi_send_warning_message = fields.Text(compute='_compute_l10n_ro_edi_send_warning_message')

    def _get_wizard_values(self):
        # EXTENDS 'account'
        values = super()._get_wizard_values()
        values['l10n_ro_edi_send'] = self.l10n_ro_edi_send_checkbox
        return values

    @api.depends('move_ids.ubl_cii_xml_id', 'enable_ubl_cii_xml')
    def _compute_l10n_ro_edi_send_enable(self):
        for wizard in self:
            wizard.l10n_ro_edi_send_enable = wizard.enable_ubl_cii_xml or any(
                m.ubl_cii_xml_id and m.l10n_ro_edi_state != 'invoice_sent' for m in wizard.move_ids)

    @api.depends('move_ids.l10n_ro_edi_state', 'l10n_ro_edi_send_enable')
    def _compute_l10n_ro_edi_send_readonly(self):
        for wizard in self:
            wizard.l10n_ro_edi_send_readonly = not wizard.l10n_ro_edi_send_enable or any(
                move.l10n_ro_edi_state == 'invoice_sending' for move in wizard.move_ids)

    @api.depends('l10n_ro_edi_send_readonly')
    def _compute_l10n_ro_edi_send_checkbox(self):
        for wizard in self:
            wizard.l10n_ro_edi_send_checkbox = not wizard.l10n_ro_edi_send_readonly

    @api.depends('move_ids.l10n_ro_edi_state')
    def _compute_l10n_ro_edi_send_warning_message(self):
        for wizard in self:
            warning_messages = False
            moves_in_sending = wizard.move_ids.filtered(lambda m: m.l10n_ro_edi_state == 'invoice_sending').mapped('name')
            if moves_in_sending:
                warning_messages = _("The following move(s) are waiting for answer from E-Factura: %s", ', '.join(moves_in_sending))
            wizard.l10n_ro_edi_send_warning_message = warning_messages

    @api.depends('l10n_ro_edi_send_checkbox')
    def _compute_checkbox_ubl_cii_xml(self):
        # extends 'account_edi_ubl_cii'
        super()._compute_checkbox_ubl_cii_xml()
        for wizard in self:
            if wizard.l10n_ro_edi_send_checkbox and wizard.enable_ubl_cii_xml and not wizard.checkbox_ubl_cii_xml:
                wizard.checkbox_ubl_cii_xml = True

    @api.model
    def _call_web_service_after_invoice_pdf_render(self, invoices_data):
        # EXTENDS 'account'
        super()._call_web_service_after_invoice_pdf_render(invoices_data)
        for invoice, invoice_data in invoices_data.items():
            if invoice_data.get('l10n_ro_edi_send') and invoice.l10n_ro_edi_state not in ('invoice_sending', 'invoice_sent'):
                if invoice_data.get('ubl_cii_xml_attachment_values'):
                    xml_data = invoice_data['ubl_cii_xml_attachment_values']['raw']
                elif invoice.ubl_cii_xml_id:
                    xml_data = invoice.ubl_cii_xml_id.raw
                else:
                    xml_data = None

                if errors := invoice._l10n_ro_edi_compute_errors(xml_data):
                    invoice_data['error'] = {
                        'error_title': _("Error on preparation to send CIUS-RO E-Factura"),
                        'errors': errors,
                    }
                    continue

                # document = self.env['l10n_ro_edi.document'].create({'invoice_id': invoice.id})
                # document._request_ciusro_send_invoice(xml_data)
                invoice._l10n_ro_edi_send_invoice(xml_data=xml_data)

                if invoice.l10n_ro_edi_state == 'error':
                    invoice_data['error'] = {
                        'error_title': _("Error when sending CIUS-RO E-Factura to the SPV"),
                        'errors': invoice.l10n_ro_edi_message.split('\n'),
                    }
