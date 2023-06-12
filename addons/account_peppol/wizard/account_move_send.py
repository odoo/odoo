# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from base64 import b64encode

from odoo import api, fields, models, _
from odoo.addons.account_edi_proxy_client.models.account_edi_proxy_user import AccountEdiProxyError


class AccountMoveSend(models.Model):
    _inherit = 'account.move.send'

    checkbox_send_peppol = fields.Boolean(
        string='Send via PEPPOL',
        compute='_compute_checkbox_send_peppol', store=True, readonly=False,
        help='Send the invoice via PEPPOL',
    )
    enable_peppol = fields.Boolean(compute='_compute_send_mail_extra_fields')
    # to be removed once the module is fully available
    peppol_proxy_state = fields.Selection(related='company_id.account_peppol_proxy_state')
    # technical field needed for computing a warning text about the peppol configuration
    peppol_warning = fields.Char(
        string="Warning",
        compute="_compute_peppol_warning",
    )

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('enable_peppol')
    def _compute_checkbox_send_peppol(self):
        for wizard in self:
            wizard.checkbox_send_peppol = wizard.enable_peppol

    @api.depends('checkbox_send_peppol')
    def _compute_checkbox_ubl_cii_xml(self):
        # extends 'account_edi_ubl_cii'
        super()._compute_checkbox_ubl_cii_xml()

        for wizard in self:
            if wizard.checkbox_send_peppol and wizard.enable_ubl_cii_xml and not wizard.checkbox_ubl_cii_xml:
                wizard.checkbox_ubl_cii_xml = True

    @api.depends('checkbox_send_peppol')
    def _compute_mail_attachments_widget(self):
        # EXTENDS 'account' - add depends
        super()._compute_mail_attachments_widget()

    @api.depends('move_ids')
    def _compute_peppol_warning(self):
        for wizard in self:
            invalid_partners = wizard.move_ids.partner_id.filtered(
                lambda partner: not partner.account_peppol_is_endpoint_valid or partner.ubl_cii_format in {False, 'facturx'})
            if not invalid_partners:
                wizard.peppol_warning = False
            else:
                names = ', '.join(invalid_partners[:5].mapped('display_name'))
                wizard.peppol_warning = _("The following partners are not correctly configured to receive Peppol documents. "
                                        "Please check and verify their Peppol endpoint and the Electronic Invoicing format: "
                                        "%s", names)

    def _compute_send_mail_extra_fields(self):
        # Extends 'account'
        super()._compute_send_mail_extra_fields()

        for wizard in self:
            # show peppol option if either the ubl option is available or any move already has a ubl file generated
            # and moves are not processing/done
            wizard.enable_peppol = (
                wizard.company_id.account_peppol_proxy_state == 'active' \
                and (
                    wizard.enable_ubl_cii_xml
                    or any(m.ubl_cii_xml_id and m.peppol_move_state not in ('processing', 'done') for m in wizard.move_ids)
                )
            )

    # -------------------------------------------------------------------------
    # ATTACHMENTS
    # -------------------------------------------------------------------------

    def _needs_ubl_cii_placeholder(self):
        return super()._needs_ubl_cii_placeholder() and not self.checkbox_send_peppol

    # -------------------------------------------------------------------------
    # BUSINESS ACTIONS
    # -------------------------------------------------------------------------

    def action_send_and_print(self, from_cron=False, allow_fallback_pdf=False):
        # Extends 'account' to force ubl xml checkbox if sending via peppol
        self.ensure_one()

        if all([self.checkbox_send_peppol, self.enable_peppol, self.enable_ubl_cii_xml, not self.checkbox_ubl_cii_xml]):
            self.checkbox_ubl_cii_xml = True

        return super().action_send_and_print(from_cron, allow_fallback_pdf)

    def _get_available_field_values_in_multi(self, move):
        # Extends 'account' to force ubl xml checkbox if sending via peppol
        # if there are many invoices to be sent
        values = super()._get_available_field_values_in_multi(move)
        if self.enable_peppol and self.checkbox_send_peppol:
            values['checkbox_ubl_cii_xml'] = True

        return values

    def _call_web_service(self, invoices_data):
        # Overrides 'account'
        super()._call_web_service(invoices_data)

        if not self.checkbox_send_peppol:
            return

        params = {'documents': []}

        invoices_data_peppol = {}
        for invoice, invoice_data in invoices_data.items():
            if invoice_data.get('ubl_cii_xml_attachment_values'):
                xml_file = invoice_data['ubl_cii_xml_attachment_values']['raw']
                filename = invoice_data['ubl_cii_xml_attachment_values']['name']
            elif invoice.ubl_cii_xml_id and invoice.peppol_move_state not in ('processing', 'canceled', 'done'):
                xml_file = invoice.ubl_cii_xml_id.raw
                filename = invoice.ubl_cii_xml_id.name
            else:
                continue

            if not invoice.partner_id.peppol_eas or not invoice.partner_id.peppol_endpoint:
                # should never happen but in case it does, we need to handle it
                invoice.peppol_move_state = 'error'
                invoice_data['error'] = _('The partner is missing Peppol EAS and/or Endpoint identifier.')
                continue

            if not invoice.partner_id.account_peppol_is_endpoint_valid:
                invoice.peppol_move_state = 'error'
                invoice_data['error'] = _('Please verify partner configuration in partner settings.')
                continue

            receiver_identification = f"{invoice.partner_id.peppol_eas}:{invoice.partner_id.peppol_endpoint}"
            params['documents'].append({
                'filename': filename,
                'receiver': receiver_identification,
                'ubl': b64encode(xml_file).decode(),
            })
            invoices_data_peppol[invoice] = invoice_data

        if not params['documents']:
            return

        edi_user = self.env['account_edi_proxy_client.user'].search(
            [
                ('company_id', '=', self.company_id.id),
                ('proxy_type', '=', 'peppol'),
            ],
            limit=1,
        )

        try:
            response = edi_user._make_request(
                f"{edi_user._get_server_url()}/api/peppol/1/send_document",
                params=params,
            )
            if response.get('error'):
                # at the moment the only error that can happen here is ParticipantNotReady error
                for invoice, invoice_data in invoices_data_peppol.items():
                    invoice.peppol_move_state = 'error'
                    invoice_data['error'] = response['error']['message']
        except AccountEdiProxyError as e:
            for invoice, invoice_data in invoices_data_peppol.items():
                invoice.peppol_move_state = 'error'
                invoice_data['error'] = e.message
        else:
            # the response only contains message uuids,
            # so we have to rely on the order to connect peppol messages to account.move
            invoices = self.env['account.move']
            for i, (invoice, invoice_data) in enumerate(invoices_data_peppol.items()):
                invoice.peppol_message_uuid = response['messages'][i]['message_uuid']
                invoice.peppol_move_state = 'processing'
                invoices |= invoice
            log_message = _('The document has been sent to the Peppol Access Point for processing')
            invoices._message_log_batch(bodies=dict((invoice.id, log_message) for invoice in invoices_data_peppol))

        if self._can_commit():
            self._cr.commit()
