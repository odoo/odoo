import json
from base64 import b64encode
from contextlib import contextmanager
from urllib.parse import quote_plus, urlencode

from requests import PreparedRequest

from odoo.tests.common import MockHTTPClient
from odoo.tools import file_open

__all__ = [
    'mock_ack',
    'mock_can_connect',
    'mock_cancel_peppol_registration',
    'mock_connect',
    'mock_documents_retrieval',
    'mock_get_participant_status',
    'mock_lookup_not_found',
    'mock_lookup_success',
    'mock_register_sender',
    'mock_register_sender_as_receiver',
    'mock_send_document',
    'mock_update_user',
]


@contextmanager
def _mock_simple_api_response(url, success=True):
    with MockHTTPClient(
        url=url,
        return_json={'result': {}} if success else {'error': {'code': "spoutch", 'message': "failure"}}
    ) as mock_response:
        yield mock_response


@contextmanager
def mock_lookup_success(peppol_identifier, services=None):
    expected_url = f'/api/peppol/1/lookup?{urlencode({"peppol_identifier": peppol_identifier})}'
    if services is None:
        services = [
            'urn:oasis:names:specification:ubl:schema:xsd:Invoice-2::Invoice##urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:3.0::2.1',
            'urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2::CreditNote##urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:3.0::2.1',
        ]
    json_response = {
        "result": {
            'identifier': peppol_identifier,
            'smp_base_url': "http://iap-services.odoo.com",
            'ttl': 60,
            'service_group_url': f'http://iap-services.odoo.com/iso6523-actorid-upis%3A%3A{quote_plus(peppol_identifier)}',
            'services': [
                {
                    "href": f"http://iap-services.odoo.com/iso6523-actorid-upis%3A%3A{quote_plus(peppol_identifier)}/services/busdox-docid-qns%3A%3A{quote_plus(service)}",
                    "document_id": service,
                }
                for service in services
            ],
        },
    }
    with MockHTTPClient(url=expected_url, return_json=json_response) as mock_response:
        yield mock_response


@contextmanager
def mock_lookup_not_found(peppol_identifier):
    expected_url = f'/api/peppol/1/lookup?{urlencode({"peppol_identifier": peppol_identifier})}'
    json_response = {"error": {"code": "NOT_FOUND", "message": "no naptr record", "retryable": False}}
    with MockHTTPClient(url=expected_url, return_status=404, return_json=json_response) as mock_response:
        yield mock_response


@contextmanager
def mock_can_connect(with_auth=False):
    expected_url = '/api/peppol/2/can_connect'
    auth_vals = {
        'available_auths': {
            'itsme': {'authorization_url': 'test_authorization_url'},
        },
    } if with_auth else {}
    with MockHTTPClient(url=expected_url, return_json={
        'auth_required': with_auth,
        **auth_vals,
    }) as mock_response:
        yield mock_response


@contextmanager
def mock_connect(success=True, peppol_state='smp_registration', id_client='test_id_client'):
    expected_url = '/api/peppol/2/connect'
    if peppol_state == 'rejected':
        json_response = {
            'code': 201,
            'message': 'Unable to register, please contact our support team at peppol.support@odoo.com.',
        }
        status_code = 403
    elif success:
        json_response = {'id_client': id_client, 'refresh_token': 'test_refresh_token', 'peppol_state': peppol_state}
        status_code = 200
    else:
        json_response = {
            'code': 208,
            'message': 'The Authentication failed',
        }
        status_code = 401
    with MockHTTPClient(url=expected_url, return_json=json_response, return_status=status_code) as mock_response:
        yield mock_response


@contextmanager
def mock_ack():
    with _mock_simple_api_response('/api/peppol/1/ack') as mock_response:
        yield mock_response


@contextmanager
def mock_register_sender(success=True):
    with _mock_simple_api_response('/api/peppol/1/register_sender', success) as mock_response:
        yield mock_response


@contextmanager
def mock_register_sender_as_receiver(success=True):
    with _mock_simple_api_response('/api/peppol/1/register_sender_as_receiver', success) as mock_response:
        yield mock_response


@contextmanager
def mock_get_participant_status(peppol_state: str | None):
    expected_url = '/api/peppol/2/participant_status'
    if peppol_state:
        json_response = {'result': {'peppol_state': peppol_state}}
    else:
        json_response = {
            'result': {
                'error': {
                    'code': "client_gone",
                    'message': "Your registration for this service is no longer valid. "
                               "If you see this message, please update the related Odoo app. "
                               "You will then be able to re-register if needed.",
                },
            },
        }
    with MockHTTPClient(url=expected_url, return_json=json_response) as mock_response:
        yield mock_response


@contextmanager
def mock_cancel_peppol_registration(success=True):
    with _mock_simple_api_response('/api/peppol/1/cancel_peppol_registration', success) as mock_response:
        yield mock_response


@contextmanager
def mock_update_user(success=True):
    with _mock_simple_api_response('/api/peppol/1/update_user', success) as mock_response:
        yield mock_response


@contextmanager
def mock_send_document(messages: list[dict] | None = None):
    def return_json(request: PreparedRequest):
        body = json.loads(request.body)
        num_invoices = len(body['params']['documents'])
        returned_messages = messages if messages is not None else [{'message_uuid': '11111111-1111-4111-8111-111111111111'}] * num_invoices
        assert len(returned_messages) == num_invoices, f"Expected {num_invoices} messages but got {len(returned_messages)}"
        return {'result': {'messages': returned_messages}}
    with MockHTTPClient(method='POST', url='/api/peppol/1/send_document', return_json=return_json) as mock_response:
        yield mock_response


@contextmanager
def mock_documents_retrieval(messages=None):
    if messages is None:
        messages = [
            {'uuid': '11111111-1111-4111-8111-111111111111', 'direction': 'incoming', 'filename': 'incoming_invoice', 'state': 'done', 'sender': '0208:2718281828'},
        ]

    all_documents_json = {
        'result': {
            'messages': [
                {
                    'accounting_supplier_party': message.get('sender', False),
                    'filename': f"{message.get('filename', 'incoming_invoice')}.xml",
                    'uuid': message['uuid'],
                    'state': message.get('state', 'done'),
                    'direction': message.get('direction', 'incoming'),
                    'document_type': 'Invoice',
                    'sender': message.get('sender', '0208:2718281828'),
                    'receiver': '0208:0477472701',
                    'timestamp': '2022-12-30',
                    'error': 'Test error' if message.get('state') == 'error' else False,
                } for message in messages
            ],
        }
    }

    def get_document_response_json(request: PreparedRequest):
        uuid = json.loads(request.body)['params']['message_uuids'][0]
        message_params = next((m for m in messages if m['uuid'] == uuid), {})
        direction = message_params.get('direction') or 'incoming'

        return {'result': {uuid: {
            'accounting_supplier_party': message_params.get('sender', False),
            'filename': f"{message_params.get('filename', 'incoming_invoice')}.xml",
            'enc_key': file_open('account_peppol/tests/assets/enc_key', mode='r').read() if direction == 'incoming' else '',
            'document': b64encode(file_open(f'account_peppol/tests/assets/{message_params.get("filename", "incoming_invoice")}', mode='rb').read()).decode('utf-8') if direction == 'incoming' else '',
            'state': message_params.get('state', 'done'),
            'direction': direction,
            'document_type': 'Invoice',
        }}}

    with (
        MockHTTPClient(method='POST', url='/api/peppol/1/get_all_documents', return_json=all_documents_json),
        MockHTTPClient(method='POST', url='/api/peppol/1/get_document', return_json=get_document_response_json),
    ):
        yield
