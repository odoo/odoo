# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from datetime import timedelta

from odoo import _, api, fields, models, modules, tools
from odoo.exceptions import UserError

from odoo.addons.account_edi_proxy_client.models.account_edi_proxy_user import AccountEdiProxyError
from odoo.addons.account_peppol.exceptions import get_peppol_error_message
from odoo.addons.account_peppol.tools.demo_utils import handle_demo
from odoo.addons.account_peppol.tools.peppol_iap_connector import PEPPOL_PROXY_URLS

_logger = logging.getLogger(__name__)
BATCH_SIZE = 50


class Account_Edi_Proxy_ClientUser(models.Model):
    _inherit = 'account_edi_proxy_client.user'

    proxy_type = fields.Selection(selection_add=[('peppol', 'PEPPOL')], ondelete={'peppol': 'cascade'})

    # -------------------------------------------------------------------------
    # HELPER METHODS
    # -------------------------------------------------------------------------

    def _get_proxy_urls(self):
        urls = super()._get_proxy_urls()
        urls['peppol'] = {
            **PEPPOL_PROXY_URLS,
            'demo': 'demo',
        }
        return urls

    @api.model
    def _get_peppol_error_message(self, error_vals):
        # DEPRECATED - to remove in master
        return get_peppol_error_message(self.env, error_vals)

    @handle_demo
    def _call_peppol_proxy(self, endpoint, params=None):
        self.ensure_one()
        if self.proxy_type != 'peppol':
            raise UserError(_('EDI user should be of type Peppol'))

        token_out_of_sync_error_message = self.env._(
            "Failed to connect to Peppol Access Point. This might happen if you restored a database from a backup or copied it without neutralization. "
            "To fix this, please go to Settings > Accounting > Peppol Settings and click on 'Reconnect this database'."
        )

        if self.is_token_out_of_sync:
            raise UserError(token_out_of_sync_error_message)

        params = params or {}
        try:
            response = self._make_request(
                f"{self._get_server_url()}{endpoint}",
                params=params,
            )
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
                if not modules.module.current_test:
                    self.env.cr.commit()
                raise UserError(_('We could not find a user with this information on our server. Please check your information.'))

            elif e.code == 'invalid_signature':
                self._mark_connection_out_of_sync()
                if not tools.config['test_enable'] and not modules.module.current_test:
                    self.env.cr.commit()
                raise UserError(token_out_of_sync_error_message)
            raise UserError(e.message)

        if error_vals := response.get('error'):
            error_message = get_peppol_error_message(self.env, error_vals)
            raise UserError(error_message)

        return response

    def _mark_connection_out_of_sync(self):
        self.ensure_one()
        if self.is_token_out_of_sync:
            return
        self.sudo().write({
            'is_token_out_of_sync': True,
            'refresh_token': None,
        })
        try:
            self._make_request(
                f'{self._get_server_url()}/api/peppol/1/mark_connection_out_of_sync',
                params={'token_desync_counter': self.token_sync_version},
                auth_type='asymmetric'
            )
        except AccountEdiProxyError as e:
            if e.code == 'connection_superseded':
                self._peppol_out_of_sync_disconnect_this_database()
                if not tools.config['test_enable'] and not modules.module.current_test:
                    self.env.cr.commit()
                raise UserError(_('This connection has been superseded by another database. Register again.'))
            raise

    def _peppol_out_of_sync_reconnect_this_database(self):
        self.ensure_one()
        assert self.is_token_out_of_sync
        self.token_sync_version += 1
        response = self._make_request(
            f'{self._get_server_url()}/api/peppol/1/resync_connection',
            params={'token_desync_counter': self.token_sync_version},
            auth_type='asymmetric'
        )
        if response.get('error'):
            if response['error'].get('code') == 'connection_superseded':
                self._peppol_out_of_sync_disconnect_this_database()
                if not tools.config['test_enable'] and not modules.module.current_test:
                    self.env.cr.commit()
            raise AccountEdiProxyError(
                response['error'].get('code', 'unknown_error'),
                response['error'].get('message', "An unknown error occurred while authenticating with IAP server.")
            )
        self.write({
            'refresh_token': response['refresh_token'],
            'is_token_out_of_sync': False,
        })

        # trigger participant status update after resync to confirm token & keep state in sync
        # but run async, since sync may confirm token server-side (thus increment token_sync_version)
        # yet fail before commit, leaving unrecoverable state
        self.env.ref('account_peppol.ir_cron_peppol_get_participant_status')._trigger()

    def _peppol_out_of_sync_disconnect_this_database(self):
        self.ensure_one()
        assert self.is_token_out_of_sync
        # delete this record and company's proxy state
        self.company_id._reset_peppol_configuration(soft=True)
        self.unlink()

    @api.model
    def _get_can_send_domain(self):
        return ('sender', 'smp_registration', 'receiver')

    # -------------------------------------------------------------------------
    # CRONS
    # -------------------------------------------------------------------------

    def _cron_peppol_get_new_documents(self):
        edi_users = self.search([('company_id.account_peppol_proxy_state', '=', 'receiver'), ('proxy_type', '=', 'peppol')])
        edi_users._peppol_get_new_documents(skip_no_journal=True)

    def _cron_peppol_get_message_status(self):
        edi_users = self.search([('company_id.account_peppol_proxy_state', 'in', self._get_can_send_domain()), ('proxy_type', '=', 'peppol')])
        edi_users._peppol_get_message_status()

    def _cron_peppol_get_participant_status(self):
        edi_users = self.search([('proxy_type', '=', 'peppol')])
        edi_users._peppol_get_participant_status()

        # throughout the registration process, we need to check the status more frequently
        if self.search_count([('company_id.account_peppol_proxy_state', '=', 'smp_registration')], limit=1):
            self.env.ref('account_peppol.ir_cron_peppol_get_participant_status')._trigger(at=fields.Datetime.now() + timedelta(hours=1))

    def _cron_peppol_webhook_keepalive(self):
        edi_users = self.search([('company_id.account_peppol_proxy_state', 'in', ['sender', 'receiver'])])
        edi_users._peppol_reset_webhook()

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

    def _peppol_import_invoice(self, attachment, peppol_state, uuid, journal=None):
        """Save new documents in an accounting journal, when one is specified on the company.

        :param attachment: the new document
        :param peppol_state: the state of the received Peppol document
        :param uuid: the UUID of the Peppol document
        :param journal: journal to use for the new move (otherwise the company's peppol journal will be used)
        :return: the created move (if any)
        """
        self.ensure_one()

        file_data = self.env['account.move']._to_files_data(attachment)[0]

        # Self-billed invoices are invoices which your customer creates on your behalf and sends you via Peppol.
        # In this case, the invoice needs to be created as an out_invoice in a sale journal.
        # 329/527: Self-billing invoice; 261: Self-billing credit note
        is_self_billed = False
        if file_data['xml_tree'].findtext('.//{*}InvoiceTypeCode') in ['389', '527'] or file_data['xml_tree'].findtext('.//{*}CreditNoteTypeCode') == '261':
            is_self_billed = True

        if not is_self_billed:
            journal = journal or self.company_id.peppol_purchase_journal_id
            move_type = 'in_invoice'
            if not journal:
                return {}

        else:
            journal = (
                journal
                or self.env['account.journal'].search(
                    [
                        *self.env['account.journal']._check_company_domain(self.company_id),
                        ('type', '=', 'sale'),
                    ],
                    limit=1
                )
            )
            move_type = 'out_invoice'
            if not journal:
                return {}

        move = self.env['account.move'].create({
            'journal_id': journal.id,
            'move_type': move_type,
            'peppol_move_state': peppol_state,
            'peppol_message_uuid': uuid,
        })
        if 'is_in_extractable_state' in move._fields:
            move.is_in_extractable_state = False

        try:
            move._extend_with_attachments([file_data], new=True)
            move._autopost_bill()
        except Exception:
            _logger.exception("Unexpected error occurred during the import of bill with id %s", move.id)
        attachment.write({'res_model': 'account.move', 'res_id': move.id})
        return {'uuid': uuid, 'move': move}

    def _peppol_get_new_documents(self, skip_no_journal=False):
        # Context added to not break stable policy: useful to tweak on databases processing large invoices
        job_count = self.env.context.get('peppol_crons_job_count') or BATCH_SIZE
        need_retrigger = False
        params = {
            'domain': {
                'direction': 'incoming',
                'errors': False,
            }
        }
        for edi_user in self:
            edi_user = edi_user.with_company(edi_user.company_id)
            if not edi_user.company_id.peppol_purchase_journal_id:
                msg = _('Please set a journal for Peppol invoices on %s before receiving documents.', edi_user.company_id.display_name)
                if skip_no_journal:
                    _logger.warning(msg)
                else:
                    raise UserError(msg)

            params['domain']['receiver_identifier'] = edi_user.edi_identification
            try:
                # request all messages that haven't been acknowledged
                messages = edi_user._call_peppol_proxy(
                    "/api/peppol/1/get_all_documents",
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

            need_retrigger = need_retrigger or len(message_uuids) > job_count
            message_uuids = message_uuids[:job_count]

            created_moves = self.env['account.move']
            uuids_to_ack = []
            # retrieve attachments for filtered messages
            all_messages = edi_user._call_peppol_proxy(
                "/api/peppol/1/get_document",
                params={'message_uuids': message_uuids},
            )
            for uuid, content in all_messages.items():
                enc_key = content["enc_key"]
                document_content = content["document"]
                filename = content["filename"] or 'attachment'  # default to attachment, which should not usually happen
                decoded_document = edi_user._decrypt_data(document_content, enc_key)
                attachment = self.env["ir.attachment"].create({
                    "name": f"{filename}.xml",
                    "raw": decoded_document,
                    "type": "binary",
                    "mimetype": "application/xml",
                })
                try:
                    vals_to_ack = edi_user._peppol_import_invoice(attachment, content["state"], uuid)
                    if move_to_ack := vals_to_ack.get('move'):
                        created_moves |= move_to_ack
                    if uuid_to_ack := vals_to_ack.get('uuid'):
                        uuids_to_ack.append(uuid_to_ack)
                except Exception as e:  # noqa: BLE001
                    _logger.error('Error while processing the Peppol document with uuid %s: %s', uuid, e)

            if not (modules.module.current_test or tools.config['test_enable']):
                self.env.cr.commit()
            if uuids_to_ack:
                edi_user._call_peppol_proxy(
                    "/api/peppol/1/ack",
                    params={'message_uuids': uuids_to_ack},
                )

        if need_retrigger:
            self.env.ref('account_peppol.ir_cron_peppol_get_new_documents')._trigger()

    def _peppol_get_message_status(self):
        # Context added to not break stable policy: useful to tweak on databases processing large invoices
        job_count = self.env.context.get('peppol_crons_job_count') or BATCH_SIZE
        need_retrigger = False
        for edi_user in self:
            edi_user = edi_user.with_company(edi_user.company_id)
            edi_user_moves = self.env['account.move'].search(
                [
                    ('peppol_move_state', '=', 'processing'),
                    ('company_id', '=', edi_user.company_id.id),
                ],
                limit=job_count + 1,
            )
            if not edi_user_moves:
                continue

            need_retrigger = need_retrigger or len(edi_user_moves) > job_count
            message_uuids = {move.peppol_message_uuid: move for move in edi_user_moves[:job_count]}
            messages_to_process = edi_user._call_peppol_proxy(
                "/api/peppol/1/get_document",
                params={'message_uuids': list(message_uuids.keys())},
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
                if error_vals := content.get('error'):
                    if error_vals['code'] == 702:
                        # "Peppol request not ready" error:
                        # thrown when the IAP is still processing the message
                        continue

                    move.peppol_move_state = 'error'
                    error_message = get_peppol_error_message(self.env, error_vals)
                    move._message_log(body=error_message)
                    continue

                move.peppol_move_state = content['state']
                move._message_log(body=_('Peppol status update: %s', content['state']))

            edi_user._call_peppol_proxy(
                "/api/peppol/1/ack",
                params={'message_uuids': list(message_uuids.keys())},
            )

        if need_retrigger:
            self.env.ref('account_peppol.ir_cron_peppol_get_message_status')._trigger()

    def _peppol_get_participant_status(self):
        for edi_user in self:
            edi_user = edi_user.with_company(edi_user.company_id)
            if edi_user.proxy_type != 'peppol':
                continue
            try:
                proxy_user = edi_user._make_request(f"{edi_user._get_server_url()}/api/peppol/2/participant_status")
            except AccountEdiProxyError as e:
                if e.code == 'client_gone':
                    # reset the connection if it was archived/deleted on IAP side
                    edi_user.sudo().company_id._reset_peppol_configuration()
                    edi_user.action_archive()
                else:
                    # don't auto-deregister users on any other errors to avoid settings client-side to states
                    # that are not recoverable without user action if an error on IAP side ever occurs
                    _logger.error('Error while updating Peppol participant status: %s', e)
                continue

            if 'error' in proxy_user:
                error_message = proxy_user['error'].get('message') or proxy_user['error'].get('data', {}).get('message')
                _logger.error('Error while updating Peppol participant status: %s', error_message)
                continue

            local_state = {
                'draft': 'not_registered',
                'sender': 'sender',
                'smp_registration': 'smp_registration',
                'receiver': 'receiver',
                'rejected': 'rejected',
            }.get(proxy_user.get('peppol_state'))

            if local_state == 'not_registered':
                edi_user.sudo().company_id._reset_peppol_configuration()
                edi_user.action_archive()
            elif local_state:
                edi_user.company_id.account_peppol_proxy_state = local_state
            else:
                _logger.warning("Received unknown Peppol state '%s' for EDI proxy user id=%s", proxy_user.get('peppol_state'), edi_user.id)
    # -------------------------------------------------------------------------
    # BUSINESS ACTIONS
    # -------------------------------------------------------------------------

    def _get_company_details(self):
        # DEPRECATED - to remove in master
        self.ensure_one()
        return self.env['peppol.registration']._get_company_details(self.company_id)

    def _peppol_register_sender(self, peppol_external_provider=None):
        # DEPRECATED - to remove in master
        self.ensure_one()

    def _peppol_register_sender_as_receiver(self):
        self.ensure_one()
        company = self.company_id

        if company.account_peppol_proxy_state != 'sender':
            # a participant can only try registering as a receiver if they are currently a sender
            peppol_states = dict(self.env['ir.model.fields'].get_field_selection('res.company', 'account_peppol_proxy_state'))[company.account_peppol_proxy_state]  # handles translation correctly
            raise UserError(
                _('Cannot register a user with a %s application', peppol_states))

        edi_identification = self._get_proxy_identification(company, 'peppol')
        peppol_info = company._get_company_info_on_peppol(edi_identification)
        is_on_peppol, external_provider, error_msg = peppol_info['is_on_peppol'], peppol_info['external_provider'], peppol_info['error_msg']
        if is_on_peppol:
            company.peppol_external_provider = external_provider
            raise UserError(error_msg)

        self._call_peppol_proxy(
            endpoint='/api/peppol/1/register_sender_as_receiver',
            params={
                'migration_key': company.sudo().account_peppol_migration_key,
                'supported_identifiers': list(company._peppol_supported_document_types())
            },
        )
        # once we sent the migration key over, we don't need it
        # but we need the field for future in case the user decided to migrate away from Odoo
        company.sudo().account_peppol_migration_key = False
        company.account_peppol_proxy_state = 'smp_registration'
        company.peppol_external_provider = None

        self.env.ref('account_peppol.ir_cron_peppol_get_participant_status')._trigger(at=fields.Datetime.now() + timedelta(hours=1))

    @handle_demo
    def _peppol_deregister_participant(self):
        self.ensure_one()

        proxy_state = None
        try:
            # call _make_request directly because _peppol_get_participant_status()
            # is cron-safe and swallows AccountEdiProxyError.
            proxy_user = self._make_request(f"{self._get_server_url()}/api/peppol/2/participant_status")
            proxy_state = proxy_user.get('peppol_state')
        except AccountEdiProxyError as e:
            # If user no longer exists on IAP side, don't try to fetch docs/statuses (they will fail).
            if e.code not in ['client_gone', 'no_such_user_found']:
                raise
        if proxy_state in ('sender', 'smp_registration', 'receiver'):
            # fetch all documents and message statuses before unlinking the edi user
            # so that the invoices are acknowledged
            self._cron_peppol_get_message_status()
            self._cron_peppol_get_new_documents()
            if not modules.module.current_test:
                self.env.cr.commit()

            self._call_peppol_proxy(endpoint='/api/peppol/1/cancel_peppol_registration')

        self.company_id._reset_peppol_configuration()
        self.unlink()

    def _peppol_deregister_participant_to_sender(self):
        self.ensure_one()

        if self.company_id.account_peppol_proxy_state == 'receiver':
            # fetch all documents and message statuses before unlinking the edi user
            # so that the invoices are acknowledged
            self._cron_peppol_get_message_status()
            self._cron_peppol_get_new_documents()
            if not modules.module.current_test:
                self.env.cr.commit()

        self._call_peppol_proxy(endpoint='/api/peppol/1/unregister_to_sender')
        self.company_id.account_peppol_proxy_state = 'sender'

    @api.model
    def _peppol_auto_register_services(self, module):
        # DEPRECATED - to remove in master
        pass

    @api.model
    def _peppol_auto_deregister_services(self, module):
        # DEPRECATED - to remove in master
        pass

    def _peppol_get_services(self):
        """Get information from the IAP regarding the Peppol services."""
        self.ensure_one()
        return self._call_peppol_proxy("/api/peppol/2/get_services")

    @api.model
    def _generate_webhook_token(self, company):
        expiration = 30 * 24  # in 30 days
        msg = [company.id, company._get_peppol_webhook_endpoint()]
        payload = tools.hash_sign(self.sudo().env, 'account_peppol_webhook', msg, expiration_hours=expiration)
        return payload

    @api.model
    def _get_user_from_token(self, token: str, url: str):
        try:
            if not (payload := tools.verify_hash_signed(self.sudo().env, 'account_peppol_webhook', token)):
                return None
        except ValueError:
            return None
        else:
            id, endpoint = payload
            if not url.startswith(endpoint):
                return None
            company = self.env['res.company'].browse(id).exists()
            if company and company.account_peppol_edi_user:
                return company.account_peppol_edi_user
            if edi_user := self.browse(id).exists():
                # Legacy fallback: we no longer generate the token based on the proxy_user, as it does
                # not exists yet with the new creation flow.
                # This can be safely removed after beginning of March 2026 (webhooks TTL = 30 days).
                return edi_user
            return None

    def _peppol_reset_webhook(self):
        for edi_user in self:
            edi_user._call_peppol_proxy('/api/peppol/2/set_webhook', params={'webhook_url': edi_user.company_id._get_peppol_webhook_endpoint(), 'token': self._generate_webhook_token(edi_user.company_id)})
