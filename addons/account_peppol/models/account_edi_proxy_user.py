# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import _, api, models, tools
from odoo.addons.account_edi_proxy_client.models.account_edi_proxy_user import AccountEdiProxyError
from odoo.addons.account_peppol.tools.demo_utils import handle_demo

_logger = logging.getLogger(__name__)
BATCH_SIZE = 50


class AccountEdiProxyClientUser(models.Model):
    _inherit = 'account_edi_proxy_client.user'

    # -------------------------------------------------------------------------
    # HELPER METHODS
    # -------------------------------------------------------------------------

    def _get_server_url_new(self, edi_format=None):
        if (edi_format or self.edi_format_id).code == 'peppol':
            return {
                'prod': 'https://peppol.api.odoo.com',
                'test': 'https://peppol.test.odoo.com',
            }.get(self._get_demo_state(), 'demo')
        return super()._get_server_url_new(edi_format=edi_format)

    def _get_route(self, action, edi_format=None):
        if (edi_format or self.edi_format_id).code == 'peppol':
            return {
                'create_user': '/iap/account_edi/2/create_user',
                'renew_token': '/iap/account_edi/1/renew_token',
            }.get(action) or super()._get_route(action, edi_format=edi_format)
        return super()._get_route(action, edi_format=edi_format)

    def _get_create_user_edi_params(self, company, edi_format, edi_identification):
        if edi_format.code == 'peppol':
            return {
                'proxy_type': edi_format.code,
                'edi_identification': edi_identification,
            }
        return super()._get_create_user_edi_params(company, edi_format, edi_identification)

    def _make_request(self, url, params=False):
        if self.edi_format_id.code == 'peppol':
            return self._make_request_peppol(url, params=params)
        return super()._make_request(url, params=params)

    @handle_demo
    def _make_request_peppol(self, url, params=False):
        return super()._make_request(url, params)

    # -------------------------------------------------------------------------
    # CRONS
    # -------------------------------------------------------------------------

    def _cron_peppol_get_new_documents(self):
        edi_users = self.search([('company_id.account_peppol_proxy_state', '=', 'active'), ('edi_format_id.code', '=', 'peppol')])
        edi_users._peppol_get_new_documents()

    def _cron_peppol_get_message_status(self):
        edi_users = self.search([('company_id.account_peppol_proxy_state', '=', 'active'), ('edi_format_id.code', '=', 'peppol')])
        edi_users._peppol_get_message_status()

    def _cron_peppol_get_participant_status(self):
        edi_users = self.search([('company_id.account_peppol_proxy_state', '!=', 'not_registered'), ('edi_format_id.code', '=', 'peppol')])
        edi_users._peppol_get_participant_status()

        # check if any of the users that were disabled (for whatever reason) can be re-enabled
        disabled_companies = self.with_context(active_test=False).search([('edi_format_id.code', '=', 'peppol'), ('active', '=', False)]).company_id
        for disabled_company in disabled_companies:
            self._try_recover_peppol_proxy_users(disabled_company)

    # -------------------------------------------------------------------------
    # BUSINESS ACTIONS
    # -------------------------------------------------------------------------

    @api.model
    def _try_recover_peppol_proxy_users(self, company, *, peppol_identifier=None):
        """Try to recover a soft-deleted PEPPOL proxy user.

        :param company: Company to recover user for
        :param peppol_identifier: Optional specific identifier to recover
        :returns: Recovered user record or None
        """
        company.ensure_one()
        # if there are existing active users, there is nothing to recover
        # explicitly check with active_test, see https://github.com/odoo/odoo/commit/4c46b696f3af73c982ba92f25d71afe8fc825ed0
        if any((
            company.with_context(active_test=True).account_edi_proxy_client_ids.filtered(lambda user: user.edi_format_id.code == 'peppol'),
            company.account_peppol_proxy_state != 'not_registered',
        )):
            return

        # in case the user was soft deleted, we can try again to recover him
        # e.g. because of refresh_token API returning no_such_user for any peppol users
        # between 2025-09-02 07:20:00 UTC and 2025-09-02 15:30:00 UTC
        domain = [
            ('edi_format_id.code', '=', 'peppol'),
            ('active', '=', False),
            ('refresh_token', '!=', False),
            ('company_id', '=', company.id),
        ]
        if peppol_identifier:
            domain.append(('edi_identification', '=', peppol_identifier))
        user = self.env['account_edi_proxy_client.user'].search(domain, limit=2).filtered(lambda u: u._get_demo_state() != 'demo')

        if len(user) != 1:
            # if there is more than one user, we won't decide which one to recover
            return

        try:
            with self.env.cr.savepoint():
                # fetch state from IAP and update user if relevant
                # _peppol_get_participant_status ignores errors, and here we want to know if it failed
                # _make_request_peppol won't commit on no_such_user error
                proxy_user = user._make_request(f"{user._get_server_url_new()}/api/peppol/1/participant_status")

                state_map = {
                    'active': 'active',
                    'verified': 'pending',
                    'rejected': 'rejected',
                    'canceled': 'canceled',
                    # IAP-side is still draft (needs phone confirmation)
                    # set to pending to match normal registration flow
                    'draft': 'pending'
                }

                if proxy_user.get('peppol_state') in state_map:
                    user.company_id.account_peppol_proxy_state = state_map[proxy_user['peppol_state']]
                    user.active = True
                else:
                    # NOTE: this shouldn't happen, but if it does, we will have refreshed the token
                    # but as it's an unknown state, there is not much we can do with that information
                    return
        except AccountEdiProxyError as e:
            _logger.info("Tried unsuccessfully to recover EDI proxy user id=%s (%s)", user.id, e)
        else:
            _logger.info("PEPPOL recovery completed. Recovered user id=%s.", user.id)
            return user

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
                    url=f"{edi_user._get_server_url_new()}/api/peppol/1/get_all_documents",
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
                    ('company_id', '=', company.id),
                    ('type', '=', 'purchase')
                ], limit=1)

            need_retrigger = need_retrigger or len(message_uuids) > job_count
            message_uuids = message_uuids[:job_count]
            proxy_acks = []

            # retrieve attachments for filtered messages
            all_messages = edi_user._make_request(
                f"{edi_user._get_server_url_new()}/api/peppol/1/get_document",
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
                    f"{edi_user._get_server_url_new()}/api/peppol/1/ack",
                    {'message_uuids': proxy_acks},
                )

        if need_retrigger:
            self.env.ref('account_peppol.ir_cron_peppol_get_new_documents')._trigger()

    def _peppol_get_message_status(self):
        # Context added to not break stable policy: useful to tweak on databases processing large invoices
        job_count = self._context.get('peppol_crons_job_count') or BATCH_SIZE
        need_retrigger = False
        for edi_user in self:
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
            messages_to_process = edi_user._make_request(
                f"{edi_user._get_server_url_new()}/api/peppol/1/get_document",
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
                f"{edi_user._get_server_url_new()}/api/peppol/1/ack",
                {'message_uuids': list(message_uuids.keys())},
            )

        if need_retrigger:
            self.env.ref('account_peppol.ir_cron_peppol_get_message_status')._trigger()

    def _peppol_get_participant_status(self):
        for edi_user in self:
            try:
                proxy_user = edi_user._make_request(f"{edi_user._get_server_url_new()}/api/peppol/1/participant_status")
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
