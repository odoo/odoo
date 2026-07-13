import json
from base64 import b64encode
from requests import PreparedRequest, Response, Session
from urllib.parse import parse_qs

from odoo.exceptions import UserError
from odoo.tests.common import tagged
from odoo.tools.misc import file_open

from odoo.addons.account.tests.test_account_move_send import TestAccountMoveSendCommon

from .common import FAKE_UUID, FILE_PATH, TestL10nFrPdpCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestPdpMessagesCommon(TestL10nFrPdpCommon, TestAccountMoveSendCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='fr'):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.env.company.account_peppol_proxy_state = 'active'

    @classmethod
    def _get_mock_data(cls, error=False, nr_invoices=1):
        proxy_documents = {
            FAKE_UUID[0]: {
                'accounting_supplier_party': False,
                'filename': 'test_outgoing.xml',
                'enc_key': '',
                'document': '',
                'state': 'done' if not error else 'error',
                'direction': 'outgoing',
                'document_type': 'Invoice',
                'origin_message_uuid': FAKE_UUID[0],
            },
            FAKE_UUID[1]: {
                'accounting_supplier_party': '0184:16356706',
                'filename': 'test_incoming',
                'enc_key': file_open(f'{FILE_PATH}/enc_key', mode='rb').read(),
                'document': b64encode(file_open(f'{FILE_PATH}/document', mode='rb').read()),
                'state': 'done' if not error else 'error',
                'direction': 'incoming',
                'document_type': 'Invoice',
                'origin_message_uuid': FAKE_UUID[1],
            },
        }

        responses = {
            '/api/pdp/1/send_document': {'result': {'messages': [{'message_uuid': FAKE_UUID[0]}] * nr_invoices}},
            '/api/pdp/1/send_response': {'result': {'messages': [{'message_uuid': FAKE_UUID[2]}] * nr_invoices}},
            # '/api/pdp/1/get_document' is handled separately in _request_handler
            '/api/pdp/1/ack': {'result': {}},
            '/api/pdp/1/get_all_documents': {'result': {
                'messages': [
                    {
                        'accounting_supplier_party': None,
                        'filename': 'test_incoming.xml',
                        'uuid': FAKE_UUID[1],
                        'origin_message_uuid': FAKE_UUID[1],
                        'state': 'done',
                        'direction': 'incoming',
                        'document_type': 'Invoice',
                        'sender': '0184:16356706',
                        'receiver': '0088:5798009811512',
                        'timestamp': '2022-12-30',
                        'error': False if not error else 'Test error',
                    }
                ],
            }},
            '/api/pdp/1/get_all_ppf_documents': {'result': {}},
        }
        return proxy_documents, responses

    @classmethod
    def _request_handler(cls, s: Session, r: PreparedRequest, /, **kw):

        if r.path_url.startswith('/api/pdp/1/annuaire_lookup?pdp_identifier='):
            identifier = parse_qs(r.path_url.rsplit('?')[1])['pdp_identifier'][0]
            return cls._get_annuaire_lookup_response(identifier, "968515759_96851575905823")
        elif r.path_url.startswith('/api/pdp/1/lookup?peppol_identifier='):
            identifier = parse_qs(r.path_url.rsplit('?')[1])['peppol_identifier'][0]
            return cls._get_peppol_lookup_response(identifier, "0208:0239843188")
        elif r.path_url.startswith('/api/peppol/1/lookup?peppol_identifier='):
            identifier = parse_qs(r.path_url.rsplit('?')[1])['peppol_identifier'][0]
            return cls._get_peppol_lookup_response(identifier, "0225:968515759_96851575905899")

        response = Response()
        response.status_code = 200
        url = r.path_url
        body = json.loads(r.body)
        if url == '/api/pdp/1/send_document':
            if not body['params']['documents']:
                raise UserError('No documents were provided')
            proxy_documents, responses = cls._get_mock_data(cls.env.context.get('error'), nr_invoices=len(body['params']['documents']))
        elif url == '/api/pdp/1/send_response':
            if 'send_response_params' in cls.env.context:
                cls.env.context['send_response_params'] = body['params']
            proxy_documents, responses = cls._get_mock_data(cls.env.context.get('error'), nr_invoices=len(body['params']['reference_uuids']))
        else:
            proxy_documents, responses = cls._get_mock_data(cls.env.context.get('error'))

        if url == '/api/pdp/1/get_document':
            uuid = body['params']['message_uuids'][0]
            response.json = lambda: {'result': {uuid: proxy_documents[uuid]}}
            return response

        if url not in responses:
            return super()._request_handler(s, r, **kw)
        response.json = lambda: responses[url]
        return response
