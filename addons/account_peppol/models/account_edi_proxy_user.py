# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import _, fields, models, modules, tools
from odoo.exceptions import UserError

from odoo.addons.account_edi_proxy_client.models.account_edi_proxy_user import AccountEdiProxyError
from odoo.addons.account_peppol.tools.demo_utils import handle_demo

_logger = logging.getLogger(__name__)
BATCH_SIZE = 50


PEPPOL_CONNECTION_SUPERSEDED_ERROR_CODE = 107


class AccountEdiProxyClientUser(models.Model):
    _inherit = 'account_edi_proxy_client.user'

    peppol_verification_code = fields.Char(string='SMS verification code')
    proxy_type = fields.Selection(selection_add=[('peppol', 'PEPPOL')], ondelete={'peppol': 'cascade'})
    peppol_token_out_of_sync = fields.Boolean(
        string='Peppol Token Out of Sync',
        help="This field is used to indicate that the Peppol token is out of sync with the proxy server. "
             "It is set to True when the token needs to be refreshed or updated.",
    )
    peppol_token_sync_version = fields.Integer(
        string='Peppol Token Sync Version',
    )

    # -------------------------------------------------------------------------
    # HELPER METHODS
    # -------------------------------------------------------------------------

    def _make_request(self, url, params=False):
        if self.proxy_type == 'peppol':
            return self._make_request_peppol(url, params=params)
        return super()._make_request(url, params=params)

    @handle_demo
    def _make_request_peppol(self, url, params=False):
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
                    'account_peppol_migration_key': False,
                })
                # commit the above changes before raising below
                if not tools.config['test_enable'] and not modules.module.current_test:
                    self.env.cr.commit()
            elif e.code == 'invalid_signature':
                self._mark_connection_out_of_sync()
                if not tools.config['test_enable'] and not modules.module.current_test:
                    self.env.cr.commit()
                raise AccountEdiProxyError(
                    e.code,
                    _(
                        "Failed to connect to Peppol Access Point. This might happen if you restored a database from a backup or copied it without neutralization. "
                        "To fix this, please go to Settings > Accounting > Peppol Settings and click on 'Reconnect this database'."
                    )
                )
            raise AccountEdiProxyError(e.code, e.message)
        return result

    def _should_fallback_to_private_key_auth(self):
        # OVERRIDES account_edi_proxy_client
        return (self.proxy_type == 'peppol' and self.private_key and self.peppol_token_out_of_sync) or super()._should_fallback_to_private_key_auth()

    def _mark_connection_out_of_sync(self):
        self.ensure_one()
        if self.peppol_token_out_of_sync:
            return
        self.write({
            'peppol_token_out_of_sync': True,
            'refresh_token': None,
        })
        response = self._make_request(
            f'{self._get_server_url()}/api/peppol/1/mark_connection_out_of_sync',
            params={'token_desync_counter': self.peppol_token_sync_version},
        )
        if response.get('error'):
            raise AccountEdiProxyError(
                response['error'].get('code', 'unknown_error'),
                response['error'].get('message', "An unknown error occurred while authenticating with IAP server.")
            )

    def _peppol_out_of_sync_reconnect_this_database(self):
        self.ensure_one()
        assert self.peppol_token_out_of_sync
        response = self._make_request(
            f'{self._get_server_url()}/api/peppol/1/resync_connection',
            params={'token_desync_counter': self.peppol_token_sync_version},
        )
        self.write({
            'refresh_token': response.get('refresh_token'),
            'peppol_token_out_of_sync': False,
        })

    def _peppol_out_of_sync_disconnect_this_database(self):
        self.ensure_one()
        assert self.peppol_token_out_of_sync
        # delete this record and company's proxy state
        self.company_id.write({
            'account_peppol_proxy_state': 'not_registered',
            'account_peppol_migration_key': False,
        })
        self.unlink()

    def _get_proxy_urls(self):
        urls = super()._get_proxy_urls()
        urls['peppol'] = {
            'prod': 'https://peppol.api.odoo.com',
            'test': 'https://peppol.test.odoo.com',
            'demo': 'demo',
        }
        return urls

    # -------------------------------------------------------------------------
    # CRONS
    # -------------------------------------------------------------------------

    def _cron_peppol_get_new_documents(self):
        edi_users = self.search([('company_id.account_peppol_proxy_state', '=', 'active'), ('proxy_type', '=', 'peppol')])
        edi_users._peppol_get_new_documents()

    def _cron_peppol_get_message_status(self):
        edi_users = self.search([('company_id.account_peppol_proxy_state', '=', 'active'), ('proxy_type', '=', 'peppol')])
        edi_users._peppol_get_message_status()

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

    def _peppol_get_new_documents(self):
        # Context added to not break stable policy: useful to tweak on databases processing large invoices
        job_count = self._context.get('peppol_crons_job_count') or BATCH_SIZE
        need_retrigger = False
        params = {
            'domain': {
                'direction': 'incoming',
                'errors': False,
            }
        }
        for edi_user in self:
            params['domain']['receiver_identifier'] = edi_user.edi_identification
            try:
                # request all messages that haven't been acknowledged
                messages = edi_user._make_request(
                    url=f"{edi_user._get_server_url()}/api/peppol/1/get_all_documents",
                    params=params,
                )
            except AccountEdiProxyError as e:
                _logger.error(
                    'Error while receiving the document from Peppol Proxy: %s', e.message)
                continue

            message_uuids = [
                message['uuid']
                for message in messages.get('messages', [])
            ]
            if not message_uuids:
                continue

            company = edi_user.company_id
            journal = company.peppol_purchase_journal_id
            # use the first purchase journal if the Peppol journal is not set up
            # to create the move anyway
            if not journal:
                journal = self.env['account.journal'].search([
                    *self.env['account.journal']._check_company_domain(company),
                    ('type', '=', 'purchase')
                ], limit=1)

            need_retrigger = need_retrigger or len(message_uuids) > job_count
            message_uuids = message_uuids[:job_count]
            proxy_acks = []

            # retrieve attachments for filtered messages
            all_messages = edi_user._make_request(
                f"{edi_user._get_server_url()}/api/peppol/1/get_document",
                {'message_uuids': message_uuids},
            )

            for uuid, content in all_messages.items():
                enc_key = content["enc_key"]
                document_content = content["document"]
                filename = content["filename"] or 'attachment'  # default to attachment, which should not usually happen
                decoded_document = edi_user._decrypt_data(document_content, enc_key)
                attachment_vals = {
                    'name': f'{filename}.xml',
                    'raw': decoded_document,
                    'type': 'binary',
                    'mimetype': 'application/xml',
                }

                try:
                    attachment = self.env['ir.attachment'].create(attachment_vals)
                    move = journal\
                        .with_context(
                            default_move_type='in_invoice',
                            default_peppol_move_state=content['state'],
                            default_peppol_message_uuid=uuid,
                        )\
                        ._create_document_from_attachment(attachment.id)
                    move._message_log(body=_('Peppol document has been received successfully'))
                # pylint: disable=broad-except
                except Exception:  # noqa: BLE001
                    # if the invoice creation fails for any reason,
                    # we want to create an empty invoice with the attachment
                    move = self.env['account.move'].create({
                        'move_type': 'in_invoice',
                        'peppol_move_state': 'done',
                        'company_id': company.id,
                        'peppol_message_uuid': uuid,
                    })
                    attachment_vals.update({
                        'res_model': 'account.move',
                        'res_id': move.id,
                    })
                    self.env['ir.attachment'].create(attachment_vals)
                if 'is_in_extractable_state' in move._fields:
                    move.is_in_extractable_state = False

                proxy_acks.append(uuid)

            if not tools.config['test_enable']:
                self.env.cr.commit()
            if proxy_acks:
                edi_user._make_request(
                    f"{edi_user._get_server_url()}/api/peppol/1/ack",
                    {'message_uuids': proxy_acks},
                )

        if need_retrigger:
            self.env.ref('account_peppol.ir_cron_peppol_get_new_documents')._trigger()

    def _peppol_get_message_status(self):
        # Context added to not break stable policy: useful to tweak on databases processing large invoices
        job_count = self._context.get('peppol_crons_job_count') or BATCH_SIZE
        need_retrigger = False
        for edi_user in self:
            edi_user_moves = self.env['account.move'].search([
                ('peppol_move_state', '=', 'processing'),
                ('company_id', '=', edi_user.company_id.id),
            ], limit=job_count + 1)
            if not edi_user_moves:
                continue

            need_retrigger = need_retrigger or len(edi_user_moves) > job_count
            message_uuids = {move.peppol_message_uuid: move for move in edi_user_moves[:job_count]}
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
                    edi_user_moves._message_log_batch(bodies={move.id: log_message for move in edi_user_moves})
                    break

                move = message_uuids[uuid]
                if content.get('error'):
                    # "Peppol request not ready" error:
                    # thrown when the IAP is still processing the message
                    if content['error'].get('code') == 702:
                        continue

                    move.peppol_move_state = 'error'
                    move._message_log(body=_("Peppol error: %s", content['error'].get('data', {}).get('message') or content['error']['message']))
                    continue

                move.peppol_move_state = content['state']
                move._message_log(body=_('Peppol status update: %s', content['state']))

            edi_user._make_request(
                f"{edi_user._get_server_url()}/api/peppol/1/ack",
                {'message_uuids': list(message_uuids.keys())},
            )

        if need_retrigger:
            self.env.ref('account_peppol.ir_cron_peppol_get_message_status')._trigger()

    def _cron_peppol_get_participant_status(self):
        edi_users = self.search([('company_id.account_peppol_proxy_state', 'in', ['pending', 'not_verified', 'sent_verification']), ('proxy_type', '=', 'peppol')])
        edi_users._peppol_get_participant_status()

    def _peppol_get_participant_status(self):
        for edi_user in self:
            try:
                proxy_user = edi_user._make_request(
                    f"{edi_user._get_server_url()}/api/peppol/1/participant_status")
            except AccountEdiProxyError as e:
                _logger.error('Error while updating Peppol participant status: %s', e)
                continue

            state_map = {
                'active': 'active',
                'verified': 'pending',
                'rejected': 'rejected',
                'canceled': 'canceled',
            }

            if proxy_user['peppol_state'] in state_map:
                edi_user.company_id.account_peppol_proxy_state = state_map[proxy_user['peppol_state']]
