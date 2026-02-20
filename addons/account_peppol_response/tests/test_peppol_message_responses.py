import json

from base64 import b64encode
from requests import PreparedRequest, Response, Session

from odoo.tests.common import tagged, freeze_time
from odoo.tools.misc import file_open

from odoo.addons.account_peppol.tests.test_peppol_messages import FAKE_UUID, TestPeppolMessage

FAKE_OUTGOING_RESPONSE_UUID = {
    'AB': 'abababab-abab-abab-abab-abababababab',
    'AP': 'apapapap-apap-apap-apap-apapapapapap',
    'RE': 'rererere-rere-rere-rere-rererererere',
}
FAKE_INCOMING_RESPONSE_UUID = 'fakefake-fake-fake-fake-fakefakefake'
RESPONSE_FILE_PATH = 'account_peppol_response/tests/assets'


@freeze_time('2023-01-01')
@tagged('-at_install', 'post_install')
class TestPeppolMessageResponse(TestPeppolMessage):

    @classmethod
    def _get_incoming_response_content(cls):
        with file_open(f'{RESPONSE_FILE_PATH}/response_document', mode='rb') as f:
            return f.read()

    @classmethod
    def _request_handler(cls, s: Session, r: PreparedRequest, /, **kw):
        response = Response()
        url = r.path_url.lower()
        if url == '/api/peppol/1/send_response':
            body = json.loads(r.body)
            response.status_code = 200
            response.json = lambda: {'result': {
                'messages': [{'message_uuid': FAKE_OUTGOING_RESPONSE_UUID[body['params']['status']]}] * len(body['params']['reference_uuids'])
            }}
            return response

        if url == '/api/peppol/1/get_document':
            response = super()._request_handler(s, r, **kw)
            results = response.json()['result']
            body = json.loads(r.body)
            uuids = body['params']['message_uuids']
            enc_key = file_open(f'{RESPONSE_FILE_PATH}/enc_key', mode='rb').read()
            results.update({
                **{
                    FAKE_OUTGOING_RESPONSE_UUID[code]: {
                        'accounting_supplier_party': False,
                        'filename': 'test_outgoing.xml',
                        'enc_key': '',
                        'document': '',
                        'state': 'done' if not cls.env.context.get('error') else 'error',
                        'direction': 'outgoing',
                        'document_type': 'ApplicationResponse',
                        'origin_message_uuid': 'not_used_when_fetching_status',
                    } for code in FAKE_OUTGOING_RESPONSE_UUID
                },
                FAKE_INCOMING_RESPONSE_UUID: {
                    'accounting_supplier_party': False,
                    'filename': 'test_incoming_resp.xml',
                    'enc_key': enc_key,
                    'document': b64encode(cls._get_incoming_response_content()),
                    'state': 'done' if not cls.env.context.get('error') else 'error',
                    'direction': 'incoming',
                    'document_type': 'ApplicationResponse',
                    'origin_message_uuid': 'move_uuid_that_does_not_exist_on_user_db',
                }
            })
            response.json = lambda: {
                'result': {
                    uuid: results[uuid] for uuid in uuids
                }
            }
            return response

        if url == '/api/peppol/1/get_all_documents':
            response = super()._request_handler(s, r, **kw)
            json_content = response.json()
            json_content['result']['messages'].append({
                'accounting_supplier_party': '0198:dk16356706',
                'filename': 'test_incoming_resp.xml',
                'uuid': FAKE_INCOMING_RESPONSE_UUID,
                'state': 'done',
                'direction': 'incoming',
                'document_type': 'ApplicationResponse',
                'sender': '0198:dk16356706',
                'receiver': '0208:0477472701',
                'timestamp': '2022-12-30',
                'error': False if not cls.env.context.get('error') else 'Test error',
                'business_type': 'AP',
            })
            response.json = lambda: json_content
            return response
        return super()._request_handler(s, r, **kw)

    def test_accept_response_peppol(self):
        """ Tests a basic flow of receiving a bill and accept it with the Business Level Response """
        self.env['account_edi_proxy_client.user']._cron_peppol_get_new_documents()

        move = self.env['account.move'].search([('peppol_message_uuid', '=', FAKE_UUID[1])])
        self.assertRecordValues(
            move, [{
                'peppol_move_state': 'done',
                'move_type': 'in_invoice',
                'state': 'draft',
            }])

        self.assertRecordValues(
            move.peppol_response_ids, [{
                'peppol_state': 'processing',
                'response_code': 'AB',
            }]
        )
        self.env['account_edi_proxy_client.user']._cron_peppol_get_message_status()
        self.assertEqual(move.peppol_move_state, 'AB')

        move.currency_id.active = True
        # Posting the bill should send an acceptance response
        move.action_post()
        peppol_accept_response = move.peppol_response_ids.filtered(lambda r: r.response_code == 'AP')
        self.assertRecordValues(
            peppol_accept_response, [{
                'peppol_state': 'processing',
                'response_code': 'AP',
            }]
        )
        self.env['account_edi_proxy_client.user']._cron_peppol_get_message_status()
        self.assertEqual(move.peppol_move_state, 'AP')

    def test_reject_response_peppol(self):
        """ Tests a basic flow of receiving a bill and accept it with the Business Level Response """
        self.env['account_edi_proxy_client.user']._cron_peppol_get_new_documents()

        move = self.env['account.move'].search([('peppol_message_uuid', '=', FAKE_UUID[1])])
        self.assertRecordValues(
            move, [{
                'peppol_move_state': 'done',
                'move_type': 'in_invoice',
                'state': 'draft',
            }])

        self.assertRecordValues(
            move.peppol_response_ids, [{
                'peppol_state': 'processing',
                'response_code': 'AB',
            }]
        )
        self.env['account_edi_proxy_client.user']._cron_peppol_get_message_status()
        self.assertEqual(move.peppol_move_state, 'AB')

        # Canceling the bill should return an action to open the rejection wizard
        res = move.button_cancel()
        self.assertEqual(res['res_model'], 'account.peppol.rejection.wizard')

        rejection_wizard = self.env[res['res_model']].browse(res['res_id'])
        rejection_wizard.button_send()
        peppol_accept_response = move.peppol_response_ids.filtered(lambda r: r.response_code == 'RE')
        self.assertRecordValues(
            peppol_accept_response, [{
                'peppol_state': 'processing',
                'response_code': 'RE',
            }]
        )
        self.env['account_edi_proxy_client.user']._cron_peppol_get_message_status()
        self.assertEqual(move.peppol_move_state, 'RE')

    def test_receive_response_to_inexisting_invoices(self):
        """ Tests the case where we receive responses to invoices that we don't have in DB.
            This can happen if a user send invoices from somewhere else than its receiver endpoint.
        """
        self.create_move(self.valid_partner)
        # With get new documents and the patched request handler, we should receive an acceptance ('AP') Business Response.
        # As no existing invoice is referenced by it, it should just be acked to the server and dropped.
        # The only (valid) response at this point should be the automatic Acknowledgement ('AB') sent when receiving the move with peppol_message_uuid == FAKE_UUID[1]
        self.env['account_edi_proxy_client.user']._cron_peppol_get_new_documents()

        imported_move = self.env['account.move'].search([('peppol_message_uuid', '!=', False)])
        self.assertEqual(len(imported_move.peppol_response_ids), 1)
        self.assertEqual(imported_move.peppol_response_ids.response_code, 'AB')

        all_peppol_responses = self.env['account.peppol.response'].search([])
        self.assertEqual(len(all_peppol_responses), 1)
