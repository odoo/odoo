# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from base64 import b64encode

from odoo import api, fields, models, _
from odoo.addons.account_edi_proxy_client.models.account_edi_proxy_user import AccountEdiProxyError


class AccountMoveSend(models.TransientModel):
    _inherit = 'account.move.send'

    checkbox_send_peppol = fields.Boolean(
        string='Send via PEPPOL',
        compute='_compute_checkbox_send_peppol', store=True, readonly=False,
        help='Send the invoice via PEPPOL',
    )
    enable_peppol = fields.Boolean(compute='_compute_enable_peppol')
    # technical field needed for computing a warning text about the peppol configuration
    peppol_warning = fields.Char(
        string="Warning",
        compute="_compute_peppol_warning",
    )
    account_peppol_edi_mode_info = fields.Char(compute='_compute_account_peppol_edi_mode_info')

    def _get_wizard_values(self):
        # EXTENDS 'account'
        values = super()._get_wizard_values()
        values['send_peppol'] = self.checkbox_send_peppol
        return values

    @api.model
    def _get_wizard_vals_restrict_to(self, only_options):
        # EXTENDS 'account'
        values = super()._get_wizard_vals_restrict_to(only_options)
        return {
            'checkbox_send_peppol': False,
            **values,
        }

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
            invalid_partners = wizard.move_ids.partner_id.commercial_partner_id.filtered(
                lambda partner: not partner.account_peppol_is_endpoint_valid)
            if not invalid_partners:
                wizard.peppol_warning = False
            else:
                names = ', '.join(invalid_partners[:5].mapped('display_name'))
                wizard.peppol_warning = _("The following partners are not correctly configured to receive Peppol documents. "
                                        "Please check and verify their Peppol endpoint and the Electronic Invoicing format: "
                                        "%s", names)

    @api.depends('enable_ubl_cii_xml')
    def _compute_enable_peppol(self):
        for wizard in self:
            # show peppol option if either the ubl option is available or any move already has a ubl file generated
            # and moves are not processing/done and if partners have an edi format set to one that works for peppol
            invalid_partners = wizard.move_ids.partner_id.commercial_partner_id.filtered(
                lambda partner: partner.ubl_cii_format in {False, 'facturx', 'oioubl_201'})
            wizard.enable_peppol = (
                wizard.company_id.account_peppol_proxy_state == 'active' \
                and (
                    wizard.enable_ubl_cii_xml
                    or any(m.ubl_cii_xml_id and m.peppol_move_state not in ('processing', 'done') for m in wizard.move_ids)
                )
                and not invalid_partners
            )

    @api.depends('company_id.account_edi_proxy_client_ids.edi_mode')
    def _compute_account_peppol_edi_mode_info(self):
        mode_strings = {
            'test': _('Test'),
            'demo': _('Demo'),
        }
        for wizard in self:
            edi_user = wizard.company_id.account_edi_proxy_client_ids.filtered(
                lambda usr: usr.proxy_type == 'peppol'
            )
            mode = mode_strings.get(edi_user.edi_mode)
            wizard.account_peppol_edi_mode_info = f' ({mode})' if mode else ''

    # -------------------------------------------------------------------------
    # ATTACHMENTS
    # -------------------------------------------------------------------------

    def _needs_ubl_cii_placeholder(self):
        return super()._needs_ubl_cii_placeholder() and not self.checkbox_send_peppol

    # -------------------------------------------------------------------------
    # BUSINESS ACTIONS
    # -------------------------------------------------------------------------

    def action_send_and_print(self, force_synchronous=False, allow_fallback_pdf=False, **kwargs):
        # Extends 'account' to force ubl xml checkbox if sending via peppol
        self.ensure_one()

        if all([self.checkbox_send_peppol, self.enable_peppol, self.enable_ubl_cii_xml, not self.checkbox_ubl_cii_xml]):
            self.checkbox_ubl_cii_xml = True
        if self.checkbox_send_peppol and self.enable_peppol:
            for move in self.move_ids:
                if not move.peppol_move_state or move.peppol_move_state == 'ready':
                    move.peppol_move_state = 'to_send'

        return super().action_send_and_print(force_synchronous=force_synchronous, allow_fallback_pdf=allow_fallback_pdf, **kwargs)

    @api.model
    def _call_web_service_after_invoice_pdf_render(self, invoices_data):
        # Overrides 'account'
        super()._call_web_service_after_invoice_pdf_render(invoices_data)

        params = {'documents': []}
        invoices_data_peppol = {}
        for invoice, invoice_data in invoices_data.items():
            if invoice_data.get('send_peppol'):
                if invoice_data.get('ubl_cii_xml_attachment_values'):
                    xml_file = invoice_data['ubl_cii_xml_attachment_values']['raw']
                    filename = invoice_data['ubl_cii_xml_attachment_values']['name']
                elif invoice.ubl_cii_xml_id and invoice.peppol_move_state not in ('processing', 'canceled', 'done'):
                    xml_file = invoice.ubl_cii_xml_id.raw
                    filename = invoice.ubl_cii_xml_id.name
                else:
                    invoice.peppol_move_state = 'skipped'
                    continue

                partner = invoice.partner_id.commercial_partner_id
                if not partner.peppol_eas or not partner.peppol_endpoint:
                    # should never happen but in case it does, we need to handle it
                    invoice.peppol_move_state = 'error'
                    invoice_data['error'] = _('The partner is missing Peppol EAS and/or Endpoint identifier.')
                    continue

                if not partner.account_peppol_is_endpoint_valid:
                    invoice.peppol_move_state = 'error'
                    invoice_data['error'] = _('Please verify partner configuration in partner settings.')
                    continue

                receiver_identification = f"{partner.peppol_eas}:{partner.peppol_endpoint}"
                params['documents'].append({
                    'filename': filename,
                    'receiver': receiver_identification,
                    'ubl': b64encode(xml_file).decode(),
                })
                invoices_data_peppol[invoice] = invoice_data

        if not params['documents']:
            return

        edi_user = next(iter(invoices_data)).company_id.account_edi_proxy_client_ids.filtered(
            lambda u: u.proxy_type == 'peppol')

        try:
            response = edi_user._make_request(
                f"{edi_user._get_server_url()}/api/peppol/1/send_document",
                params=params,
            )
        except AccountEdiProxyError as e:
            for invoice, invoice_data in invoices_data_peppol.items():
                invoice.peppol_move_state = 'error'
                invoice_data['error'] = e.message
        else:
            if response.get('error'):
                # at the moment the only error that can happen here is ParticipantNotReady error
                for invoice, invoice_data in invoices_data_peppol.items():
                    invoice.peppol_move_state = 'error'
                    invoice_data['error'] = response['error']['message']
            else:
                # the response only contains message uuids,
                # so we have to rely on the order to connect peppol messages to account.move
                invoices = self.env['account.move']
                for message, (invoice, invoice_data) in zip(response['messages'], invoices_data_peppol.items()):
                    invoice.peppol_message_uuid = message['message_uuid']
                    invoice.peppol_move_state = 'processing'
                    invoices |= invoice
                log_message = _('The document has been sent to the Peppol Access Point for processing')
                invoices._message_log_batch(bodies=dict((invoice.id, log_message) for invoice in invoices))

        if self._can_commit():
            self._cr.commit()
