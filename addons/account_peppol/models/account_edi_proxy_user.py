# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import _, fields, models, modules, tools
from odoo.exceptions import UserError
from odoo.addons.account_edi_proxy_client.models.account_edi_proxy_user import AccountEdiProxyError

_logger = logging.getLogger(__name__)


class AccountEdiProxyClientUser(models.Model):
    _inherit = 'account_edi_proxy_client.user'

    peppol_verification_code = fields.Char(string='SMS verification code')
    proxy_type = fields.Selection(selection_add=[('peppol', 'PEPPOL')], ondelete={'peppol': 'cascade'})

    # -------------------------------------------------------------------------
    # HELPER METHODS
    # -------------------------------------------------------------------------

    def _make_request(self, url, params=False):
        # extends account_edi_proxy_client to update peppol_proxy_state
        # of archived users
        try:
            result = super()._make_request(url, params)
        except AccountEdiProxyError as e:
            if (
                e.code == 'no_such_user'
                and not self.active
                and not self.company_id.account_edi_proxy_client_ids.filtered(lambda u: u.proxy_type == 'peppol')
            ):
                self.company_id.write({
                    'account_peppol_proxy_state': 'not_registered',
                    'is_account_peppol_participant': False,
                    'account_peppol_migration_key': False,
                })
                # commit the above changes before raising below
                if not tools.config['test_enable'] and not modules.module.current_test:
                    self.env.cr.commit()
            raise AccountEdiProxyError(e.code, e.message)
        return result

    def _get_proxy_urls(self):
        urls = super()._get_proxy_urls()
        urls['peppol'] = {
            'prod': 'https://peppol.api.odoo.com',
            'test': 'https://peppol.test.odoo.com',
        }
        return urls

    def _get_server_url(self, proxy_type=None, edi_mode=None):
        proxy_type = proxy_type or self.proxy_type
        if not proxy_type == 'peppol':
            return super()._get_server_url(proxy_type, edi_mode)

        peppol_param = self.env['ir.config_parameter'].sudo().get_param(
            'account_peppol.edi.mode', False
        )
        if peppol_param == 'test':
            edi_mode = 'test'

        return super()._get_server_url(proxy_type, edi_mode)

    # -------------------------------------------------------------------------
    # BUSINESS ACTIONS
    # -------------------------------------------------------------------------

    def _get_proxy_identification(self, company, proxy_type):
        if proxy_type == 'peppol':
            if not company.peppol_eas or not company.peppol_endpoint:
                raise UserError(
                    _("Please fill in the EAS code and the Participant ID code."))
            return f'{company.peppol_eas}:{company.peppol_endpoint}'
        return super()._get_proxy_identification(company, proxy_type)

    def _cron_peppol_get_new_documents(self):
        # Retrieve all new Peppol documents for every edi user in the database
        edi_users = self.env['account_edi_proxy_client.user'].search(
            [('company_id.account_peppol_proxy_state', '=', 'active')])

        for edi_user in edi_users:
            proxy_acks = []
            try:
                # request all messages that haven't been acknowledged
                messages = edi_user._make_request(
                    f"{edi_user._get_server_url()}/api/peppol/1/get_all_documents")
            except AccountEdiProxyError as e:
                _logger.error(
                    'Error while receiving the document from Peppol Proxy: %s', e.message)
                continue

            message_uuids = [
                message['uuid']
                for message in messages.get('messages', [])
                if message['direction'] == 'incoming'
                and message['receiver'] == edi_user.edi_identification
            ]
            if not message_uuids:
                continue

            company = edi_user.company_id
            # retrieve attachments for filtered messages
            all_messages = edi_user._make_request(
                f"{edi_user._get_server_url()}/api/peppol/1/get_document",
                {'message_uuids': message_uuids},
            )

            for uuid, content in all_messages.items():
                error_move_vals = {
                    'move_type': 'in_invoice',
                    'peppol_move_state': 'error',
                    'company_id': company.id,
                    'extract_can_show_send_button': False,
                    'peppol_message_uuid': uuid,
                }
                if content.get('error'):
                    # in this case there is no attachment that we could add to the account move
                    move = self.env['account.move'].create(error_move_vals)
                    move._message_log(body=_('Error when receiving via Peppol: %s', content['error']['message']))
                    proxy_acks.append(uuid)
                    continue

                enc_key = content["enc_key"]
                document_content = content["document"]
                filename = content["filename"] or 'attachment' # default to attachment, which should not usually happen
                partner_endpoint = content["accounting_supplier_party"]
                decoded_document = edi_user._decrypt_data(document_content, enc_key)

                journal_id = company.peppol_purchase_journal_id
                # use the first purchase journal if the Peppol journal is not set up
                # to create the move anyway
                if not journal_id:
                    journal_id = self.env['account.journal'].search([
                        *self.env['account.journal']._check_company_domain(company),
                        ('type', '=', 'purchase')
                    ], limit=1)

                attachment_vals = {
                    'name': f'{filename}.xml',
                    'raw': decoded_document,
                    'type': 'binary',
                    'mimetype': 'application/xml',
                }

                try:
                    attachment = self.env['ir.attachment'].create(attachment_vals)
                    move = journal_id\
                        .with_context(
                            default_move_type='in_invoice',
                            default_peppol_move_state=content['state'],
                            default_extract_can_show_send_button=False,
                            default_peppol_message_uuid=uuid,
                        )\
                        ._create_document_from_attachment(attachment.id)
                    if partner_endpoint:
                        move._message_log(body=_(
                            'Peppol document has been received successfully. Sender endpoint: %s', partner_endpoint))
                    else:
                        move._message_log(
                            body=_('Peppol document has been received successfully'))
                # pylint: disable=broad-except
                except Exception:
                    # if the invoice creation fails for any reason,
                    # we want to create an empty invoice with the attachment
                    move = self.env['account.move'].create(error_move_vals)
                    attachment_vals.update({
                        'res_model': 'account.move',
                        'res_id': move.id,
                    })
                    self.env['ir.attachment'].create(attachment_vals)
                    if partner_endpoint:
                        move._message_log(body=_(
                            'Failed to import a Peppol document. Sender endpoint: %s', partner_endpoint))
                    else:
                        move._message_log(body=_('Failed to import a Peppol document.'))

                proxy_acks.append(uuid)

            if not tools.config['test_enable']:
                self.env.cr.commit()
            if proxy_acks:
                edi_user._make_request(
                    f"{edi_user._get_server_url()}/api/peppol/1/ack",
                    {'message_uuids': proxy_acks},
                )

    def _cron_peppol_get_message_status(self):
        edi_users = self.env['account_edi_proxy_client.user'].search(
            [('company_id.account_peppol_proxy_state', '=', 'active')])

        for edi_user in edi_users:
            edi_user_moves = self.env['account.move'].search([
                ('peppol_move_state', '=', 'processing'),
                ('company_id', '=', edi_user.company_id.id),
            ])
            if not edi_user_moves:
                continue

            message_uuids = {move.peppol_message_uuid: move for move in edi_user_moves}
            messages_to_process = edi_user._make_request(
                f"{edi_user._get_server_url()}/api/peppol/1/get_document",
                {'message_uuids': list(message_uuids.keys())},
            )

            for uuid, content in messages_to_process.items():
                if uuid == 'error':
                    # this rare edge case can happen if the participant is not active on the proxy side
                    # in this case we can't get information about the invoices
                    edi_user_moves.peppol_move_state = 'error'
                    log_message = _("Peppol error: %s", content['message'])
                    edi_user_moves._message_log_batch(bodies=dict((move.id, log_message) for move in edi_user_moves))
                    continue

                move = message_uuids[uuid]
                if content.get('error'):
                    move.peppol_move_state = 'error'
                    move._message_log(body=_("Peppol error: %s", content['error']['message']))
                    continue

                move.peppol_move_state = content['state']
                move._message_log(body=_('Peppol status update: %s', content['state']))

            if message_uuids:
                edi_user._make_request(
                    f"{edi_user._get_server_url()}/api/peppol/1/ack",
                    {'message_uuids': list(message_uuids.keys())},
                )

    def _cron_peppol_get_participant_status(self):
        edi_users = self.env['account_edi_proxy_client.user'].search(
            [('company_id.account_peppol_proxy_state', '=', 'pending')])

        for edi_user in edi_users:
            try:
                proxy_user = edi_user._make_request(
                    f"{edi_user._get_server_url()}/api/peppol/1/participant_status")
            except AccountEdiProxyError as e:
                _logger.error('Error while updating Peppol participant status: %s', e)
                continue

            if proxy_user['peppol_state'] in {'active', 'rejected', 'canceled'}:
                edi_user.company_id.account_peppol_proxy_state = proxy_user['peppol_state']
