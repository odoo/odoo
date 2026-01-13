import logging
from datetime import datetime, timedelta
from lxml import etree
from markupsafe import Markup

from odoo import api, models
from odoo.addons.account_edi_proxy_client.models.account_edi_proxy_user import AccountEdiProxyError
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AccountEdiProxyClientUser(models.Model):
    _inherit = 'account_edi_proxy_client.user'

    def _peppol_send_response(self, reference_moves, status, clarifications=None):
        self.ensure_one()
        clarifications = clarifications or []
        reference_moves = reference_moves.filtered(lambda rm: rm.peppol_message_uuid and rm.peppol_can_send_response)
        if not reference_moves:
            return

        assert status in {'AB', 'AP', 'RE'}
        if status == 'RE':
            reason_exists = False
            for clarification in clarifications:
                if clarification['list_identifier'] == 'OPStatusReason':
                    reason_exists = True
                    break
            if not reason_exists:
                raise ValidationError(self.env._('At least one reason must be given when rejecting a Peppol invoice.'))

        try:
            response = self._call_peppol_proxy(
                "/api/peppol/1/send_response",
                params={
                    'reference_uuids': reference_moves.mapped('peppol_message_uuid'),
                    'status': status,
                    'clarifications': clarifications,
                },
            )
        except UserError as e:
            log_message = Markup(self.env._(
                "An error occurred with the Peppol server while responding to this invoice's expeditor.<br/>Status: %(status)s - %(error)s",
                status=status,
                error=str(e)
            ))
            reference_moves._message_log_batch(
                bodies={move.id: log_message for move in reference_moves},
            )
        else:
            self.env['account.peppol.response'].create([{
                    'peppol_message_uuid': message['message_uuid'],
                    'response_code': status,
                    'peppol_state': 'processing',
                    'move_id': move.id,
                }
                for message, move in zip(response.get('messages'), reference_moves)
            ])
            log_message = self.env._(
                "A Peppol response was sent to the Peppol Access Point declaring you %(status)s this document.",
                status=self.env._('received') if status == 'AB' else self.env._('accepted') if status == 'AP' else self.env._('rejected'),
            )
            reference_moves._message_log_batch(bodies={move.id: log_message for move in reference_moves})

    @api.model
    def _peppol_extract_response_info(self, document):
        doc_tree = etree.fromstring(document)
        blr_status = doc_tree.find('{*}DocumentResponse/{*}Response/{*}ResponseCode').text
        clarifications = self.env['account.peppol.clarification'].search([])
        clarification_messages = {'OPStatusReason': [], 'OPStatusAction': []}
        for status in doc_tree.findall('.//{*}Response/{*}Status'):
            status_reason_code = status.find('{*}StatusReasonCode')
            status_reason = status.find('{*}StatusReason')

            if status_reason_code is not None and status_reason is not None:
                # It is not mandatory in Peppol to have both (the reason code and the reason name/description) but at least one is required
                if clarif_list := clarification_messages.get(status_reason_code.attrib['listID']):
                    clarif_list.append(status_reason.text)
            elif status_reason_code is not None:
                if clarif_list := clarification_messages.get(status_reason_code.attrib['listID']):
                    clarification = clarifications.filtered(lambda c: c.list_identifier == status_reason_code.attrib['listID'] and c.code == status_reason_code.text)
                    clarif_list.append(clarification.name)
            else:
                clarification = clarifications.filtered(lambda c: status_reason in (c.name, c.description))
                clarification_messages[clarification.list_identifier].append(status_reason.text)

        rejection_message = ''
        if clarification_messages['OPStatusReason']:
            rejection_message = Markup(self.env._('<b>Reasons:</b><br/>')) + ', '.join(clarification_messages['OPStatusReason'])
        if clarification_messages['OPStatusAction']:
            rejection_message += (Markup('<br/>') if rejection_message else '') + Markup(self.env._('<b>Suggested actions:</b><br/>')) + ', '.join(clarification_messages['OPStatusAction'])

        return blr_status, rejection_message

    def _peppol_process_new_messages(self, messages):
        self.ensure_one()
        processed_messages = {}
        other_messages = {}
        origin_message_uuids = [content['origin_message_uuid'] for content in messages.values()]
        origin_moves = self.env['account.move'].search([('peppol_message_uuid', 'in', origin_message_uuids)])
        for uuid, content in messages.items():
            if content['document_type'] == 'ApplicationResponse':
                enc_key = content["enc_key"]
                document_content = content["document"]
                decoded_document = self._decrypt_data(document_content, enc_key)
                blr_status, rejection_message = self._peppol_extract_response_info(decoded_document)
                response = self.env['account.peppol.response']
                if blr_status in {'AB', 'AP', 'RE'}:
                    # We only support those code for now,
                    # which are the only mandatory codes to support in order to correctly handle PEPPOL Business Responses.
                    if move := origin_moves.filtered(lambda m: m.peppol_message_uuid == content['origin_message_uuid']):
                        response = self.env['account.peppol.response'].create({
                            'peppol_message_uuid': uuid,
                            'response_code': blr_status,
                            'peppol_state': content['state'],
                            'move_id': move.id,
                        })
                        if content['state'] == 'done':
                            if blr_status == 'RE':
                                move._message_log(
                                    body=self.env._(
                                        "The Peppol receiver of this document has rejected it with the following information:%(br)s%(rejection_message)s",
                                        br=Markup("<br/>"),
                                        rejection_message=rejection_message,
                                    )
                                )
                            else:
                                move._message_log(
                                    body=self.env._(
                                        "The Peppol receiver of this document has %(status)s it.",
                                        status=self.env._('received') if blr_status == 'AB' else self.env._('accepted'),
                                    ),
                                )
                processed_messages[uuid] = response
            else:
                other_messages[uuid] = content

        processed_messages.update(super()._peppol_process_new_messages(other_messages))
        return processed_messages

    def _peppol_post_process_new_messages(self, uuid_to_record):
        super()._peppol_post_process_new_messages(uuid_to_record)
        # records in uuid_to_record can also be account.peppol.response but we only send responses for invoices/credit notes
        moves = self.env['account.move'].browse(record.id for record in uuid_to_record.values() if record._name == 'account.move')
        moves.partner_id._peppol_fill_participant_supported_documents()
        self._peppol_send_response(moves, 'AB')

    def _peppol_get_documents_for_status(self, batch_size):
        self.ensure_one()
        documents = super()._peppol_get_documents_for_status(batch_size)
        if len(documents) > batch_size:
            return documents

        edi_user_responses = self.env['account.peppol.response'].search(
            [
                ('peppol_state', '=', 'processing'),
                ('company_id', '=', self.company_id.id),
            ],
            limit=batch_size - len(documents) + 1,
        )
        return documents + list(edi_user_responses)

    def _peppol_process_messages_status(self, messages, uuid_to_record):
        self.ensure_one()
        processed_message_uuids = []
        other_messages = {}
        for uuid, content in messages.items():
            if uuid_to_record[uuid]._name != 'account.peppol.response':
                other_messages[uuid] = content
                continue

            peppol_response = uuid_to_record[uuid]
            if content.get('error'):
                if content['error'].get('code') == 702:
                    # "Peppol request not ready" error:
                    # thrown when the IAP is still processing the message
                    continue
                if content['error'].get('code') == 207:
                    peppol_response.peppol_state = 'not_serviced'
                else:
                    peppol_response.peppol_state = 'error'
                    peppol_response.move_id._message_log(
                        body=self.env._("Peppol business response error: %s", content['error'].get('data', {}).get('message') or content['error']['message']),
                    )
                processed_message_uuids.append(uuid)
                continue

            peppol_response.peppol_state = content['state']
            processed_message_uuids.append(uuid)
        return processed_message_uuids + super()._peppol_process_messages_status(other_messages, uuid_to_record)

    def _cron_peppol_auto_register_services(self):
        # TODO prro in master: merge this in account_peppol instead of _peppol_auto_register_services.
        # The difference is to use _peppol_supported_document_types and not a module parameter to just send all services to IAP,
        # which already does a filtering on existing document types
        receivers = self.search([
            ('proxy_type', '=', 'peppol'),
            ('company_id.account_peppol_proxy_state', '=', 'receiver')
        ])
        supported_identifiers = list(self.env['res.company']._peppol_supported_document_types())
        failed = False
        for receiver in receivers:
            try:
                receiver._call_peppol_proxy(
                    '/api/peppol/2/add_services',
                    params={'document_identifiers': supported_identifiers},
                )
            # Broad exception case, so as not to block execution of the rest of the _post_init hook.
            except (AccountEdiProxyError, UserError) as exception:
                _logger.error(
                    'Auto registration of peppol services for module: account_peppol_response failed on the user: %s, with exception: %s',
                    receiver.edi_identification, exception,
                )
                failed = True
        if failed:
            if registering_cron := self.env.ref('account_peppol_response.ir_cron_peppol_auto_register_services', raise_if_not_found=False):
                registering_cron._trigger(at=datetime.now() + timedelta(hours=4))
