import logging
from datetime import datetime
from lxml import etree
from markupsafe import Markup

from odoo import _, api, fields, models, modules, tools
from odoo.exceptions import UserError

from odoo.addons.account_edi_proxy_client.models.account_edi_proxy_user import AccountEdiProxyError
from odoo.addons.l10n_fr_pdp.tools.demo_utils import handle_demo

_logger = logging.getLogger(__name__)
BATCH_SIZE = 50

CDAR_NSMAP = {
    'qdt': "urn:un:unece:uncefact:data:standard:QualifiedDataType:100",
    'rsm': "urn:un:unece:uncefact:data:standard:CrossDomainAcknowledgementAndResponse:100",
    'ram': "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100",
    'udt': "urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100",
    'xsi': "http://www.w3.org/2001/XMLSchema-instance",
}

PROCESS_CONDITION_CODE_TO_RESPONSE_CODE = {
    '200': 'submitted',  # PA-S (sending platform)
    '202': 'received',  # PA-R (receiving platform)
    '203': 'made_available',  # PA-R
    '204': 'in_hand',  # R (receiver)
    '205': 'approved',  # R
    '207': 'contested',  # R
    '210': 'refused',  # R
    '211': 'payment_sent',  # R
    '212': 'paid',  # S (sender)
    '213': 'rejected',  # PA-R
    '220': 'cancelled',  # S
}



def _parse_cdar_datetime(date_string):
    if date_string is None:
        return None
    return datetime.strptime(date_string, '%Y%m%d%H%M%S')


def _parse_cdar_date(date_string):
    if date_string is None:
        return None
    return datetime.strptime(date_string, '%Y%m%d')



class AccountEdiProxyClientUser(models.Model):
    _inherit = 'account_edi_proxy_client.user'

    proxy_type = fields.Selection(selection_add=[('pdp', 'PDP')], ondelete={'pdp': 'cascade'})

    # -------------------------------------------------------------------------
    # HELPER METHODS
    # -------------------------------------------------------------------------

    def _get_proxy_urls(self):
        urls = super()._get_proxy_urls()
        urls['pdp'] = {
            'prod': 'https://pdp.api.odoo.com',
            # TODO: test url
            # 'test': 'https://pdp.test.odoo.com',
            'test': 'http://localhost:9999',
            'demo': 'demo',
        }
        return urls

    def _get_proxy_identification(self, company, proxy_type):
        if proxy_type != 'pdp':
            return super()._get_proxy_identification(company, proxy_type)
        if not company.pdp_identifier:
            raise UserError(
                _("Please fill the PDP identifier."))
        return f'0225:{company.pdp_identifier}'

    @handle_demo
    def _register_proxy_user(self, company, proxy_type, edi_mode):
        """ Override to avoid using the deprecated route on IAP """
        if proxy_type != 'pdp':
            return super()._register_proxy_user(company, proxy_type, edi_mode)

        private_key_sudo = self.env['certificate.key'].sudo()._generate_rsa_private_key(
            company,
            name=f"{proxy_type}_{edi_mode}_{company.id}.key",
        )
        peppol_identifier = self._get_proxy_identification(company, proxy_type)
        if edi_mode == 'demo':
            # simulate registration
            response = {'id_client': f'demo{company.id}{proxy_type}', 'refresh_token': 'demo'}
        else:
            try:
                # b64encode returns a bytestring, we need it as a string
                response = self._make_request(self._get_server_url(proxy_type, edi_mode) + '/api/pdp/1/connect', params={
                    'dbuuid': company.env['ir.config_parameter'].get_param('database.uuid'),
                    'company_id': company.id,
                    'peppol_identifier': peppol_identifier,
                    'public_key': private_key_sudo._get_public_key_bytes(encoding='pem').decode(),
                })
            except AccountEdiProxyError as e:
                raise UserError(e.message)

        if error_message := response.get('error'):
            raise UserError(error_message)

        return self.create({
            'id_client': response['id_client'],
            'company_id': company.id,
            'proxy_type': 'pdp',
            'edi_mode': edi_mode,
            'edi_identification': peppol_identifier,
            'private_key_id': private_key_sudo.id,
            'refresh_token': response['refresh_token'],
        })

    @handle_demo
    def _call_pdp_proxy(self, endpoint, params=None):
        self.ensure_one()
        if self.proxy_type != 'pdp':
            raise UserError(_('EDI user should be of type PDP'))

        params = params or {}
        try:
            response = self._make_request(
                f"{self._get_server_url()}{endpoint}",
                params=params,
            )
        except AccountEdiProxyError as e:
            if e.code == 'no_such_user_found':
                # TODO: may be too "aggressive" in production; but useful for testing?
                self.company_id.l10n_fr_pdp_proxy_state = False
                self.unlink()
                if not modules.module.current_test:
                    self.env.cr.commit()
                raise UserError(_('We could not find a user with this information on our server. Please check your information.'))
            raise UserError(e.message)

        if 'error' in response:
            errors = [
                response['error'].get('subject'),
                response['error'].get('message'),
            ]
            message = '\n'.join([error for error in errors if error])
            raise UserError(message or _('Connection error, please try again later.'))
        return response

    def _get_pdp_company_details(self):
        self.ensure_one()
        return {
            'peppol_company_name': self.company_id.display_name,
            'peppol_company_vat': self.company_id.vat,
            'peppol_company_street': self.company_id.street,
            'peppol_company_city': self.company_id.city,
            'peppol_company_zip': self.company_id.zip,
            'peppol_country_code': self.company_id.country_id.code,
            'peppol_phone_number': self.company_id.pdp_phone_number,
            'peppol_contact_email': self.company_id.pdp_contact_email,
            'peppol_webhook_endpoint': self.company_id._get_pdp_webhook_endpoint(),
            'peppol_webhook_token': self._generate_pdp_webhook_token(),
        }

    def _pdp_register_receiver(self):
        # remove in master
        self.ensure_one()
        company = self.company_id
        if company.l10n_fr_pdp_proxy_state in ('pending', 'receiver'):
            # a participant can only try registering as a receiver if they are not registered
            pdp_state_translated = dict(company._fields['l10n_fr_pdp_proxy_state'].selection)[company.l10n_fr_pdp_proxy_state]
            raise UserError(_('Cannot register a user with a %s application', pdp_state_translated))

        params = {
            'company_details': self._get_pdp_company_details(),
            'supported_identifiers': list(self.company_id._pdp_supported_document_types()),
        }
        self._call_pdp_proxy(
            endpoint='/api/pdp/1/register_receiver',
            params=params,
        )
        company.l10n_fr_pdp_proxy_state = 'pending'

        datetime_in_1_hour = fields.Datetime.add(fields.Datetime.now(), hours=1)
        self.env.ref('l10n_fr_pdp.ir_cron_pdp_get_participant_status')._trigger(at=datetime_in_1_hour)

    def _pdp_deregister_participant(self):
        self.ensure_one()

        proxy_state = self.company_id.l10n_fr_pdp_proxy_state
        if proxy_state == 'receiver':
            # fetch all documents and message statuses before unlinking the edi user
            # so that the invoices are acknowledged
            self._cron_pdp_get_message_status()
            self._cron_pdp_get_new_documents()
            if not tools.config['test_enable'] and not modules.module.current_test:
                self.env.cr.commit()

        if proxy_state:
            self._call_pdp_proxy(endpoint='/api/pdp/1/cancel_pdp_registration')

        self.company_id.l10n_fr_pdp_proxy_state = False
        self.unlink()

    def _pdp_get_participant_status(self):
        for edi_user in self:
            edi_user = edi_user.with_company(edi_user.company_id)
            try:
                proxy_user = edi_user._call_pdp_proxy("/api/pdp/1/participant_status")
            except AccountEdiProxyError as e:
                _logger.error('Error while updating PDP participant status: %s', e)
                continue

            if proxy_user['pdp_state'] in ('pending', 'receiver', 'rejected'):
                edi_user.company_id.l10n_fr_pdp_proxy_state = proxy_user['pdp_state']

    def _generate_pdp_webhook_token(self):
        self.ensure_one()
        expiration = 30 * 24  # in 30 days
        msg = [self.id, self.company_id._get_pdp_webhook_endpoint()]
        payload = tools.hash_sign(self.sudo().env, 'account_pdp_webhook', msg, expiration_hours=expiration)
        return payload

    @api.model
    def _get_pdp_user_from_token(self, token: str, url: str):
        try:
            if not (payload := tools.verify_hash_signed(self.sudo().env, 'account_pdp_webhook', token)):
                return None
        except ValueError:
            return None
        else:
            user_id, endpoint = payload
            if not url.startswith(endpoint):
                return None
            return self.browse(user_id).exists()

    def _pdp_reset_webhook(self):
        for edi_user in self:
            edi_user._call_pdp_proxy(
                '/api/pdp/1/set_webhook',
                params={
                    'webhook_url': edi_user.company_id._get_pdp_webhook_endpoint(),
                    'token': edi_user._generate_pdp_webhook_token()
                }
            )

    def _pdp_get_new_documents(self, batch_size=None):
        job_count = batch_size or BATCH_SIZE
        need_retrigger = False
        params = {
            'domain': {
                'direction': 'incoming',  # TODO: maybe we should also fetch outgoing lifecycle documents (adjust IAP code)
                'errors': False,
            }
        }
        for edi_user in self:
            edi_user = edi_user.with_company(edi_user.company_id)
            params['domain']['receiver_identifier'] = edi_user.edi_identification
            try:
                # request all messages that haven't been acknowledged
                messages = edi_user._call_pdp_proxy(
                    "/api/pdp/1/get_all_documents",
                    params=params,
                )
            except UserError as e:
                _logger.error('Error while receiving the document from PDP Proxy: %s', e)
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
            all_messages = edi_user._call_pdp_proxy(
                "/api/pdp/1/get_document",
                params={'message_uuids': message_uuids},
            )
            processed_uuid_to_record = edi_user._pdp_process_new_messages(all_messages)

            if not tools.config['test_enable']:
                self.env.cr.commit()
            if processed_uuid_to_record:
                edi_user._call_pdp_proxy(
                    "/api/pdp/1/ack",
                    params={'message_uuids': list(processed_uuid_to_record)},
                )
        if need_retrigger:
            self.env.ref('l10n_fr_pdp.ir_cron_pdp_get_new_documents')._trigger()

    def _pdp_get_message_status(self, batch_size=None):
        job_count = batch_size or BATCH_SIZE
        need_retrigger = False
        for edi_user in self:
            edi_user = edi_user.with_company(edi_user.company_id)
            documents = edi_user._pdp_get_documents_for_status(job_count)
            if not documents:
                continue
            need_retrigger = need_retrigger or len(documents) > job_count
            uuid_to_record = {document.pdp_message_uuid: document for document in documents[:job_count]}
            messages_to_process = edi_user._call_pdp_proxy(
                "/api/pdp/1/get_document",
                params={'message_uuids': list(uuid_to_record)},
            )

            processed_message_uuids = edi_user._pdp_process_messages_status(messages_to_process, uuid_to_record)

            if processed_message_uuids:
                edi_user._call_pdp_proxy(
                    "/api/pdp/1/ack",
                    params={'message_uuids': processed_message_uuids},
                )
        if need_retrigger:
            self.env.ref('l10n_fr_pdp.ir_cron_pdp_get_message_status')._trigger()

    def _pdp_get_documents_for_status(self, batch_size):
        self.ensure_one()

        edi_user_moves = self.env['account.move'].search(
            [
                ('pdp_move_state', '=', 'processing'),
                ('company_id', '=', self.company_id.id),
            ],
            limit=batch_size + 1,
        )
        documents = list(edi_user_moves)
        if len(documents) > batch_size:
            return documents

        edi_user_responses = self.env['pdp.response'].search(
            [
                ('pdp_state', '=', 'processing'),
                ('company_id', '=', self.company_id.id),
            ],
            limit=batch_size - len(documents) + 1,
        )
        return documents + list(edi_user_responses)

    def _pdp_process_messages_status(self, messages, uuid_to_record):
        self.ensure_one()
        processed_message_uuids = []
        for uuid, content in messages.items():
            record_model = uuid_to_record[uuid]._name
            if record_model == 'pdp.response':
                pdp_response = uuid_to_record[uuid]
                if content.get('error'):
                    if content['error'].get('code') == 702:
                        # "Peppol request not ready" error:
                        # thrown when the IAP is still processing the message
                        continue
                    if content['error'].get('code') == 207:
                        pdp_response.pdp_state = 'not_serviced'
                    else:
                        pdp_response.pdp_state = 'error'
                        pdp_response.move_id._message_log(
                            body=self.env._("PDP response error: %s", content['error'].get('data', {}).get('message') or content['error']['message']),
                        )
                    processed_message_uuids.append(uuid)
                    continue

                pdp_response.pdp_state = content['state']
                processed_message_uuids.append(uuid)
            elif record_model == 'account.move':
                move = uuid_to_record[uuid]
                if content.get('error'):
                    if content['error'].get('code') == 702:
                        # "Peppol request not ready" error:
                        # thrown when the IAP is still processing the message
                        continue
                    move._message_log(body=self.env._("PDP error: %s", content['error'].get('data', {}).get('message') or content['error']['message']))
                    move.pdp_move_state = 'error'
                    processed_message_uuids.append(uuid)
                    continue

                move.pdp_move_state = content['state']
                move._message_log(body=self.env._('PDP status update: %s', content['state']))
                processed_message_uuids.append(uuid)
        return processed_message_uuids

    def _pdp_send_response(self, reference_moves, status, additional_info=None):
        self.ensure_one()
        reference_moves = reference_moves.filtered(lambda rm: rm.pdp_can_send_response)
        if not reference_moves:
            return
        if additional_info is None:
            additional_info = {}

        if status not in self.env['pdp.response']._fields['response_code'].get_values(self.env):
            raise UserError(_("Unsupported response status: '%s'.", status))

        try:
            issue_time = fields.Datetime.now()
            additional_info['issue_datetime'] = issue_time
            response = self._call_pdp_proxy(
                "/api/pdp/1/send_response",
                params={
                    'reference_uuids': reference_moves.mapped('pdp_message_uuid'),
                    'status': status,
                    'additional_info': additional_info or {},
                },
            )
        except UserError as e:
            log_message = Markup(self.env._(
                "An error occurred with the PDP proxy while sending a response message to this invoice's expeditor.<br/>Status: %(status)s - %(error)s",
                status=status,
                error=str(e),
            ))
            reference_moves._message_log_batch(
                bodies={move.id: log_message for move in reference_moves},
            )
            return

        if response.get('error'):
            log_message = Markup(self.env._(
                "An error occurred with the PDP server while sending a response message to this invoice's expeditor.<br/>Status: %(status)s - %(error)s",
                status=status,
                error=response['error']['message'],
            ))
            reference_moves._message_log_batch(
                bodies={move.id: log_message for move in reference_moves},
            )
        else:
            self.env['pdp.response'].create([
                {
                    'pdp_message_uuid': message['message_uuid'],
                    'response_code': status,
                    # TODO: status_info
                    'pdp_state': 'processing',
                    'move_id': move.id,
                    'issue_date': issue_time,
                }
                for message, move in zip(response.get('messages'), reference_moves)
            ])
            log_message = self.env._(
                "A PDP response was sent to the PDP Access Point declaring you %(status)s this document.",
                status=status,  # TODO: translation
            )
            reference_moves._message_log_batch(bodies={move.id: log_message for move in reference_moves})

    def _pdp_process_new_messages(self, messages):
        self.ensure_one()
        processed_messages = {}
        response_uuids = []
        purchase_journal = self.company_id.pdp_purchase_journal_id

        # Note: We process the invoices first to avoid importing a respnse before its origin move
        for uuid, content in messages.items():
            if content['document_type'] == 'CrossDomainAcknowledgementAndResponse':
                response_uuids.append(uuid)
            else:
                if move := self._pdp_import_invoice(uuid, content, purchase_journal):
                    processed_messages[uuid] = move
        if not response_uuids:
            return processed_messages

        origin_message_uuids = [messages[uuid]['origin_message_uuid'] for uuid in response_uuids]
        relevant_moves_domain = [
            ('pdp_message_uuid', 'in', origin_message_uuids),
            ('company_id', '=', self.company_id.id),  # TODO: on PRRO PR?
        ]
        uuid_to_move_map = self.env['account.move'].search(relevant_moves_domain).grouped('pdp_message_uuid')
        for uuid in response_uuids:
            content = messages[uuid]
            origin_uuid = content['origin_message_uuid']
            origin_move = uuid_to_move_map.get(origin_uuid)
            if not origin_move:
                _logger.warning('The PDP response with UUID %s could not be imported: Original journal entry (UUID %s) not found.', uuid, origin_uuid)
                continue
            if response := self._pdp_import_response(uuid, content, origin_move):
                processed_messages[uuid] = response

        return processed_messages

    def _pdp_import_response(self, uuid, content, origin_move):
        response = self.env['pdp.response']
        if not origin_move:
            return response

        enc_key = content["enc_key"]
        document_content = content["document"]
        decoded_document = self._decrypt_data(document_content, enc_key)
        info = self._pdp_extract_response_info(decoded_document)
        response_code = info['response_code']
        issue_date = info['issue_date']
        status_info = info['status_info']
        # TODO: Map response code to response text
        # TODO: Maybe split note reason / reason code part off from `note`
        if response_code not in response._fields['response_code'].get_values(self.env) or not issue_date:
            origin_move._message_log(
                body=self.env._(
                    "Failed to process incoming response (Response Code = %(response_code)s; Issue Date = %(issue_date)s).%(br)s%(note_info)s",
                    response_code=response_code,
                    issue_date=issue_date,
                    note_info=f"It included the following status info:\n{status_info}" if status_info else '',
                    br=Markup('<br/>') if status_info else '',
                ),
            )
            return response

        response = self.env['pdp.response'].create({
            'pdp_message_uuid': uuid,
            'response_code': response_code,
            'pdp_state': content['state'],  # TODO: do we need to fetch response messages that are not 'done'?
            'move_id': origin_move.id,
            'status_info': status_info,
            'issue_date': issue_date,
        })
        if content['state'] == 'done':
            origin_move._message_log(
                body=self.env._(
                    "Received response with Response Code '%(response_code)s' issued on %(issue_date)s.%(br)s%(note_info)s",
                    response_code=response_code,
                    issue_date=issue_date,
                    note_info=f"It included the following status info:\n{status_info}" if status_info else '',
                    br=Markup('<br/>') if status_info else '',
                ),
            )
        return response

    @api.model
    def _pdp_extract_response_info(self, document):
        xml_node = etree.fromstring(document)
        status_nodes = xml_node.findall("rsm:AcknowledgementDocument/ram:ReferenceReferencedDocument/ram:SpecifiedDocumentStatus", namespaces=CDAR_NSMAP)
        process_condition_code = xml_node.findtext("rsm:AcknowledgementDocument/ram:ReferenceReferencedDocument/ram:ProcessConditionCode", namespaces=CDAR_NSMAP)
        status_list = [
            {
              'index': node.findtext("./ram:SequenceNumeric", namespaces=CDAR_NSMAP),
              'reason_code': node.findtext("./ram:ReasonCode", namespaces=CDAR_NSMAP),
              'reason': node.findtext("./ram:Reason", namespaces=CDAR_NSMAP),
              'note': "\n".join([
                  f"({note_node.findtext('./ram:SubjectCode', namespaces=CDAR_NSMAP)}) {note_node.findtext('./ram:Content', namespaces=CDAR_NSMAP)}"
                  for note_node in node.findall("./ram:IncludedNote", namespaces=CDAR_NSMAP)
              ]),
            } for node in status_nodes
        ] if status_nodes is not None else []

        return {
            'response_code': PROCESS_CONDITION_CODE_TO_RESPONSE_CODE.get(process_condition_code, process_condition_code),
            'issue_date': _parse_cdar_datetime(xml_node.findtext("rsm:AcknowledgementDocument/ram:IssueDateTime/udt:DateTimeString", namespaces=CDAR_NSMAP)),
            'status_info': "\n\n".join([f"#{status['index']}\n[{status['reason_code']}] {status['reason']}\n{status['note']}" for status in status_list]),
        }

    def _pdp_import_invoice(self, uuid, content, journal):
        if not journal:
            _logger.warning('The PDP document with UUID %s could not be imported (missing journal)', uuid)
            return self.env['account.move']
        enc_key = content["enc_key"]
        document_content = content["document"]
        filename = content["filename"] or 'attachment'  # default to attachment, which should not usually happen
        decoded_document = self._decrypt_data(document_content, enc_key)
        attachment = self.env["ir.attachment"].create(
            {
                "name": f"{filename}.xml",
                "raw": decoded_document,
                "type": "binary",
                "mimetype": "application/xml",
            }
        )

        move = self.env['account.move'].create({
            'journal_id': journal.id,
            'move_type': 'in_invoice',
            'pdp_move_state': content['state'],
            'pdp_message_uuid': uuid,
        })
        if 'is_in_extractable_state' in move._fields:
            move.is_in_extractable_state = False

        move._extend_with_attachments(attachment, new=True)
        move._message_log(
            body=_(
                "PDP document (UUID: %(uuid)s) has been received successfully",
                uuid=uuid,
            ),
            attachment_ids=attachment.ids,
        )
        move._autopost_bill()
        attachment.write({'res_model': 'account.move', 'res_id': move.id})
        return move

    # -------------------------------------------------------------------------
    # CRONS
    # -------------------------------------------------------------------------

    def _cron_pdp_get_new_documents(self):
        edi_users = self.search([('proxy_type', '=', 'pdp'), ('company_id.l10n_fr_pdp_proxy_state', '=', 'receiver')])
        edi_users._pdp_get_new_documents()

    def _cron_pdp_get_message_status(self):
        edi_users = self.search([('proxy_type', '=', 'pdp'), ('company_id.l10n_fr_pdp_proxy_state', '=', 'receiver')])
        edi_users._pdp_get_message_status()

    def _cron_pdp_get_participant_status(self):
        edi_users = self.search([('proxy_type', '=', 'pdp')])
        edi_users._pdp_get_participant_status()

        # throughout the registration process, we need to check the status more frequently
        if self.search_count([('company_id.l10n_fr_pdp_proxy_state', '=', 'pending')], limit=1):
            datetime_in_1_hour = fields.Datetime.add(fields.Datetime.now(), hours=1)
            self.env.ref('l10n_fr_pdp.ir_cron_pdp_get_participant_status')._trigger(at=datetime_in_1_hour)

    def _cron_pdp_webhook_keepalive(self):
        edi_users = self.search([('proxy_type', '=', 'pdp'), ('company_id.l10n_fr_pdp_proxy_state', '=', 'receiver')])
        edi_users._pdp_reset_webhook()
