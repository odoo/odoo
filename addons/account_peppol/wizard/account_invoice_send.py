# Part of Odoo. See LICENSE file for full copyright and licensing details.

from base64 import b64encode

from odoo import _, api, fields, models, modules, tools
from odoo.exceptions import UserError

from odoo.addons.account_edi_proxy_client.models.account_edi_proxy_user import AccountEdiProxyError


SUPPORTED_FILE_TYPES = {
    'application/pdf': '.pdf',
    'application/vnd.oasis.opendocument.spreadsheet': '.ods',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx',
    'image/jpeg': '.jpeg',
    'image/png': '.png',
    'text/csv': '.csv',
}


class AccountInvoiceSend(models.TransientModel):
    _inherit = 'account.invoice.send'

    peppol_invoice_ids = fields.Many2many(comodel_name='account.move', compute='_compute_peppol_invoice_ids', store=True)
    company_id = fields.Many2one(comodel_name='res.company', compute='_compute_company_id', store=True)
    account_peppol_edi_mode_info = fields.Char(compute='_compute_account_peppol_edi_mode_info')
    checkbox_send_peppol = fields.Boolean(
        string='Send via PEPPOL',
        compute='_compute_checkbox_send_peppol', store=True, readonly=False,
        help='Send the invoice via PEPPOL',
    )
    checkbox_send_peppol_readonly = fields.Boolean(compute='_compute_checkbox_send_peppol_readonly')
    enable_peppol = fields.Boolean(compute='_compute_enable_peppol')
    # technical field needed for computing a warning text about the peppol configuration
    peppol_warning = fields.Char(
        string="Warning",
        compute="_compute_peppol_warning",
    )

    @api.depends('invoice_ids')
    def _compute_peppol_invoice_ids(self):
        for wizard in self:
            wizard.peppol_invoice_ids = wizard.invoice_ids.filtered(
                lambda invoice: (
                        invoice._get_peppol_document()
                    and invoice.peppol_move_state not in ('processing', 'done')
                )
            )

    @api.depends('peppol_invoice_ids')
    def _compute_company_id(self):
        for wizard in self:
            companies = wizard.peppol_invoice_ids.company_id
            if len(companies) > 1:
                raise UserError(_("You can only send invoices from the same company via Peppol."))
            wizard.company_id = companies or self.env.company

    @api.depends('company_id.account_edi_proxy_client_ids.edi_format_id.code')
    def _compute_account_peppol_edi_mode_info(self):
        mode_strings = {
            'test': _('Test'),
            'demo': _('Demo'),
        }
        for wizard in self:
            edi_user = wizard.company_id.sudo().account_edi_proxy_client_ids.filtered(
                lambda usr: usr.edi_format_id.code == 'peppol'
            )
            mode = mode_strings.get(edi_user._get_demo_state())
            wizard.account_peppol_edi_mode_info = f' ({mode})' if mode else ''

    @api.depends('peppol_invoice_ids')
    def _compute_checkbox_send_peppol(self):
        for wizard in self:
            wizard.checkbox_send_peppol = wizard.enable_peppol and wizard.peppol_invoice_ids

    @api.depends('peppol_invoice_ids')
    def _compute_checkbox_send_peppol_readonly(self):
        for wizard in self:
            wizard.checkbox_send_peppol_readonly = not wizard.enable_peppol or not wizard.peppol_invoice_ids

    @api.depends('invoice_ids')
    def _compute_enable_peppol(self):
        for wizard in self:
            wizard.enable_peppol = bool(wizard.invoice_ids) and wizard.company_id.account_peppol_proxy_state == 'active'

    @api.depends('peppol_invoice_ids')
    def _compute_peppol_warning(self):
        for wizard in self:
            warnings = []

            invalid_partners = wizard.peppol_invoice_ids.commercial_partner_id.filtered(
                lambda partner: not partner.account_peppol_is_endpoint_valid
            )
            if invalid_partners:
                partner_warning = _(
                    "The following partners are not correctly configured to receive Peppol documents. "
                    "Please check and verify their Peppol endpoint and the Electronic Invoicing format: "
                    "%s", ', '.join(invalid_partners[:5].mapped('display_name'))
                )
                warnings.append(partner_warning)

            non_peppol_invoices = self.invoice_ids - self.peppol_invoice_ids
            if self.peppol_invoice_ids and non_peppol_invoices:
                non_peppol_warning = _(
                    "The following invoices can not be sent via Peppol. Please check them: "
                    "%s", ', '.join(non_peppol_invoices.mapped('name'))
                )
                warnings.append(non_peppol_warning)

            wizard.peppol_warning = "\n".join(warnings) if warnings else False

    @api.depends('enable_peppol', 'checkbox_send_peppol')
    def _compute_display_attachment_fields(self):
        # EXTENDS 'account'
        super()._compute_display_attachment_fields()
        for wizard in self:
            if not wizard.display_attachment_fields:
                wizard.display_attachment_fields = wizard.enable_peppol and wizard.checkbox_send_peppol and wizard.composition_mode != 'mass_mail'

    def _compute_attachments_not_supported(self):
        # EXTENDS 'account'
        super()._compute_attachments_not_supported()
        for wizard in self:
            if wizard.display_attachment_fields and wizard.checkbox_send_peppol:
                xml_attachment_name = wizard.peppol_invoice_ids._get_peppol_document().attachment_id.name
                _attachments_to_embed, attachments_not_supported = wizard._get_peppol_available_attachments(
                    wizard.peppol_invoice_ids,
                    wizard.attachment_ids.filtered(lambda attachment: attachment.name != xml_attachment_name),
                )
                wizard.attachments_not_supported = {
                    attachment.id if isinstance(attachment.id, int) else attachment.id.origin: _("Unsupported file type via peppol")
                    for attachment in attachments_not_supported
                }

    def send_and_print_action(self):
        if self.enable_peppol and self.checkbox_send_peppol:
            self._send_peppol_documents()
        return super().send_and_print_action()

    def _send_peppol_documents(self):
        self.ensure_one()

        edi_user = self.company_id.account_edi_proxy_client_ids.filtered(
            lambda u: u.edi_format_id.code == 'peppol'
        )
        if not edi_user:
            raise UserError(_("No Account EDI Proxy User found. Please check your company's Peppol configuration."))

        invoices_data = {invoice: {} for invoice in self.peppol_invoice_ids}

        documents = []
        for invoice, invoice_data in invoices_data.items():
            partner = invoice.partner_id.commercial_partner_id
            if not partner.peppol_eas or not partner.peppol_endpoint:
                invoice.peppol_move_state = 'error'
                invoice_data['error'] = _('The partner is missing Peppol EAS and/or Endpoint identifier.')
                continue
            if not partner.account_peppol_is_endpoint_valid:
                invoice.peppol_move_state = 'error'
                invoice_data['error'] = _('Please verify partner configuration in partner settings.')
                continue

            attachment = invoice._get_peppol_document().sudo().attachment_id
            if not attachment:
                invoice.peppol_move_state = 'error'
                invoice_data['error'] = _('Please check that a Peppol document has been generated.')
                continue

            self._embed_extra_attachments(invoice, attachment, self.attachment_ids)
            if len(attachment) > 64000000:
                invoice_data['error'] = _("Invoice %s is too big to send via peppol (64MB limit)", invoice.name)
                continue

            documents.append({
                'filename': attachment.name,
                'receiver': f"{partner.peppol_eas}:{partner.peppol_endpoint}",
                'ubl': b64encode(attachment.raw).decode(),
            })

        if documents:
            try:
                response = edi_user._make_request(
                    f"{edi_user._get_server_url_new()}/api/peppol/1/send_document",
                    params={'documents': documents},
                )
            except AccountEdiProxyError as e:
                for invoice in invoices_data.items():
                    invoice.peppol_move_state = 'error'
                    invoice_data['error'] = e.message
            else:
                if response.get('error'):
                    # at the moment the only error that can happen here is ParticipantNotReady error
                    for invoice, invoice_data in invoices_data.items():
                        invoice.peppol_move_state = 'error'
                        invoice_data['error'] = response['error']['message']
                else:
                    # the response only contains message uuids,
                    # so we have to rely on the order to connect peppol messages to account.move
                    invoices = self.env['account.move'].browse([invoice.id for invoice in invoices_data])
                    for message, invoice in zip(response['messages'], invoices):
                        attachments_linked_message = _("The invoice has been sent to the Peppol Access Point. The following attachments were sent with the XML:")
                        attachments_not_linked_message = _("Some attachments could not be sent with the XML:")

                        invoice.peppol_message_uuid = message['message_uuid']
                        invoice.peppol_move_state = 'processing'

                        xml_attachment_name = invoice._get_peppol_document().attachment_id.name
                        attachments_linked, attachments_not_linked = self._get_peppol_available_attachments(
                            invoice,
                            self.attachment_ids.filtered(lambda attachment: attachment.name != xml_attachment_name),
                        )
                        if attachments_not_linked:
                            invoice.with_context(no_new_invoice=True).message_post(
                                body=attachments_not_linked_message,
                                attachments=[(attachment.name, attachment.raw) for attachment in attachments_not_linked],
                            )

                        if attachments_linked:
                            invoice.with_context(no_new_invoice=True).message_post(
                                body=attachments_linked_message,
                                attachments=[(attachment.name, attachment.raw) for attachment in attachments_linked],
                            )

        if not tools.config['test_enable'] and not modules.module.current_test:
            self._cr.commit()

    def _embed_extra_attachments(self, invoice, xml_attachment, extra_attachments):
        pdf_name = f'{invoice.name.replace("/", "_")}.pdf'
        attachments_to_embed, _not_supported_attachments = self._get_peppol_available_attachments(
            invoice,
            extra_attachments.filtered(
                lambda attachment: attachment.name not in (xml_attachment.name, pdf_name, f'Invoice_{pdf_name}')
            ),
        )
        self.env['ir.actions.report']._add_attachments_into_invoice_xml(
            invoice,
            xml_attachment,
            [{
                'name': attachment.name,
                'raw_b64': attachment.datas,
                'mimetype': attachment.mimetype,
            } for attachment in attachments_to_embed],
        )

    @api.model
    def _get_peppol_available_attachments(self, invoice, attachments):
        if not attachments or not invoice.edi_document_ids.filtered(lambda doc: doc.edi_format_id.code == 'peppol'):
            return self.env['ir.attachment'], attachments or self.env['ir.attachment']
        accepted_attachments = attachments.filtered(lambda attachment: attachment.mimetype in SUPPORTED_FILE_TYPES)
        return accepted_attachments, attachments - accepted_attachments
