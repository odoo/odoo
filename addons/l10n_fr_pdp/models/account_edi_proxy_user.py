import logging
import uuid
from lxml import etree
from markupsafe import Markup
from types import MappingProxyType

from odoo import api, fields, models, tools
from odoo.exceptions import UserError
from odoo.tools.misc import format_date
from odoo.tools.translate import LazyTranslate

from odoo.addons.account_edi_proxy_client.models.account_edi_proxy_user import AccountEdiProxyError
from odoo.addons.l10n_fr_pdp.models.account_peppol_response import PEPPOL_TO_PDP_STATUS, PDP_STATUSES
from odoo.addons.l10n_fr_pdp.tools.demo_utils import handle_demo
from odoo.addons.l10n_fr_pdp.utils.cdar import _parse_datetime_node as _parse_cdar_datetime_node

_logger = logging.getLogger(__name__)
_lt = LazyTranslate(__name__)
BATCH_SIZE = 50

CDAR_NSMAP = MappingProxyType({
    'qdt': "urn:un:unece:uncefact:data:standard:QualifiedDataType:100",
    'rsm': "urn:un:unece:uncefact:data:standard:CrossDomainAcknowledgementAndResponse:100",
    'ram': "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100",
    'udt': "urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100",
    'xsi': "http://www.w3.org/2001/XMLSchema-instance",
})

PROCESS_CONDITION_CODE_TO_RESPONSE_CODE_PDP = MappingProxyType({
    '200': 'submitted',  # PA-S (sending platform)
    '202': 'AB',  # PA-R (receiving platform)
    '203': 'made_available',  # PA-R
    '204': 'in_hand',  # R (receiver)
    '205': 'AP',  # R
    '207': 'contested',  # R
    '210': 'refused',  # R
    '211': 'payment_sent',  # R
    '212': 'PD',  # S (sender)
    '213': 'RE',  # PA-R
    '220': 'cancelled',  # S
})

PROCESS_CONDITION_CODE_TO_RESPONSE_CODE_PPF = MappingProxyType({
    '500': 'AB',
    '501': 'RE',
    '250': 'AP',
    '251': 'refused',
    '300': 'AP',
    '301': 'refused',
    '400': 'AP',
    '401': 'refused',
    '601': 'refused',
})

PROCESS_CONDITION_CODE_TO_RESPONSE_CODE = MappingProxyType({
    **PROCESS_CONDITION_CODE_TO_RESPONSE_CODE_PDP,
    **PROCESS_CONDITION_CODE_TO_RESPONSE_CODE_PPF,
})

STATUS_TO_PROCESS_CONDITION_CODE_PDP = MappingProxyType({status: code for code, status in PROCESS_CONDITION_CODE_TO_RESPONSE_CODE_PDP.items()})

PAYMENT_TYPE_CODES = MappingProxyType({
    'RAP': _lt("Amount remaining to be paid"),  # Reste à payer
    'ESC': _lt("Discount granted"),  # Escompte accordé ; EPD
    'RAB': _lt("Rebate granted"),  # Rabais accordé
    'REM': _lt("Allowance granted"),  # Remise accordée
    'MPA': _lt("Amount paid"),  # Montant payé
    'MEN': _lt("Amount collected (including tax)"),  # Montant encaissé (TTC)
})

DEMO_ENDPOINTS = {  # pdp reports specific endpoints not already mocked by l10n_fr_pdp demo utils
    'pilot_phase': lambda params: {
        'annuaire_line_start_date': fields.Date.today(),
        'pilot_phase': params['pdp_pilot_phase'],
    },
    'participant_status': lambda params: {},
    'send_document': lambda params: {
        'ppf_messages': [{'uid': f'demo_{uuid.uuid4()}', 'flow_id': f'demo_{uuid.uuid4()}'} for _d in params['documents']],
    },
    'pdp_state': lambda params: {},
}


class AccountEdiProxyClientUser(models.Model):
    _inherit = 'account_edi_proxy_client.user'

    proxy_type = fields.Selection(selection_add=[('pdp', 'Approved Platform')], ondelete={'pdp': 'cascade'})

    _peppol_proxy_types_conflict = models.Constraint(
        """
            EXCLUDE (
                company_id WITH =,
                edi_mode WITH =
            )
            WHERE (active IS TRUE AND proxy_type IN ('peppol', 'pdp'))
        """,
        "You can not have both a Peppol and a PDP proxy user"
    )

    # -------------------------------------------------------------------------
    # HELPER METHODS
    # -------------------------------------------------------------------------

    @api.model
    def _get_peppol_proxy_types(self):
        # Extend 'account_peppol'
        return super()._get_peppol_proxy_types() + ['pdp']

    def _get_proxy_urls(self):
        urls = super()._get_proxy_urls()
        urls['pdp'] = {
            'prod': 'https://pdp.api.odoo.com',
            'test': 'https://pdp.test.odoo.com',
            'demo': 'demo',
        }
        return urls

    @handle_demo
    def _call_peppol_proxy(self, endpoint, params=None):
        if (
            self.env.company._get_peppol_edi_mode() == 'demo'
            and self.proxy_type == 'pdp'
            and (demo_endpoint := DEMO_ENDPOINTS.get(endpoint.split('/')[-1]))
        ):
            self.ensure_one()
            return demo_endpoint(params)
        else:
            return super()._call_peppol_proxy(endpoint, params)

    def _get_proxy_identification(self, company, proxy_type):
        if proxy_type != 'pdp':
            return super()._get_proxy_identification(company, proxy_type)
        if not company.pdp_identifier:
            scheme = dict(self.env["res.partner"]._fields['peppol_eas']._description_selection(self.env))["0225"]
            raise UserError(self.env._("Please fill the Peppol Endpoint field with scheme '%s' on the company partner.", scheme))
        return f'0225:{company.pdp_identifier}'

    def _get_company_details(self):
        self.ensure_one()
        result = super()._get_company_details()
        if self.proxy_type != 'pdp':
            return result
        result['pdp_pilot_phase'] = self.company_id.l10n_fr_pdp_pilot_phase
        return result

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
                response = self._make_request(self._get_server_url(proxy_type, edi_mode) + self._get_peppol_proxy_endpoint("1/connect", proxy_type='pdp'), params={
                    'dbuuid': company.env['ir.config_parameter'].sudo().get_param('database.uuid'),
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
    def _pdp_register_receiver(self):
        self.ensure_one()
        if self.proxy_type != 'pdp':
            raise UserError(self.env._("This is only possible for the 'Approved Platform'."))

        company = self.company_id
        if company.account_peppol_proxy_state in {'smp_registration', 'receiver'}:
            # A participant can only try registering as a receiver if they are not registered
            proxy_state_translated = dict(company._fields['account_peppol_proxy_state']._description_selection(self.env))[company.account_peppol_proxy_state]
            raise UserError(self.env._("Cannot register a user with a '%(proxy_state)s' application.", proxy_state=proxy_state_translated))

        params = {
            'company_details': self._get_company_details(),
            'supported_identifiers': list(self.company_id._peppol_supported_document_types())
        }
        self._call_peppol_proxy(
            endpoint=self._get_peppol_proxy_endpoint('1/register_receiver'),
            params=params,
        )
        self.company_id.account_peppol_proxy_state = 'smp_registration'

        datetime_in_1_hour = fields.Datetime.add(fields.Datetime.now(), hours=1)
        self.env.ref('account_peppol.ir_cron_peppol_get_participant_status')._trigger(at=datetime_in_1_hour)

    def _peppol_process_participant_status(self, proxy_user):
        self.ensure_one()
        super()._peppol_process_participant_status(proxy_user)

        if self.proxy_type != 'pdp':
            return

        if annuaire_start_date := proxy_user.get('annuaire_line_start_date'):
            self.sudo().company_id.l10n_fr_pdp_annuaire_start_date = fields.Date.to_date(annuaire_start_date)
        if 'pilot_phase' in proxy_user:
            self.sudo().company_id.l10n_fr_pdp_pilot_phase = proxy_user['pilot_phase']

    def _pdp_get_regulatory_documents(self, batch_size=None):
        job_count = batch_size or BATCH_SIZE
        need_retrigger = False
        for edi_user in self:
            edi_user = edi_user.with_company(edi_user.company_id)
            try:
                # Request all messages that haven't been acknowledged
                messages = edi_user._call_peppol_proxy(
                    endpoint=edi_user._get_peppol_proxy_endpoint('1/get_all_ppf_documents'),
                )
            except AccountEdiProxyError as e:
                _logger.error('Error while receiving the document from Peppol Proxy: %s', e.message)
                continue

            message_uuids = [
                message['uuid']
                for message in messages.get('messages', [])
            ]
            if not message_uuids:
                continue

            need_retrigger = need_retrigger or len(message_uuids) > job_count
            message_uuids = message_uuids[:job_count]

            # Retrieve attachments for filtered messages
            all_messages = edi_user._call_peppol_proxy(
                endpoint=edi_user._get_peppol_proxy_endpoint('1/get_ppf_document'),
                params={'ppf_message_uuids': message_uuids},
            )
            processed_uuid_to_record = edi_user._pdp_process_regulatory_messages(all_messages)

            if not tools.config['test_enable']:
                self.env.cr.commit()
            if processed_uuid_to_record:
                edi_user._call_peppol_proxy(
                    endpoint=edi_user._get_peppol_proxy_endpoint('1/ack_ppf'),
                    params={'message_uuids': list(processed_uuid_to_record)},
                )
        if need_retrigger:
            self.env.ref('l10n_fr_pdp.ir_cron_pdp_get_regulatory_documents')._trigger()

    def _peppol_process_messages_status(self, messages, uuid_to_record):
        self.ensure_one()
        processed_message_uuids = []
        other_messages = {}
        for uid, content in messages.items():
            record = uuid_to_record[uid]
            # In case of an error there is no 'document_type' in the content.
            if record._name != 'account.peppol.response' or 'document_type' in content and content['document_type'] != 'CrossDomainAcknowledgementAndResponse':
                other_messages[uid] = content
                continue

            peppol_response = record
            if content.get('error'):
                if content['error'].get('code') == 702:
                    # "Peppol request not ready" error: thrown when the IAP is still processing the message
                    continue
                if content['error'].get('code') == 207:
                    peppol_response.peppol_state = 'not_serviced'
                else:
                    peppol_response.peppol_state = 'error'
                    peppol_response.move_id._message_log(
                        body=self.env._("French e-invoicing response error: %s", content['error'].get('data', {}).get('message') or content['error']['message']),
                    )
                processed_message_uuids.append(uid)
                continue

            peppol_response.peppol_state = content['state']
            processed_message_uuids.append(uid)

            origin_move = peppol_response.move_id
            decoded_document = self._peppol_get_decoded_document(content)
            filename = content["filename"] or 'lifecycle'
            attachment = self.env["ir.attachment"].create(
                {
                    "name": f"{filename}.xml",
                    "raw": decoded_document,
                    "type": "binary",
                    "mimetype": "application/xml",
                    "res_id": origin_move.id,
                    "res_model": 'account.move',
                }
            )
            response_code_description = PDP_STATUSES.get(peppol_response.response_code) or peppol_response.response_code
            origin_move._message_log(
                body=self.env._(
                    "The Response issued on %(issue_date)s with Response Code '%(response_code)s' was sent by the access point.",
                    response_code=response_code_description,
                    issue_date=format_date(self.env, peppol_response.pdp_issue_date),
                ),
                attachment_ids=attachment.ids,
            )
        return processed_message_uuids + super()._peppol_process_messages_status(other_messages, uuid_to_record)

    def _pdp_send_response(self, reference_moves, status, additional_info=None):
        self.ensure_one()
        reference_moves = reference_moves.filtered(lambda rm: rm.pdp_can_send_response)
        if not reference_moves:
            return
        additional_info = additional_info or {}

        status_string = PDP_STATUSES.get(status)
        if not status_string:
            raise UserError(self.env._("Unsupported response status: '%s'.", status))

        try:
            issue_time = fields.Datetime.now()
            issue_time_string = fields.Datetime.to_string(issue_time)
            for move in reference_moves:
                additional_info.setdefault(move.peppol_message_uuid, {})['issue_datetime'] = issue_time_string
            response = self._call_peppol_proxy(
                "/api/pdp/1/send_response",
                params={
                    'reference_uuids': reference_moves.mapped('peppol_message_uuid'),
                    'status': PEPPOL_TO_PDP_STATUS.get(status) or status,
                    'additional_info': additional_info,
                    'lifecycle': True,
                },
            )
        except UserError as e:
            log_message = self.env._(
                "An error occurred with the Approved Platform while sending a response.%(br)sStatus: %(status)s - %(error)s",
                br=Markup('<br>'),
                status=status_string,
                error=str(e),
            )
            reference_moves._message_log_batch(
                bodies={move.id: log_message for move in reference_moves},
            )
            return

        if response.get('error'):
            log_message = self.env._(
                "An error occurred with the Approved Platform while sending a response.%(br)sStatus: %(status)s - %(error)s",
                br=Markup('<br>'),
                status=status_string,
                error=response['error']['message'],
            )
            reference_moves._message_log_batch(
                bodies={move.id: log_message for move in reference_moves},
            )
            return
        self.env['account.peppol.response'].create([
            {
                'peppol_message_uuid': message['message_uuid'],
                'response_code': status,
                'peppol_state': 'processing',
                'move_id': move.id,
                'pdp_status_info': "\n\n".join([
                    # We only put the note since we have all other info
                    self._format_status_info({'note': additional_info.get(move.peppol_message_uuid, {}).get('note')})
                ]),
                'pdp_payment_info': additional_info.get(move.peppol_message_uuid, {}).get('payments'),
                'pdp_issue_date': issue_time,
                'pdp_flow_number': '2',
            }
            for message, move in zip(response.get('messages'), reference_moves)
        ])
        log_message = self.env._(
            "A French e-invoicing response with Response Code '%(status)s' was sent to the French e-invoicing Access Point.",
            status=status_string,
        )
        reference_moves._message_log_batch(bodies={move.id: log_message for move in reference_moves})

    def _peppol_process_new_messages(self, messages):
        self.ensure_one()
        # Note: We process the invoices first to avoid importing a response before its origin move
        response_uuids = {uuid for uuid in messages if messages[uuid]['document_type'] == 'CrossDomainAcknowledgementAndResponse'}
        other_messages = {uuid: content for uuid, content in messages.items() if uuid not in response_uuids}
        other_uuids, moves = super()._peppol_process_new_messages(other_messages)

        processed_uuids = []

        origin_message_uuids = [messages[uuid]['origin_message_uuid'] for uuid in response_uuids]
        relevant_moves_domain = [
            ('peppol_message_uuid', 'in', origin_message_uuids),
            ('company_id', '=', self.company_id.id),
        ]
        uuid_to_move_map = self.env['account.move'].search(relevant_moves_domain).grouped('peppol_message_uuid')
        for uid in response_uuids:
            content = messages[uid]
            origin_uuid = content['origin_message_uuid']
            origin_move = uuid_to_move_map.get(origin_uuid)
            if not origin_move:
                _logger.warning('The French e-invoicing response with UUID %s could not be imported: Original journal entry (UUID %s) not found.', uid, origin_uuid)
                continue
            if self._pdp_import_incoming_response(uid, content, origin_move[:1]):
                processed_uuids.append(uid)

        return other_uuids + processed_uuids, moves

    def _pdp_process_regulatory_messages(self, messages):
        self.ensure_one()
        processed_messages = {}
        origin_peppol_message_uuids = [content['origin_peppol_message_uuid'] for content in messages.values() if content['origin_peppol_message_uuid']]
        origin_domain = [
            ('peppol_message_uuid', 'in', origin_peppol_message_uuids),
            ('company_id', '=', self.company_id.id),
        ]
        original_moves = self.env['account.move'].search(origin_domain).grouped('peppol_message_uuid')

        for uid, content in messages.items():
            # We acknowledge all messages:
            # The original move / response are outgoing messages created locally. They will not be created later.
            flow_number = content['flow_number']
            if content['document_type'] in {'Invoice', 'CreditNote'}:
                processed_messages[uid] = self.env['account.move']
                origin_uuid = content['origin_peppol_message_uuid']
                origin_move = original_moves.get(origin_uuid)
                if not origin_uuid or not origin_move:
                    _logger.warning('[Flow 1] The tax extract from the PPF with UUID %s could not be imported: Original journal entry (UUID %s) not found.', uid, origin_uuid)
                    continue
                processed_messages[uid] = self._pdp_import_tax_extract(uid, content, origin_move[:1])
            elif content['document_type'] == 'CrossDomainAcknowledgementAndResponse' and flow_number in ('1', '6'):
                processed_messages[uid] = self.env['account.peppol.response']
                origin_uuid = content['origin_peppol_message_uuid']
                origin_move = original_moves.get(origin_uuid)
                if not origin_uuid or not origin_move:
                    flow_description = "tax extract" if flow_number == '1' else "status"
                    _logger.warning('[Flow %s] The %s response from the PPF with UUID %s could not be imported: Original journal entry (UUID %s) not found.', flow_number, flow_description, uid, origin_uuid)
                    continue
                if content['direction'] == 'outgoing':
                    processed_messages[uid] = self._pdp_import_outgoing_response(uid, content, origin_move[:1])
                else:
                    processed_messages[uid] = self._pdp_import_incoming_response(uid, content, origin_move[:1])
            elif content['document_type'] == 'CrossDomainAcknowledgementAndResponse' and flow_number == '10':
                self._pdp_import_flow_10_response(uid, content)
                processed_messages[uid] = True

        return processed_messages

    def _pdp_import_flow_10_response(self, uuid, content):
        flow_id = content['flow_id'].split('_')[-1]
        flow = self.env['l10n.fr.pdp.reports.flow'].search([('pdp_flow_id', '=', flow_id)], limit=1)
        if not flow:
            _logger.warning('Flow 10 message with uuid %s and flow_id %s could not be linked '
                            'to any flow 10', uuid, flow_id)
            return
        document = self._peppol_get_decoded_document(content)

        flow.payload_id = self.env['ir.attachment'].create({
            'name': f'message.{uuid}.xml',
            'raw': document,
            'res_model': flow._name,
            'res_id': flow.id,
            'type': 'binary',
            'mimetype': 'application/xml',
        })

    def _pdp_import_tax_extract(self, uuid, content, origin_move):
        if not origin_move:
            return self.env['account.move']

        # Do not update the transport status if we already received a lifecycle
        if origin_move.pdp_ppf_move_state:
            return origin_move

        if content.get('error'):
            body = self.env._("[Flow 1] There was an error when sending the tax extract to the PPF: %s",
                              content['error'].get('data', {}).get('message') or content['error']['message'])
            origin_move._message_log(body=body)
            origin_move.pdp_ppf_move_state = 'error'
        else:
            origin_move.pdp_ppf_move_state = 'sent'

        return origin_move

    def _pdp_import_outgoing_response(self, uuid, content, origin_move):
        response = self.env['account.peppol.response']
        if not origin_move:
            return response

        origin_peppol_lifecycle_uuid = content.get("origin_peppol_lifecycle_uuid")
        response = origin_move.peppol_response_ids.filtered(
            lambda r: r.peppol_message_uuid == origin_peppol_lifecycle_uuid
        )[:1]
        if not response:
            _logger.warning('[Flow %s] The status response sent to the PPF with UUID %s could not be imported: Original journal entry (UUID %s) not found.',
                            content['flow_number'], uuid, origin_move.peppol_message_uuid)
            return response

        # Do not update the transport status if we already received a lifecycle
        if response.pdp_ppf_state:
            return response

        if content.get('error'):
            error_message = content['error'].get('data', {}).get('message') or content['error']['message']
            status = dict(response._fields['response_code']._description_selection(self.env))[response.response_code]
            body = self.env._("[Flow 6] There was an error when sending a '%(status)s' response (UUID %(uuid)s) to the PPF: %(error)s",
                              status=status, uuid=response.peppol_message_uuid, error=error_message)
            origin_move._message_log(body=body)
            response.pdp_ppf_state = 'error'
        else:
            response.pdp_ppf_state = 'sent'

        return response

    def _pdp_import_incoming_response(self, uuid, content, origin_move):
        response = self.env['account.peppol.response']
        if not origin_move:
            return response

        # The endpoint for PDP / Peppol does not return the 'flow_number'; they are always flow 2.
        # The PPF endpoint always puts the 'flow_number'.
        flow_number = content.get('flow_number') or '2'
        decoded_document = self._peppol_get_decoded_document(content)
        info = self._pdp_extract_response_info(decoded_document)
        response_code = info['response_code']
        issue_date = info['issue_date']
        status_infos = info['status_infos']
        origin_ref_status_code = content.get("origin_ref_status_code")
        origin_peppol_lifecycle_uuid = content.get("origin_peppol_lifecycle_uuid")
        origin_ref_status = PROCESS_CONDITION_CODE_TO_RESPONSE_CODE.get(origin_ref_status_code)
        markup_status_info = Markup('<br/><br/>').join([self._format_status_info(status, separator=Markup('<br/>')) for status in status_infos])
        response_code_description = PDP_STATUSES.get(response_code)
        ref_status_code_description = PDP_STATUSES.get(origin_ref_status)

        if not response_code_description or not issue_date or (flow_number == '6' and not ref_status_code_description):
            if origin_ref_status_code:
                main_message = self.env._(
                    "Failed to process incoming response for status %(ref_status_info)s with Response Code '%(response_code)s' issued on %(issue_date)s.",
                    ref_status_info=(ref_status_code_description or origin_ref_status_code),
                    response_code=response_code_description,
                    issue_date=format_date(self.env, issue_date),
                )
            else:
                main_message = self.env._(
                    "Failed to process incoming response with Response Code '%(response_code)s' issued on %(issue_date)s.",
                    response_code=response_code_description,
                    issue_date=format_date(self.env, issue_date),
                )
            origin_move._message_log(
                body=self._pdp_format_message_body(flow_number, main_message, markup_status_info),
            )
            return response

        filename = content["filename"] or 'lifecycle'
        attachment = self.env["ir.attachment"].create(
            {
                "name": f"{filename}.xml",
                "raw": decoded_document,
                "type": "binary",
                "mimetype": "application/xml",
                "res_id": origin_move.id,
                "res_model": 'account.move',
            }
        )

        response = self.env['account.peppol.response'].create({
            'peppol_message_uuid': uuid,
            'pdp_ref_uuid': origin_peppol_lifecycle_uuid,
            'response_code': response_code,
            'peppol_state': content['state'],
            'move_id': origin_move.id,
            'pdp_ref_response_code': PROCESS_CONDITION_CODE_TO_RESPONSE_CODE.get(origin_ref_status_code),
            'pdp_status_info': '\n\n'.join([self._format_status_info(status, separator=Markup('\n')) for status in status_infos]),
            'pdp_issue_date': issue_date,
            'pdp_flow_number': flow_number,
            'pdp_payment_info': [payment_info for status in status_infos for payment_info in status.get('payment_infos', [])],
        })
        if content['state'] == 'done':
            if origin_ref_status_code:
                main_message = self.env._(
                    "Received response for status %(ref_status_info)s with Response Code '%(response_code)s' issued on %(issue_date)s.",
                    ref_status_info=(ref_status_code_description or origin_ref_status_code),
                    response_code=response_code_description,
                    issue_date=format_date(self.env, issue_date),
                )
            else:
                main_message = self.env._(
                    "Received response with Response Code '%(response_code)s' issued on %(issue_date)s.",
                    response_code=response_code_description,
                    issue_date=format_date(self.env, issue_date),
                )
            origin_move._message_log(
                body=self._pdp_format_message_body(flow_number, main_message, markup_status_info),
                attachment_ids=attachment.ids,
            )
        return response

    @api.model
    def _pdp_parse_included_note(self, note_node):
        subject_code = note_node.findtext('./ram:SubjectCode', namespaces=CDAR_NSMAP)
        content = note_node.findtext('./ram:Content', namespaces=CDAR_NSMAP)
        return (f"({subject_code})" if subject_code else "") + content

    @api.model
    def _pdp_extract_response_info(self, document):
        xml_node = etree.fromstring(document)
        status_nodes = xml_node.findall("rsm:AcknowledgementDocument/ram:ReferenceReferencedDocument/ram:SpecifiedDocumentStatus", namespaces=CDAR_NSMAP)
        process_condition_code = xml_node.findtext("rsm:AcknowledgementDocument/ram:ReferenceReferencedDocument/ram:ProcessConditionCode", namespaces=CDAR_NSMAP)
        status_infos = [
            {
              'index': node.findtext("./ram:SequenceNumeric", namespaces=CDAR_NSMAP),
              'reason_code': node.findtext("./ram:ReasonCode", namespaces=CDAR_NSMAP),
              'reason': node.findtext("./ram:Reason", namespaces=CDAR_NSMAP),
              'payment_infos': [
                  {
                      'type_code': pay_node.findtext("./ram:TypeCode", namespaces=CDAR_NSMAP),
                      'amount': pay_node.findtext("./ram:ValueAmount", namespaces=CDAR_NSMAP),
                      'currency': n.get("currencyID") if (n := pay_node.find("./ram:ValueAmount", namespaces=CDAR_NSMAP)) is not None else None,
                      'tax_percent': pay_node.findtext("./ram:ValuePercent", namespaces=CDAR_NSMAP),
                  }
                  for pay_node in node.findall("./ram:SpecifiedDocumentCharacteristic", namespaces=CDAR_NSMAP)
              ],
              'note': "\n".join([
                  note
                  for note_node in node.findall("./ram:IncludedNote", namespaces=CDAR_NSMAP)
                  if (note := self._pdp_parse_included_note(note_node))
              ]),
            } for node in status_nodes
        ] if status_nodes is not None else []

        return {
            'process_condition_code': process_condition_code,
            'response_code': PROCESS_CONDITION_CODE_TO_RESPONSE_CODE.get(process_condition_code, process_condition_code),
            'issue_date': _parse_cdar_datetime_node(xml_node.find("rsm:AcknowledgementDocument/ram:IssueDateTime/udt:DateTimeString", namespaces=CDAR_NSMAP)),
            'status_infos': status_infos,
        }

    @api.model
    def _format_payment_info(self, info, separator='\n'):
        type_code = info.get('type_code')
        type_string = PAYMENT_TYPE_CODES.get(type_code)
        amount = info.get('amount')
        currency = info.get('currency')
        tax_percent = info.get('tax_percent')

        infos = []
        if type_code and type_string:
            infos.append(f"[{type_code}] {type_string}")
        elif type_code:
            infos.append(f"[{type_code}]")
        if amount and tax_percent:
            infos.append(self.env._("%(amount)s %(currency_code)s (including %(tax_percent)s%% VAT)",
                                    amount=amount, currency_code=currency, tax_percent=tax_percent))
        elif amount:
            infos.append(self.env._("%(amount)s %(currency_code)s", amount=amount, currency_code=currency))

        return separator.join(infos)

    @api.model
    def _format_status_info(self, status, separator='\n'):
        reason_code = status.get('reason_code')
        reason = status.get('reason')
        note = status.get('note')

        infos = []
        # Reason
        if reason_code and reason:
            infos.append(f"[{reason_code}] {reason}")
        elif reason_code:
            infos.append(f"[{reason_code}]")
        elif reason:
            infos.append(reason)
        # Note
        if note:
            infos.append(note)
        # Payment Infos
        if payment_infos := status.get('payment_infos'):
            infos.append(self.env._("Payment Info:"))
            for payment_info in payment_infos:
                infos.append(self._format_payment_info(payment_info, separator=separator))

        return separator.join(infos)

    @api.model
    def _pdp_format_message_body(self, flow_number, main_message, markup_status_info):
        messages = [
            self.env._("[Flow %(flow_number)s] %(main_message)s", flow_number=flow_number, main_message=main_message),
        ]
        if markup_status_info:
            status_message = Markup('<br/>').join([
                self.env._("It included the following status info:"),
                markup_status_info
            ])
            messages.append(status_message)
        return Markup('<br/><br/>').join(messages)

    def _peppol_get_filetype(self, content):
        if content['document_type'] == 'Factur-X':
            return "pdf", "application/pdf"
        return super()._peppol_get_filetype(content)

    def _pdp_send_lifecycles(self, batch_size=None):
        job_count = batch_size or BATCH_SIZE
        need_retrigger = False
        for edi_user in self:
            edi_user = edi_user.with_company(edi_user.company_id)
            company = edi_user.company_id
            collected_moves = self.env['account.move'].search(
                [
                    ('company_id', '=', company.id),
                    ('pdp_ppf_move_state', 'in', ['sent', 'done']),
                    ('pdp_lifecycle_residual', '!=', 0.0),
                ],
                limit=job_count + 1,
            )
            move_count = len(collected_moves)
            _logger.info("At least %s moves need payment lifecycles in company '%s'.", move_count, company.name)
            if not collected_moves:
                continue
            need_retrigger = need_retrigger or move_count > job_count
            try:
                wizard = self.env['pdp.response.wizard'].create({
                    'status': 'PD',
                    'move_ids': collected_moves[:job_count].ids,
                })
                wizard.button_send()
            except Exception:  # noqa: BLE001
                _logger.exception('Error while sending payment lifecycles: %s')
                continue
        if need_retrigger:
            self.env.ref('l10n_fr_pdp.ir_cron_pdp_send_lifecycles')._trigger()

    # -------------------------------------------------------------------------
    # CRONS
    # -------------------------------------------------------------------------

    def _cron_pdp_get_regulatory_documents(self):
        edi_users = self.search([('company_id.account_peppol_proxy_state', '=', 'receiver'), ('proxy_type', '=', 'pdp')])
        edi_users._pdp_get_regulatory_documents()

    def _cron_pdp_send_lifecycles(self):
        edi_users = self.search([('company_id.account_peppol_proxy_state', '=', 'receiver'), ('proxy_type', '=', 'pdp')])
        edi_users._pdp_send_lifecycles()
