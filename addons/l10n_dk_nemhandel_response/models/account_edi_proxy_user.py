from lxml import etree
from markupsafe import Markup

from odoo import api, models
from odoo.exceptions import UserError


class AccountEdiProxyClientUser(models.Model):
    _inherit = 'account_edi_proxy_client.user'

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
            log_message = Markup(self.env._(
                "An error occurred with the Nemhandel proxy while responding to this invoice's expeditor.<br/>Response: %(status)s - %(error)s",
                status=status,
                error=str(e),
            ))
            reference_moves._message_log_batch(
                bodies={move.id: log_message for move in reference_moves},
            )
        else:
            if response.get('error'):
                log_message = Markup(self.env._(
                    "An error occurred with the Nemhandel server while responding to this invoice's expeditor.<br/>Status: %(status)s - %(error)s",
                    status=status,
                    error=response['error']['message'],
                ))
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
                    "A Nemhandel response was sent to the Nemhandel Access Point declaring you %(status)s this document.",
                    status=self.env._('accepted') if status == 'BusinessAccept' else self.env._('rejected'),
                )
                reference_moves._message_log_batch(bodies={move.id: log_message for move in reference_moves})

    @api.model
    def _nemhandel_extract_response_info(self, document):
        doc_tree = etree.fromstring(document)
        blr_status = doc_tree.find('{*}DocumentResponse/{*}Response/{*}ResponseCode').text
        descriptions = doc_tree.findall('{*}DocumentResponse/{*}Response/{*}Description')

        note = ''
        if descriptions:
            note = ' with the following information:'
            for description in descriptions:
                note += '<br/>' + (description.text or 'N/A')

        return blr_status, Markup(note)

    def _nemhandel_process_new_messages(self, messages):
        self.ensure_one()
        processed_messages = {}
        other_messages = {}
        origin_message_uuids = [content['origin_message_uuid'] for content in messages.values()]
        origin_moves = self.env['account.move'].search([('nemhandel_message_uuid', 'in', origin_message_uuids)])
        for uuid, content in messages.items():
            if content['document_type'] == 'ApplicationResponse':
                enc_key = content["enc_key"]
                document_content = content["document"]
                decoded_document = self._decrypt_data(document_content, enc_key)
                blr_status, note = self._nemhandel_extract_response_info(decoded_document)
                response = self.env['nemhandel.response']
                if move := origin_moves.filtered(lambda m: m.nemhandel_message_uuid == content['origin_message_uuid']):
                    if blr_status in {'BusinessAccept', 'BusinessReject'}:
                        response = self.env['nemhandel.response'].create({
                            'nemhandel_message_uuid': uuid,
                            'response_code': blr_status,
                            'nemhandel_state': content['state'],
                            'move_id': move.id,
                        })
                        if content['state'] == 'done':
                            if blr_status == 'BusinessReject':
                                move._message_log(
                                    body=self.env._(
                                        "The Nemhandel receiver of this document has rejected it%(note)s",
                                        note=note or '.',
                                    )
                                )
                            else:
                                move._message_log(
                                    body=self.env._(
                                        "The Nemhandel receiver of this document has accepted it%(note)s",
                                        note=note or '.',
                                    ),
                                )
                    if blr_status in {'TechnicalReject', 'ProfileReject'}:
                        move._message_log(
                            body=self.env._(
                                "An issue arose with your Nemhandel document on the partner's side%(note)s"
                                "%(br)sPlease contact the support if this issue persists.",
                                note=note or '.',
                                br=Markup('<br/>'),
                            ),
                        )
                processed_messages[uuid] = response
            else:
                other_messages[uuid] = content

        processed_messages.update(super()._nemhandel_process_new_messages(other_messages))
        return processed_messages

    def _nemhandel_get_documents_for_status(self, batch_size):
        self.ensure_one()
        documents = super()._nemhandel_get_documents_for_status(batch_size)
        if len(documents) > batch_size:
            return documents

        edi_user_responses = self.env['nemhandel.response'].search(
            [
                ('nemhandel_state', '=', 'processing'),
                ('company_id', '=', self.company_id.id),
            ],
            limit=batch_size - len(documents) + 1,
        )
        return documents + list(edi_user_responses)

    def _nemhandel_process_messages_status(self, messages, uuid_to_record):
        self.ensure_one()
        processed_message_uuids = []
        other_messages = {}
        for uuid, content in messages.items():
            if uuid_to_record[uuid]._name != 'nemhandel.response':
                other_messages[uuid] = content
                continue

            nemhandel_response = uuid_to_record[uuid]
            if content.get('error'):
                if content['error'].get('code') == 702:
                    # "Nemhandel request not ready" error:
                    # thrown when the IAP is still processing the message
                    continue
                if content['error'].get('code') == 207:
                    nemhandel_response.nemhandel_state = 'not_serviced'
                else:
                    nemhandel_response.nemhandel_state = 'error'
                    nemhandel_response.move_id._message_log(
                        body=self.env._("Nemhandel business response error: %s", content['error'].get('data', {}).get('message') or content['error']['message']),
                    )
                processed_message_uuids.append(uuid)
                continue

            nemhandel_response.nemhandel_state = content['state']
            processed_message_uuids.append(uuid)
        return processed_message_uuids + super()._nemhandel_process_messages_status(other_messages, uuid_to_record)
