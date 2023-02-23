# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from base64 import b64encode

from odoo import api, fields, models, _
from odoo.addons.account_edi_proxy_client.models.account_edi_proxy_user import AccountEdiProxyError
from odoo.exceptions import UserError


class AccountMoveSend(models.Model):
    _inherit = 'account.move.send'

    checkbox_send_peppol = fields.Boolean(
        string='Send via PEPPOL',
        compute='_compute_checkbox_send_peppol', store=True, readonly=False,
        help='Send the invoice via PEPPOL',
    )
    peppol_proxy_state = fields.Selection(related='company_id.account_peppol_proxy_state')
    peppol_warning = fields.Char(
        string="Warning",
        compute="_compute_peppol_warning",
    ) # technical field needed for computing a warning text about the peppol configuration

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('checkbox_ubl_cii_xml', 'enable_ubl_cii_xml')
    def _compute_checkbox_send_peppol(self):
        # we can't send via peppol if checkbox_ubl_cii_xml is unchecked
        for wizard in self:
            if not (wizard.checkbox_ubl_cii_xml and wizard.enable_ubl_cii_xml):
                wizard.checkbox_send_peppol = False

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

    # -------------------------------------------------------------------------
    # ATTACHMENTS
    # -------------------------------------------------------------------------

    def _needs_ubl_cii_placeholder(self):
        return super()._needs_ubl_cii_placeholder() and not self.checkbox_send_peppol

    # -------------------------------------------------------------------------
    # BUSINESS ACTIONS
    # -------------------------------------------------------------------------

    def action_send_and_print(self, from_cron=False):
        # Extends the wizard to mark the move to be sent via PEPPOL first
        self.ensure_one()

        if self.checkbox_send_peppol and self.peppol_proxy_state == 'active':
            for move in self.move_ids:
                if not move.peppol_move_state:
                    move.peppol_move_state = 'to_send'

        return super().action_send_and_print(from_cron)

    def _call_web_service(self, prepared_data_list):
        # Overrides 'account'
        if not self.checkbox_send_peppol:
            return super()._call_web_service(prepared_data_list)

        params = {'documents': []}
        all_moves = self.env['account.move']

        if not prepared_data_list:
            # if a user tries to resend an invoice that has a peppol error state,
            # the prepared_data_list is going to be empty, as the xml has been aready generated
            error_moves = self.move_ids.filtered(lambda m: m.peppol_move_state == 'error')
            if not error_moves:
                return

            for error_move in error_moves:
                receiver_identification = f"{error_move.partner_id.peppol_eas}:{error_move.partner_id.peppol_endpoint}"
                if not error_move.ubl_cii_xml_id:
                    # this happens when a user manually deletes the xml file
                    # but doesn't delete the pdf file
                    # they should delete both if they want to regenerate attachments
                    raise UserError(_('The following invoice does not have an XML attachment: %s', error_move.name))

                params['documents'].append({
                    'filename': error_move.name,
                    'receiver': receiver_identification,
                    'ubl': b64encode(error_move.ubl_cii_xml_id.raw).decode(),
                })
                all_moves |= error_move

        for move, prepared_data in prepared_data_list:
            if not prepared_data:
                move.peppol_move_state = False
                raise UserError(_('Please select the UBL format'))

            if move.peppol_move_state not in ('to_send', 'error'):
                continue

            xml_file = prepared_data['ubl_cii_xml_attachment_values']['raw']
            filename = prepared_data['ubl_cii_xml_attachment_values']['name']

            if not move.partner_id.peppol_eas or not move.partner_id.peppol_endpoint:
                # should never happen but in case it does, we need to handle it
                move.peppol_move_state = 'error'
                move._message_log(body=_('The partner is missing Peppol EAS and/or Endpoint identifier.'))
                continue

            if not move.partner_id.account_peppol_is_endpoint_valid:
                move.peppol_move_state = 'error'
                move._message_log(body=_('Please verify partner configuration in partner settings.'))
                continue

            receiver_identification = f"{move.partner_id.peppol_eas}:{move.partner_id.peppol_endpoint}"
            params['documents'].append({
                'filename': filename,
                'receiver': receiver_identification,
                'ubl': b64encode(xml_file).decode(),
            })
            all_moves |= move

        edi_user = self.env['account_edi_proxy_client.user'].search([
            ('company_id', '=', self.company_id.id),
            ('proxy_type', '=', 'peppol'),
        ])

        try:
            response = edi_user._make_request(
                f"{edi_user._get_server_url()}/api/peppol/1/send_document",
                params=params,
            )
            if response.get('error'):
                # at the moment the only error that can happen here is ParticipantNotReady error
                all_moves._message_log_batch(bodies=dict((move.id, response['error']['message']) for move in all_moves))
                all_moves.peppol_move_state = 'error'
                raise UserError(response['error']['message'])
        except AccountEdiProxyError as e:
            all_moves._message_log_batch(bodies=dict((move.id, e.message) for move in all_moves))
            all_moves.peppol_move_state = 'error'
            raise UserError(e.message)
        else:
            # the response only contains message uuids,
            # so we have to rely on the order to connect peppol messages to account.move
            for i, move in enumerate(all_moves):
                move.peppol_message_uuid = response['messages'][i]['message_uuid']
                move.peppol_move_state = 'processing'
            log_message = _('The document has been sent to the Peppol Access Point for processing')
            all_moves._message_log_batch(bodies=dict((move.id, log_message) for move in all_moves))
