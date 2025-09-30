import logging
from lxml import etree
from markupsafe import Markup

from odoo import api, fields, models, modules, tools, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.business_data import split_vat

from odoo.addons.account_edi_proxy_client.models.account_edi_proxy_user import AccountEdiProxyError
from odoo.addons.l10n_dk.tools.demo_utils import handle_demo

_logger = logging.getLogger(__name__)
BATCH_SIZE = 50


class AccountEdiProxyClientUser(models.Model):
    _inherit = 'account_edi_proxy_client.user'

    nemhandel_verification_code = fields.Char(string='Nemhandel SMS verification code')
    proxy_type = fields.Selection(selection_add=[('nemhandel', 'Nemhandel')], ondelete={'nemhandel': 'cascade'})

    # -------------------------------------------------------------------------
    # HELPER METHODS
    # -------------------------------------------------------------------------

    def _get_proxy_urls(self):
        urls = super()._get_proxy_urls()
        urls['nemhandel'] = {
            'prod': 'https://nemhandel.api.odoo.com',
            'test': 'https://nemhandel.test.odoo.com',
            'demo': 'demo',
        }
        return urls

    @handle_demo
    def _call_nemhandel_proxy(self, endpoint, params=None):
        self.ensure_one()
        if self.proxy_type != 'nemhandel':
            raise UserError(_('EDI user should be of type Nemhandel'))

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
            error_message = response['error'].get('subject') or response['error'].get('data', {}).get('message')
            raise UserError(errors.get(error_code) or error_message or _('Connection error, please try again later.'))
        return response

    @handle_demo
    def _check_user_on_alternative_service(self):
        status = self._call_nemhandel_proxy('/api/nemhandel/1/check_user_valid')
        if status and status.get('status') != 'valid':
            error_msg = _(
                "A participant with these details has already been registered on the network. "
                "If you have previously registered to an alternative Nemhandel service, please deregister"
            )

            raise UserError(error_msg)

    # -------------------------------------------------------------------------
    # CRONS
    # -------------------------------------------------------------------------

    def _cron_nemhandel_get_new_documents(self):
        edi_users = self.search([('proxy_type', '=', 'nemhandel'), ('company_id.l10n_dk_nemhandel_proxy_state', '=', 'receiver')])
        edi_users._nemhandel_get_new_documents(skip_no_journal=True)

    def _cron_nemhandel_get_message_status(self):
        edi_users = self.search([('proxy_type', '=', 'nemhandel'), ('company_id.l10n_dk_nemhandel_proxy_state', '=', 'receiver')])
        edi_users._nemhandel_get_message_status()

    def _cron_nemhandel_get_participant_status(self):
        edi_users = self.search([('proxy_type', '=', 'nemhandel')])
        edi_users._nemhandel_get_participant_status()

    def _cron_nemhandel_webhook_keepalive(self):
        edi_users = self.search([('proxy_type', '=', 'nemhandel'), ('company_id.l10n_dk_nemhandel_proxy_state', '=', 'receiver')])
        edi_users._nemhandel_reset_webhook()

    # -------------------------------------------------------------------------
    # BUSINESS ACTIONS
    # -------------------------------------------------------------------------

    def _get_proxy_identification(self, company, proxy_type):
        if proxy_type != 'nemhandel':
            return super()._get_proxy_identification(company, proxy_type)
        if not company.nemhandel_identifier_type or not company.nemhandel_identifier_value:
            raise UserError(_("Please fill in the Identifier Type and Value."))
        return f'{company.nemhandel_identifier_type}:{company.nemhandel_identifier_value}'

    def _register_proxy_user(self, company, proxy_type, edi_mode):
        ''' Override to avoid using the deprecated route on IAP '''
        if proxy_type != 'nemhandel':
            return super()._register_proxy_user(company, proxy_type, edi_mode)

        private_key_sudo = self.env['certificate.key'].sudo()._generate_rsa_private_key(
            company,
            name=f"{proxy_type}_{edi_mode}_{company.id}.key",
        )
        nemhandel_identifier = self._get_proxy_identification(company, proxy_type)
        if edi_mode == 'demo':
            # simulate registration
            response = {'id_client': f'demo{company.id}{proxy_type}', 'refresh_token': 'demo'}
        else:
            try:
                # b64encode returns a bytestring, we need it as a string
                response = self._make_request(self._get_server_url(proxy_type, edi_mode) + '/api/nemhandel/1/connect', params={
                    'dbuuid': company.env['ir.config_parameter'].get_str('database.uuid'),
                    'company_id': company.id,
                    'nemhandel_identifier': nemhandel_identifier,
                    'public_key': private_key_sudo._get_public_key_bytes(encoding='pem').decode(),
                })
            except AccountEdiProxyError as e:
                raise UserError(e.message)

        return self.create({
            'id_client': response['id_client'],
            'company_id': company.id,
            'proxy_type': proxy_type,
            'edi_mode': edi_mode,
            'edi_identification': nemhandel_identifier,
            'private_key_id': private_key_sudo.id,
            'refresh_token': response['refresh_token'],
        })

    @api.model
    def _nemhandel_extract_response_info(self, document):
        doc_tree = etree.fromstring(document)
        blr_status = doc_tree.find('{*}DocumentResponse/{*}Response/{*}ResponseCode').text
        descriptions = doc_tree.findall('{*}DocumentResponse/{*}Response/{*}Description')

        note = Markup()
        if descriptions:
            for description in descriptions:
                note += Markup('<br>{}').format(description.text or self.env._("N/A"))
        return blr_status, note

    def _nemhandel_import_response(self, uuid, content, decoded_document, origin_moves):
        blr_status, note = self._nemhandel_extract_response_info(decoded_document)
        if move := origin_moves.get(content['origin_message_uuid']):
            if blr_status in {'BusinessAccept', 'BusinessReject'}:
                self.env['nemhandel.response'].create({
                    'nemhandel_message_uuid': uuid,
                    'response_code': blr_status,
                    'nemhandel_state': content['state'],
                    'move_id': move.id,
                })
                if content['state'] == 'done':
                    if blr_status == 'BusinessReject':
                        move._message_log(
                            body=self.env._(
                                "The Nemhandel receiver of this document has rejected it with the following information: %s",
                                note,
                            ) if note else self.env._(
                                "The Nemhandel receiver of this document has rejected it.",
                            ),
                        )
                    else:
                        move._message_log(
                            body=self.env._(
                                "The Nemhandel receiver of this document has accepted it with the following information: %s",
                                note,
                            ) if note else self.env._(
                                "The Nemhandel receiver of this document has accepted it.",
                            ),
                        )
            if blr_status in {'TechnicalReject', 'ProfileReject'}:
                move._message_log(
                    body=self.env._(
                        "An issue arose with your Nemhandel document on the partner's side with the following information: %(note)s"
                        "%(br)sPlease contact the support if this issue persists.",
                        note=note,
                        br=Markup('<br>'),
                    ) if note else self.env._(
                        "An issue arose with your Nemhandel document on the partner's side."
                        "%(br)sPlease contact the support if this issue persists.",
                        br=Markup('<br>'),
                    ),
                )

    def _nemhandel_import_invoice(self, attachment, nemhandel_state, uuid, journal=None):
        """Save new documents in an accounting journal, when one is specified on the company.

        :param attachment: the new document
        :param nemhandel_state: the state of the received Nemhandel document
        :param uuid: the UUID of the Nemhandel document
        :return: the created invoice if the document was saved, `False` if it was not
        """
        self.ensure_one()
        journal = journal or self.company_id.nemhandel_purchase_journal_id
        if not journal:
            return False

        move = self.env['account.move'].create({
            'journal_id': journal.id,
            'move_type': 'in_invoice',
            'nemhandel_move_state': nemhandel_state,
            'nemhandel_message_uuid': uuid,
        })
        if 'is_in_extractable_state' in move._fields:
            move.is_in_extractable_state = False

        move._extend_with_attachments(move._to_files_data(attachment), new=True)
        move._message_log(
            body=_(
                "Nemhandel document (UUID: %(uuid)s) has been received successfully.",
                uuid=uuid,
            ),
            attachment_ids=attachment.ids,
        )
        attachment.write({'res_model': 'account.move', 'res_id': move.id})
        return {'uuid': uuid, 'move': move}

    def _nemhandel_get_new_documents(self, skip_no_journal=True, batch_size=None):
        job_count = batch_size or BATCH_SIZE
        need_retrigger = False
        params = {
            'domain': {
                'direction': 'incoming',
                'errors': False,
            }
        }
        for edi_user in self:
            edi_user = edi_user.with_company(edi_user.company_id)
            journal = edi_user.company_id.nemhandel_purchase_journal_id
            if not journal:
                msg = _('Please set a journal for Nemhandel invoices on %s before receiving documents.', edi_user.company_id.display_name)
                if skip_no_journal:
                    _logger.warning(msg)
                else:
                    raise UserError(msg)

            params['domain']['receiver_identifier'] = edi_user.edi_identification
            try:
                # request all messages that haven't been acknowledged
                messages = edi_user._call_nemhandel_proxy(
                    "/api/nemhandel/1/get_all_documents",
                    params=params,
                )
            except UserError as e:
                _logger.error(
                    'Error while receiving the document from Nemhandel Proxy: %s', ', '.join(e.args),
                )
                continue

            message_uuids = [
                message['uuid']
                for message in messages.get('messages', [])
            ]
            if not message_uuids:
                continue

            need_retrigger = need_retrigger or len(message_uuids) > job_count
            message_uuids = message_uuids[:job_count]

            # retrieve attachments for filtered messages
            all_messages = edi_user._call_nemhandel_proxy(
                "/api/nemhandel/1/get_document",
                params={'message_uuids': message_uuids},
            )

            processed_uuids, moves = edi_user._nemhandel_process_new_messages(all_messages)

            if not (modules.module.current_test or tools.config['test_enable']):
                self.env.cr.commit()
            if processed_uuids:
                edi_user._call_nemhandel_proxy(
                    "/api/nemhandel/1/ack",
                    params={'message_uuids': processed_uuids},
                )
                edi_user._nemhandel_post_process_new_messages(moves)
        if need_retrigger:
            self.env.ref('l10n_dk.ir_cron_nemhandel_get_new_documents')._trigger()

    def _nemhandel_process_new_messages(self, messages):
        self.ensure_one()
        processed_uuids = []
        moves = self.env['account.move']
        origin_message_uuids = [content['origin_message_uuid'] for content in messages.values()]
        origin_moves = self.env['account.move'].search([
            ('nemhandel_message_uuid', 'in', origin_message_uuids),
            ('company_id', '=', self.company_id.id),
            ('partner_id', '!=', self.company_id.partner_id.id),
        ]).grouped('nemhandel_message_uuid')
        for uuid, content in messages.items():
            enc_key = content["enc_key"]
            document_content = content["document"]
            decoded_document = self._decrypt_data(document_content, enc_key)
            if content['document_type'] == 'ApplicationResponse':
                self._nemhandel_import_response(uuid, content, decoded_document, origin_moves)
                processed_uuids.append(uuid)
            else:
                filename = content["filename"] or 'attachment'  # default to attachment, which should not usually happen
                attachment = self.env["ir.attachment"].create(
                    {
                        "name": f"{filename}.xml",
                        "raw": decoded_document,
                        "type": "binary",
                        "mimetype": "application/xml",
                    }
                )
                if uuid_move := self._nemhandel_import_invoice(attachment, content["state"], uuid, journal=self.company_id.nemhandel_purchase_journal_id):
                    # Only acknowledge when we saved the document somewhere
                    processed_uuids.append(uuid)
                    moves += uuid_move.get('move', self.env['account.move'])
        return processed_uuids, moves

    def _nemhandel_post_process_new_messages(self, moves):
        self.ensure_one()
        self.company_id.nemhandel_purchase_journal_id._notify_einvoices_received(moves)
        for partner in moves.partner_id.filtered(lambda partner: partner.nemhandel_verification_state in ('not_verified', False)):
            partner.button_nemhandel_check_partner_endpoint()

    def _nemhandel_get_message_status(self, batch_size=None):
        job_count = batch_size or BATCH_SIZE
        need_retrigger = False
        for edi_user in self:
            edi_user = edi_user.with_company(edi_user.company_id)
            uuid_to_record = edi_user._nemhandel_get_documents_for_status(job_count + 1)
            if not uuid_to_record:
                continue
            if len(uuid_to_record) > job_count:
                need_retrigger = True
                uuid_to_record.popitem()

            messages_to_process = edi_user._call_nemhandel_proxy(
                "/api/nemhandel/1/get_document",
                params={'message_uuids': list(uuid_to_record)},
            )

            processed_message_uuids = edi_user._nemhandel_process_messages_status(messages_to_process, uuid_to_record)

            edi_user._call_nemhandel_proxy(
                "/api/nemhandel/1/ack",
                params={'message_uuids': list(processed_message_uuids)},
            )
        if need_retrigger:
            self.env.ref('l10n_dk.ir_cron_nemhandel_get_message_status')._trigger()

    def _nemhandel_get_documents_for_status(self, batch_size):
        self.ensure_one()
        uuid_to_record = {}
        edi_user_moves = self.env['account.move'].search(
            [
                ('nemhandel_move_state', '=', 'processing'),
                ('company_id', '=', self.company_id.id),
            ],
            limit=batch_size,
        )
        uuid_to_record.update(edi_user_moves.grouped('nemhandel_message_uuid'))
        if len(uuid_to_record) > batch_size:
            return uuid_to_record
        edi_user_responses = self.env['nemhandel.response'].search(
            [
                ('nemhandel_state', '=', 'processing'),
                ('company_id', '=', self.company_id.id),
            ],
            limit=batch_size - len(edi_user_moves),
        )
        uuid_to_record.update(edi_user_responses.grouped('nemhandel_message_uuid'))
        return uuid_to_record

    def _nemhandel_process_error_status(self, content, record):
        ''' Process the eventual errors sent by IAP.
            Returns True if the error is final, False if it has to be fetched again.
        '''
        if content['error'].get('code') == 702:
            # "Nemhandel request not ready" error:
            # thrown when the IAP is still processing the message
            return False
        if record._name == 'nemhandel.response':
            # In case of an error, IAP doesn't return the document_type, so we fall back on the record's name
            if content['error'].get('code') == 207:
                record.nemhandel_state = 'not_serviced'
            else:
                record.nemhandel_state = 'error'
                record.move_id._message_log(
                    body=self.env._("Nemhandel business response error: %s", content['error'].get('data', {}).get('message') or content['error']['message']),
                )
            return True

        # Invoice
        record._message_log(body=_("Nemhandel error: %s", content['error'].get('data', {}).get('message') or content['error']['message']))
        record.nemhandel_move_state = 'error'
        return True

    def _nemhandel_process_messages_status(self, messages, uuid_to_record):
        self.ensure_one()
        processed_message_uuids = []
        for uuid, content in messages.items():
            record = uuid_to_record[uuid]
            if content.get('error'):
                if self._nemhandel_process_error_status(content, record):
                    processed_message_uuids.append(uuid)
                continue

            if content['document_type'] == 'ApplicationResponse':
                record.nemhandel_state = content['state']
            else:
                record.nemhandel_move_state = content['state']
                record._message_log(body=_('Nemhandel status update: %s', content['state']))
            processed_message_uuids.append(uuid)
        return processed_message_uuids

    def _nemhandel_send_response(self, reference_moves, status, note=False):
        self.ensure_one()
        reference_moves = reference_moves.filtered(lambda rm: rm.nemhandel_message_uuid and rm.partner_id.nemhandel_response_support)
        if not reference_moves:
            return

        assert status in {'BusinessAccept', 'BusinessReject'}

        try:
            response = self._call_nemhandel_proxy(
                "/api/nemhandel/1/send_response",
                params={
                    'reference_uuids': reference_moves.mapped('nemhandel_message_uuid'),
                    'status': status,
                    'note': note,
                },
            )
        except UserError as e:
            log_message = self.env._(
                "An error occurred with the Nemhandel proxy while responding to this invoice's expeditor.%(br)sResponse: %(status)s - %(error)s",
                br=Markup('<br>'),
                status=status,
                error=str(e),
            )
            reference_moves._message_log_batch(
                bodies={move.id: log_message for move in reference_moves},
            )
        else:
            if response.get('error'):
                log_message = self.env._(
                    "An error occurred with the Nemhandel server while responding to this invoice's expeditor.%(br)sStatus: %(status)s - %(error)s",
                    br=Markup('<br>'),
                    status=status,
                    error=response['error']['message'],
                )
                reference_moves._message_log_batch(
                    bodies={move.id: log_message for move in reference_moves},
                )
            else:
                self.env['nemhandel.response'].create([{
                        'nemhandel_message_uuid': message['message_uuid'],
                        'response_code': status,
                        'nemhandel_state': 'processing',
                        'move_id': move.id,
                    }
                    for message, move in zip(response.get('messages'), reference_moves)
                ])
                log_message = self.env._(
                    "A Nemhandel response was sent to the Nemhandel Access Point declaring you accepted this document.",
                ) if status == 'BusinessAccept' else self.env._(
                    "A Nemhandel response was sent to the Nemhandel Access Point declaring you rejected this document.",
                )
                reference_moves._message_log_batch(bodies={move.id: log_message for move in reference_moves})

    def _nemhandel_get_participant_status(self):
        for edi_user in self:
            edi_user = edi_user.with_company(edi_user.company_id)
            try:
                proxy_user = edi_user._call_nemhandel_proxy("/api/nemhandel/1/participant_status")
            except AccountEdiProxyError as e:
                _logger.error('Error while updating Nemhandel participant status: %s', e)
                continue

            if proxy_user['nemhandel_state'] in {'not_registered', 'receiver', 'rejected'}:
                edi_user.company_id.l10n_dk_nemhandel_proxy_state = proxy_user['nemhandel_state']

    def _get_nemhandel_company_details(self):
        self.ensure_one()
        return {
            'nemhandel_company_name': self.company_id.display_name,
            'nemhandel_company_cvr': split_vat(self.company_id.vat)[1],
            'nemhandel_country_code': self.company_id.country_id.code,
            'nemhandel_phone_number': self.company_id.nemhandel_phone_number,
            'nemhandel_contact_email': self.company_id.nemhandel_contact_email,
            'nemhandel_webhook_endpoint': self.company_id._get_nemhandel_webhook_endpoint(),
            'nemhandel_webhook_token': self._generate_nemhandel_webhook_token(),
        }

    def _nemhandel_register_as_receiver(self):
        self.ensure_one()

        company = self.company_id

        if company.l10n_dk_nemhandel_proxy_state != 'in_verification':
            # a participant can only try registering as a receiver if they are not registered
            nemhandel_state_translated = dict(company._fields['l10n_dk_nemhandel_proxy_state'].selection)[company.l10n_dk_nemhandel_proxy_state]
            raise UserError(_('Cannot register a user with a %s application', nemhandel_state_translated))

        company_vat = split_vat(company.vat)[1]
        if company.nemhandel_identifier_type == '0184' and company_vat != company.nemhandel_identifier_value:
            raise ValidationError(_("If you try to register with your CVR, please make sure your company has the same VAT"))

        self._check_user_on_alternative_service()

        self._call_nemhandel_proxy(endpoint='/api/nemhandel/1/register_participant')
        company.l10n_dk_nemhandel_proxy_state = 'receiver'

    def _nemhandel_deregister_participant(self):
        self.ensure_one()

        if self.company_id.l10n_dk_nemhandel_proxy_state == 'receiver':
            # fetch all documents and message statuses before unlinking the edi user
            # so that the invoices are acknowledged
            self._cron_nemhandel_get_message_status()
            self._cron_nemhandel_get_new_documents()
            if not tools.config['test_enable'] and not modules.module.current_test:
                self.env.cr.commit()

        if self.company_id.l10n_dk_nemhandel_proxy_state != 'not_registered':
            try:
                self._call_nemhandel_proxy(endpoint='/api/nemhandel/1/cancel_nemhandel_registration')
            except UserError as e:
                if e.args and e.args[0] != "The user doesn't exist on the proxy":
                    raise

        self.company_id.l10n_dk_nemhandel_proxy_state = 'not_registered'
        self.unlink()

    def _generate_nemhandel_webhook_token(self):
        self.ensure_one()
        expiration = 30 * 24  # in 30 days
        msg = [self.id, self.company_id._get_nemhandel_webhook_endpoint()]
        payload = tools.hash_sign(self.sudo().env, 'account_nemhandel_webhook', msg, expiration_hours=expiration)
        return payload

    @api.model
    def _get_nemhandel_user_from_token(self, token: str, url: str):
        try:
            if not (payload := tools.verify_hash_signed(self.sudo().env, 'account_nemhandel_webhook', token)):
                return None
        except ValueError:
            return None
        else:
            user_id, endpoint = payload
            if not url.startswith(endpoint):
                return None
            return self.browse(user_id).exists()

    def _nemhandel_reset_webhook(self):
        for edi_user in self:
            edi_user._call_nemhandel_proxy(
                '/api/nemhandel/1/set_webhook',
                params={
                    'webhook_url': edi_user.company_id._get_nemhandel_webhook_endpoint(),
                    'token': edi_user._generate_nemhandel_webhook_token()
                }
            )
