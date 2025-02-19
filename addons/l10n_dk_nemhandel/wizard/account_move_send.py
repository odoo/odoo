from base64 import b64encode

from odoo import api, fields, models, _
from odoo.addons.account_edi_proxy_client.models.account_edi_proxy_user import AccountEdiProxyError


class AccountMoveSend(models.TransientModel):
    _inherit = 'account.move.send'

    checkbox_send_nemhandel = fields.Boolean(
        string='Send via Nemhandel',
        compute='_compute_checkbox_send_nemhandel', store=True, readonly=False,
        help='Send the invoice via Nemhandel',
    )
    enable_nemhandel = fields.Boolean(compute='_compute_enable_nemhandel')
    # technical field needed for computing a warning text about the nemhandel configuration
    nemhandel_warning = fields.Json(compute="_compute_nemhandel_warning")
    nemhandel_mode_info = fields.Char(compute='_compute_nemhandel_mode_info')

    def _get_wizard_values(self):
        # EXTENDS 'account'
        values = super()._get_wizard_values()
        values['send_nemhandel'] = self.checkbox_send_nemhandel
        return values

    @api.model
    def _get_wizard_vals_restrict_to(self, only_options):
        # EXTENDS 'account'
        values = super()._get_wizard_vals_restrict_to(only_options)
        return {
            'checkbox_send_nemhandel': False,
            **values,
        }

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('enable_nemhandel')
    def _compute_checkbox_send_nemhandel(self):
        for wizard in self:
            wizard.checkbox_send_nemhandel = wizard.enable_nemhandel

    @api.depends('checkbox_send_nemhandel')
    def _compute_checkbox_ubl_cii_xml(self):
        # extends 'account_edi_ubl_cii'
        super()._compute_checkbox_ubl_cii_xml()
        for wizard in self:
            if wizard.checkbox_send_nemhandel and wizard.enable_ubl_cii_xml and not wizard.checkbox_ubl_cii_xml:
                wizard.checkbox_ubl_cii_xml = True

    @api.depends('checkbox_send_nemhandel')
    def _compute_mail_attachments_widget(self):
        # EXTENDS 'account' - add depends
        super()._compute_mail_attachments_widget()

    @api.depends('move_ids')
    def _compute_nemhandel_warning(self):
        for wizard in self:
            invalid_partners = wizard.move_ids.partner_id.commercial_partner_id.filtered(
                lambda partner: partner.nemhandel_verification_state != 'valid'
            )
            if not invalid_partners:
                wizard.nemhandel_warning = False
            else:
                wizard.nemhandel_warning = {'nemhandel_partners': {
                    'message': _("Partner(s) are not correctly configured to receive Nemhandel documents. Check their Nemhandel Adress"),
                    'action_text': _("View Partner(s)"),
                    'action': invalid_partners._get_records_action(name=_("Check Partner(s)"))
                }}

    @api.depends('enable_ubl_cii_xml')
    def _compute_enable_nemhandel(self):
        for wizard in self:
            # show nemhandel option if either the ubl option is available or any move already has a ubl file generated
            # and moves are not processing/done and if partners have an edi format set to one that works for nemhandel
            invalid_partners = wizard.move_ids.partner_id.commercial_partner_id.filtered(lambda partner: partner.ubl_cii_format != 'oioubl_21')
            wizard.enable_nemhandel = (
                wizard.company_id.l10n_dk_nemhandel_proxy_state == 'receiver'
                and (
                    wizard.enable_ubl_cii_xml
                    or any(m.ubl_cii_xml_id and m.nemhandel_move_state not in {'processing', 'done'} for m in wizard.move_ids)
                )
                and not invalid_partners
            )

    @api.depends('company_id.account_edi_proxy_client_ids.edi_mode')
    def _compute_nemhandel_mode_info(self):
        mode_strings = {
            'test': _('Test'),
            'demo': _('Demo'),
        }
        for wizard in self:
            edi_user = wizard.company_id.account_edi_proxy_client_ids.filtered(lambda usr: usr.proxy_type == 'nemhandel')
            mode = mode_strings.get(edi_user.edi_mode)
            wizard.nemhandel_mode_info = f' ({mode})' if mode else ''

    # -------------------------------------------------------------------------
    # ATTACHMENTS
    # -------------------------------------------------------------------------

    def _needs_ubl_cii_placeholder(self):
        return super()._needs_ubl_cii_placeholder() and not self.checkbox_send_nemhandel

    # -------------------------------------------------------------------------
    # BUSINESS ACTIONS
    # -------------------------------------------------------------------------

    def action_send_and_print(self, force_synchronous=False, allow_fallback_pdf=False, **kwargs):
        # Extends 'account' to force ubl xml checkbox if sending via peppol
        self.ensure_one()

        if all([self.checkbox_send_nemhandel, self.enable_nemhandel, self.enable_ubl_cii_xml, not self.checkbox_ubl_cii_xml]):
            self.checkbox_ubl_cii_xml = True
        if self.checkbox_send_nemhandel and self.enable_nemhandel:
            for move in self.move_ids:
                if not move.nemhandel_move_state or move.nemhandel_move_state == 'ready':
                    move.nemhandel_move_state = 'to_send'

        return super().action_send_and_print(force_synchronous=force_synchronous, allow_fallback_pdf=allow_fallback_pdf, **kwargs)

    @api.model
    def _call_web_service_after_invoice_pdf_render(self, invoices_data):
        # Overrides 'account'
        super()._call_web_service_after_invoice_pdf_render(invoices_data)

        params, invoices_data_nemhandel = self._check_nemhandel_invoices_data_error(invoices_data)

        if not params['documents']:
            return

        edi_user = next(iter(invoices_data)).company_id.account_edi_proxy_client_ids.filtered(lambda u: u.proxy_type == 'nemhandel')

        try:
            response = edi_user._make_request(
                f"{edi_user._get_server_url()}/api/nemhandel/1/send_document",
                params=params,
            )
        except AccountEdiProxyError as e:
            for invoice, invoice_data in invoices_data_nemhandel.items():
                invoice.nemhandel_move_state = 'error'
                invoice_data['error'] = e.message
        else:
            if response.get('error'):
                # at the moment the only error that can happen here is ParticipantNotReady error
                for invoice, invoice_data in invoices_data_nemhandel.items():
                    invoice.nemhandel_move_state = 'error'
                    invoice_data['error'] = response['error']['message']
            else:
                # the response only contains message uuids,
                # so we have to rely on the order to connect peppol messages to account.move
                invoices = self.env['account.move']
                for message, (invoice, invoice_data) in zip(response['messages'], invoices_data_nemhandel.items()):
                    invoice.nemhandel_message_uuid = message['message_uuid']
                    invoice.nemhandel_move_state = 'processing'
                    invoices |= invoice
                log_message = _('The document has been sent to the Nemhandel Access Point for processing')
                invoices._message_log_batch(bodies=dict((invoice.id, log_message) for invoice in invoices))

        if self._can_commit():
            self._cr.commit()

    def _check_nemhandel_invoices_data_error(self, invoices_data):
        params = {'documents': []}
        invoices_data_nemhandel = {}
        for invoice, invoice_data in invoices_data.items():
            if not invoice_data.get('send_nemhandel'):
                continue

            if invoice_data.get('ubl_cii_xml_attachment_values'):
                xml_file = invoice_data['ubl_cii_xml_attachment_values']['raw']
                filename = invoice_data['ubl_cii_xml_attachment_values']['name']
            elif invoice.ubl_cii_xml_id and invoice.nemhandel_move_state not in ('processing', 'canceled', 'done'):
                xml_file = invoice.ubl_cii_xml_id.raw
                filename = invoice.ubl_cii_xml_id.name
            else:
                invoice.nemhandel_move_state = 'skipped'
                continue

            partner = invoice.partner_id.commercial_partner_id
            if not partner.nemhandel_identifier_type or not partner.nemhandel_identifier_value:
                # should never happen but in case it does, we need to handle it
                invoice.nemhandel_move_state = 'error'
                invoice_data['error'] = _('The partner is missing Nemhandel RecipientID and/or Nemhandel identifier.')
                continue

            if partner.nemhandel_verification_state != 'valid':
                invoice.nemhandel_move_state = 'error'
                invoice_data['error'] = _('Please verify partner configuration in partner settings.')
                continue

            receiver_identification = f"{partner.nemhandel_identifier_type}:{partner.nemhandel_identifier_value}"
            params['documents'].append({
                'filename': filename,
                'receiver': receiver_identification,
                'ubl': b64encode(xml_file).decode(),
            })
            invoices_data_nemhandel[invoice] = invoice_data

        return params, invoices_data_nemhandel
