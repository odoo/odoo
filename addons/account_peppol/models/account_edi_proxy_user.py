# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from lxml import etree

from odoo import _, api, fields, models, tools
from odoo.tools.misc import format_list
from odoo.addons.account_edi_proxy_client.models.account_edi_proxy_user import AccountEdiProxyError
from odoo.addons.account_peppol.tools.demo_utils import handle_demo
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)
BATCH_SIZE = 50


class AccountEdiProxyClientUser(models.Model):
    _inherit = 'account_edi_proxy_client.user'

    peppol_verification_code = fields.Char(string='SMS verification code')
    proxy_type = fields.Selection(selection_add=[('peppol', 'PEPPOL')], ondelete={'peppol': 'cascade'})

    # -------------------------------------------------------------------------
    # HELPER METHODS
    # -------------------------------------------------------------------------

    def _make_request(self, url, params=False):
        if self.proxy_type in self._get_peppol_proxy_types():
            return self._make_request_peppol(url, params=params)
        return super()._make_request(url, params=params)

    @handle_demo
    def _make_request_peppol(self, url, params=False):
        peppol_proxy_types = self._get_peppol_proxy_types()
        if self.proxy_type not in peppol_proxy_types:
            proxy_type_map = dict(self._fields['proxy_type']._description_selection(self.env))
            proxy_types = [proxy_type_map[proxy_type] for proxy_type in peppol_proxy_types]
            raise UserError(_('EDI user should be of one of the following types: %s', format_list(self.env, proxy_types, 'or')))
        return super()._make_request(url, params)

    def _call_peppol_proxy(self, endpoint, params=None):
        errors = {
            'code_incorrect': _('The verification code is not correct'),
            'code_expired': _('This verification code has expired. Please request a new one.'),
            'too_many_attempts': _('Too many attempts to request an SMS code. Please try again later.'),
        }

        params = params or {}
        try:
            response = self._make_request(
                f"{self._get_server_url()}{endpoint}",
                params=params,
            )
        except AccountEdiProxyError as e:
            raise UserError(e.message)

        if 'error' in response:
            error_code = response['error'].get('code')
            error_message = response['error'].get('message') or response['error'].get('data', {}).get('message')
            raise UserError(errors.get(error_code) or error_message or _('Connection error, please try again later.'))
        return response

    @api.model
    def _get_peppol_proxy_types(self):
        return ['peppol']

    def _get_proxy_urls(self):
        urls = super()._get_proxy_urls()
        urls['peppol'] = {
            'prod': 'https://peppol.api.odoo.com',
            'test': 'https://peppol.test.odoo.com',
            'demo': 'demo',
        }
        return urls

    def _get_peppol_proxy_endpoint(self, endpoint, proxy_type=None):
        """The `endpoint` should include the number; be like `2/participant_status`"""
        if not proxy_type:
            self.ensure_one()
            proxy_type = self.proxy_type
        return f"/api/{proxy_type}/{endpoint}"

    # -------------------------------------------------------------------------
    # CRONS
    # -------------------------------------------------------------------------

    def _cron_peppol_get_new_documents(self):
        edi_users = self.search([('company_id.account_peppol_proxy_state', '=', 'active'), ('proxy_type', 'in', self._get_peppol_proxy_types())])
        edi_users._peppol_get_new_documents()

    def _cron_peppol_get_message_status(self):
        edi_users = self.search([('company_id.account_peppol_proxy_state', 'in', ('active', 'sender')), ('proxy_type', 'in', self._get_peppol_proxy_types())])
        edi_users._peppol_get_message_status()

    # -------------------------------------------------------------------------
    # BUSINESS ACTIONS
    # -------------------------------------------------------------------------

    def _peppol_register_receiver(self):
        # remove in master
        self.ensure_one()
        params = {
            'company_details': self._get_company_details(),
            'supported_identifiers': list(self.company_id._peppol_supported_document_types())
        }
        self._call_peppol_proxy(
            endpoint=self._get_peppol_proxy_endpoint('1/register_receiver'),
            params=params,
        )
        self.company_id.account_peppol_proxy_state = 'pending'

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
            company.with_context(active_test=True).account_edi_proxy_client_ids.filtered(lambda user: user.proxy_type == 'peppol'),
            company.sudo().account_peppol_migration_key,
            company.account_peppol_proxy_state != 'not_registered',
        )):
            return

        # in case the user was soft deleted, we can try again to recover him
        # e.g. because of refresh_token API returning no_such_user for any peppol users
        # between 2025-09-02 07:20:00 UTC and 2025-09-02 15:30:00 UTC
        domain = [
            ('proxy_type', 'in', self._get_peppol_proxy_types()),
            ('active', '=', False),
            ('refresh_token', '!=', False),
            ('edi_mode', '!=', 'demo'),
            ('company_id', '=', company.id),
        ]
        if peppol_identifier:
            domain.append(('edi_identification', '=', peppol_identifier))
        user = self.env['account_edi_proxy_client.user'].search(domain, limit=2)

        if len(user) != 1:
            # if there is more than one user, we won't decide which one to recover
            return

        try:
            # fetch state from IAP and update user if relevant
            # _peppol_get_participant_status ignores errors, and here we want to know if it failed
            # _make_request_peppol won't commit on no_such_user error
            proxy_user = user._make_request(user._get_server_url() + user._get_peppol_proxy_endpoint('1/participant_status'))

            state_map = {'active': 'active', 'sender': 'sender', 'verified': 'pending', 'rejected': 'rejected'}

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
                    url=edi_user._get_server_url() + edi_user._get_peppol_proxy_endpoint('1/get_all_documents'),
                    params=params,
                )
            except AccountEdiProxyError as e:
                _logger.error(
                    'Error while receiving the document from Peppol Proxy: %s', e.message)
                continue

            received_messages = messages.get('messages', [])
            # Edge case: self-addressed messages (sender == receiver), i.e. a company genuinely
            # invoicing itself. The outgoing invoice already carries the message UUID, so the
            # duplicate check would wrongly discard the incoming document.
            # Exclude those messages from the check so the vendor bill can still be created.
            uuids_to_check = [
                message['uuid'] for message in received_messages
                if message.get('sender') and message['sender'] != message['receiver']
            ]
            # Acknowledge the duplicates on IAP side.
            if duplicate_message_uuids := set(
                self.env['account.move'].search([
                    ('peppol_message_uuid', 'in', uuids_to_check),
                    ('company_id', '=', edi_user.company_id.id),
                ])
                .mapped('peppol_message_uuid')
            ):
                edi_user._make_request(
                    edi_user._get_server_url() + edi_user._get_peppol_proxy_endpoint('1/ack'),
                    {'message_uuids': list(duplicate_message_uuids)},
                )
                _logger.info(
                    "Messages with UUID %s could not be imported because they are identified as duplicates",
                    ', '.join(duplicate_message_uuids)
                )

            # Remove the duplicates
            message_uuids = [
                message['uuid'] for message in received_messages
                if message['uuid'] not in duplicate_message_uuids
            ]

            if not message_uuids:
                continue

            need_retrigger = need_retrigger or len(message_uuids) > job_count
            message_uuids = message_uuids[:job_count]

            # retrieve attachments for filtered messages
            all_messages = edi_user._make_request(
                edi_user._get_server_url() + edi_user._get_peppol_proxy_endpoint('1/get_document'),
                {'message_uuids': message_uuids},
            )

            processed_uuids, moves = edi_user.with_context(_from_peppol_get_new_documents=True)._peppol_process_new_messages(all_messages)

            if not tools.config['test_enable']:
                self.env.cr.commit()
            if processed_uuids:
                edi_user._make_request(
                    edi_user._get_server_url() + edi_user._get_peppol_proxy_endpoint('1/ack'),
                    {'message_uuids': processed_uuids},
                )
                edi_user._peppol_post_process_new_messages(moves)

        if need_retrigger:
            self.env.ref('account_peppol.ir_cron_peppol_get_new_documents')._trigger()

    def _peppol_get_filetype(self, content):
        return "xml", "application/xml"

    def _peppol_get_decoded_document(self, content):
        enc_key = content["enc_key"]
        document_content = content["document"]
        return self._decrypt_data(document_content, enc_key)

    def _peppol_process_new_messages(self, messages):
        self.ensure_one()
        company = self.company_id
        processed_uuids = []
        moves = self.env['account.move']
        for uuid, content in messages.items():
            fileextension, mimetype = self._peppol_get_filetype(content)
            filename = content["filename"] or 'attachment'  # default to attachment, which should not usually happen
            attachment_vals = {
                'name': f'{filename}.{fileextension}',
                'raw': self._peppol_get_decoded_document(content),
                'type': 'binary',
                'mimetype': mimetype,
            }

            try:
                attachment = self.env['ir.attachment'].create(attachment_vals)
                xml_tree = etree.fromstring(attachment.raw)
                invoice_type_code = xml_tree.findtext('.//{*}InvoiceTypeCode')
                credit_note_type_code = xml_tree.findtext('.//{*}CreditNoteTypeCode')

                if invoice_type_code in ['389', '527'] or credit_note_type_code == '261':
                    # 389/527: Self-billing invoice; 261: Self-billing credit note
                    journal = self.env['account.journal'].search(
                        [
                            *self.env['account.journal']._check_company_domain(company),
                            ('type', '=', 'sale'),
                        ],
                        limit=1,
                    )
                    move_type = 'out_invoice' if invoice_type_code else 'out_refund'
                else:
                    # use the first purchase journal if the Peppol journal is not set up
                    # to create the move anyway
                    journal = company.peppol_purchase_journal_id or self.env['account.journal'].search([
                        *self.env['account.journal']._check_company_domain(company),
                        ('type', '=', 'purchase')
                    ], limit=1)
                    move_type = 'in_invoice'

                move = journal\
                    .with_company(company) \
                    .with_context(
                        default_move_type=move_type,
                        default_peppol_move_state=content['state'],
                        default_peppol_message_uuid=uuid,
                        default_journal_id=journal.id,
                    )\
                    ._create_document_from_attachment(attachment.id)
                move._message_log(body=_('%(proxy_type)s document has been received successfully',
                                         proxy_type=dict(self._fields['proxy_type']._description_selection(self.env))[self.proxy_type]))
                moves += move
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
                moves += move
                attachment_vals.update({
                    'res_model': 'account.move',
                    'res_id': move.id,
                })
                self.env['ir.attachment'].create(attachment_vals)
                _logger.exception('Error while processing the Peppol document with uuid %s', uuid)
            if 'is_in_extractable_state' in move._fields:
                move.is_in_extractable_state = False

            processed_uuids.append(uuid)

        return processed_uuids, moves

    def _peppol_post_process_new_messages(self, moves):
        self.ensure_one()
        for partner in moves.partner_id.filtered(lambda partner: partner.account_peppol_verification_label in ('not_verified', False)):
            partner.button_account_peppol_check_partner_endpoint()

    def _peppol_get_message_status(self):
        # Context added to not break stable policy: useful to tweak on databases processing large invoices
        job_count = self._context.get('peppol_crons_job_count') or BATCH_SIZE
        need_retrigger = False
        for edi_user in self:
            documents = edi_user._peppol_get_documents_for_status(job_count)
            if not documents:
                continue

            need_retrigger = need_retrigger or len(documents) > job_count
            uuid_to_record = {document.peppol_message_uuid: document for document in documents[:job_count]}
            messages_to_process = edi_user._make_request(
                edi_user._get_server_url() + edi_user._get_peppol_proxy_endpoint('1/get_document'),
                params={'message_uuids': list(uuid_to_record)},
            )

            processed_message_uuids = edi_user._peppol_process_messages_status(messages_to_process, uuid_to_record)

            if processed_message_uuids:
                edi_user._make_request(
                    edi_user._get_server_url() + edi_user._get_peppol_proxy_endpoint('1/ack'),
                    {'message_uuids': processed_message_uuids},
                )

        if need_retrigger:
            self.env.ref('account_peppol.ir_cron_peppol_get_message_status')._trigger()

    def _peppol_process_messages_status(self, messages, uuid_to_record):
        self.ensure_one()
        processed_message_uuids = []

        for uuid, content in messages.items():
            move = uuid_to_record[uuid]
            if content.get('error'):
                # "Peppol request not ready" error:
                # thrown when the IAP is still processing the message
                if content['error'].get('code') == 702:
                    continue

                move.peppol_move_state = 'error'
                move._message_log(body=self._peppol_get_message_status_error_body(move, content['error']))
                continue

            move.peppol_move_state = content['state']
            move._message_log(body=self._peppol_get_message_status_update_body(move, content))
            processed_message_uuids.append(uuid)
        return processed_message_uuids

    def _peppol_get_message_status_error_body(self, move, error):
        self.ensure_one()
        return _("Peppol error: %s", error.get('data', {}).get('message') or error['message'])

    def _peppol_get_message_status_update_body(self, move, content):
        self.ensure_one()
        return _('Peppol status update: %s', content['state'])

    def _peppol_get_documents_for_status(self, batch_size):
        self.ensure_one()
        edi_user_moves = self.env['account.move'].search(
            [
                ('peppol_move_state', '=', 'processing'),
                ('company_id', '=', self.company_id.id),
            ],
            limit=batch_size + 1,
        )
        return list(edi_user_moves)

    def _cron_peppol_get_participant_status(self):
        edi_users = self.search([('company_id.account_peppol_proxy_state', '!=', 'not_registered'), ('proxy_type', 'in', self._get_peppol_proxy_types())])
        edi_users._peppol_get_participant_status()

        # check if any of the users that were disabled (for whatever reason) can be re-enabled
        disabled_companies = self.with_context(active_test=False).search([('proxy_type', 'in', self._get_peppol_proxy_types()), ('active', '=', False)]).company_id
        for disabled_company in disabled_companies:
            self._try_recover_peppol_proxy_users(disabled_company)

    def _peppol_process_participant_status_get_local_state_map(self):
        self.ensure_one()
        return {
            'draft': 'not_registered',
            'active': 'active',
            'sender': 'sender',
            'verified': 'pending',
            'rejected': 'rejected',
        }

    def _peppol_process_participant_status(self, proxy_user):
        self.ensure_one()

        local_state = self._peppol_process_participant_status_get_local_state_map().get(proxy_user.get('peppol_state'))

        if local_state == 'not_registered':
            self.sudo().company_id._reset_peppol_configuration()
        elif local_state:
            self.company_id.account_peppol_proxy_state = local_state
        else:
            _logger.warning("Received unknown Peppol state '%s' for EDI proxy user id=%s", proxy_user.get('peppol_state'), self.id)

    def _peppol_get_participant_status(self):
        for edi_user in self:
            try:
                proxy_user = edi_user._make_request(
                    edi_user._get_server_url() + edi_user._get_peppol_proxy_endpoint('1/participant_status'))
            except AccountEdiProxyError as e:
                if e.code == 'client_gone':
                    # reset the connection if it was archived/deleted on IAP side
                    edi_user.sudo().company_id._reset_peppol_configuration()
                else:
                    # don't auto-deregister users on any other errors to avoid settings client-side to states
                    # that are not recoverable without user action if an error on IAP side ever occurs
                    _logger.error('Error while updating Peppol participant status: %s', e)
                continue

            edi_user._peppol_process_participant_status(proxy_user)

    def _get_company_details(self):
        self.ensure_one()
        return {
            'peppol_company_name': self.company_id.display_name,
            'peppol_company_vat': self.company_id.vat,
            'peppol_company_street': self.company_id.street,
            'peppol_company_city': self.company_id.city,
            'peppol_company_zip': self.company_id.zip,
            'peppol_country_code': self.company_id.country_id.code,
            'peppol_phone_number': self.company_id.account_peppol_phone_number,
            'peppol_contact_email': self.company_id.account_peppol_contact_email,
            'peppol_migration_key': self.company_id.sudo().account_peppol_migration_key,
        }

    @api.model
    def _peppol_auto_deregister_services(self, module):
        """Unregister a set of document types for all recipient users.

        This function should be run in the uninstall hook of any module that extends the supported
        document types.

        :param module: Module from which this function is being called, allows us to determine which
            document types are no longer supported.
        """
        receivers = self.search([
            ('proxy_type', 'in', self._get_peppol_proxy_types()),
            ('company_id.account_peppol_proxy_state', '=', 'active')
        ])
        unsupported_identifiers = list(self.env['res.company']._peppol_modules_document_types().get(module, {}))
        for receiver in receivers:
            try:
                receiver._call_peppol_proxy(
                    receiver._get_peppol_proxy_endpoint('2/remove_services'),
                    params={'document_identifiers': unsupported_identifiers},
                )
            except (AccountEdiProxyError, UserError) as exception:
                _logger.error(
                    'Auto deregistration of peppol services for module: %s failed on the user: %s, with exception: %s',
                    module, receiver.edi_identification, exception,
                )
