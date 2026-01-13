import json
from base64 import b64encode
from contextlib import ExitStack, contextmanager
from textwrap import dedent
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
    expected_url = f'https://peppol.test.odoo.com/api/peppol/1/lookup?{urlencode({"peppol_identifier": peppol_identifier})}'
    if services is None:
        services = [
            'urn:oasis:names:specification:ubl:schema:xsd:Invoice-2::Invoice##urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:3.0::2.1',
            'urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2::CreditNote##urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:3.0::2.1',
            'urn:oasis:names:specification:ubl:schema:xsd:ApplicationResponse-2::ApplicationResponse##urn:fdc:peppol.eu:poacc:trns:invoice_response:3::2.1',
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
                    "document_id": f"busdox-docid-qns::{service}",
                }
                for service in services
            ],
        },
    }

    lookup_mock = MockHTTPClient(url=expected_url, return_json=json_response)
    service_group_mocks = []

    # also mock services for SMP name extractions
    for service in json_response['result']['services']:
        response = '''
            <smp:SignedServiceMetadata xmlns:smp="http://busdox.org/serviceMetadata/publishing/1.0/"
                xmlns:ds="http://www.w3.org/2000/09/xmldsig#"
                xmlns:id="http://busdox.org/transport/identifiers/1.0/"
                xmlns:wsa="http://www.w3.org/2005/08/addressing">
                <smp:ServiceMetadata>
                    <smp:ServiceInformation>
                        <smp:ProcessList>
                            <smp:Process>
                                <smp:ServiceEndpointList>
                                    <smp:Endpoint transportProfile="peppol-transport-as4-v2_0">
                                        <smp:ServiceDescription>Definitely not Odoo</smp:ServiceDescription>
                                    </smp:Endpoint>
                                </smp:ServiceEndpointList>
                            </smp:Process>
                        </smp:ProcessList>
                    </smp:ServiceInformation>
                </smp:ServiceMetadata>
            </smp:SignedServiceMetadata>
        '''
        service_group_mocks.append(MockHTTPClient(url=service['href'], return_body=dedent(response)))
    with ExitStack() as stack:
        stack.enter_context(lookup_mock)
        for mock in service_group_mocks:
            stack.enter_context(mock)
        yield lookup_mock, service_group_mocks


@contextmanager
def mock_lookup_not_found(peppol_identifier):
    expected_url = f'https://peppol.test.odoo.com/api/peppol/1/lookup?{urlencode({"peppol_identifier": peppol_identifier})}'
    json_response = {"error": {"code": "NOT_FOUND", "message": "no naptr record", "retryable": False}}
    with MockHTTPClient(url=expected_url, return_status=404, return_json=json_response) as mock_response:
        yield mock_response


@contextmanager
def mock_can_connect(with_auth=False):
    expected_url = 'https://peppol.test.odoo.com/api/peppol/2/can_connect'
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
    expected_url = 'https://peppol.test.odoo.com/api/peppol/2/connect'
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
    with _mock_simple_api_response('https://peppol.test.odoo.com/api/peppol/1/ack') as mock_response:
        yield mock_response


@contextmanager
def mock_register_sender(success=True):
    with _mock_simple_api_response('https://peppol.test.odoo.com/api/peppol/1/register_sender', success) as mock_response:
        yield mock_response


@contextmanager
def mock_register_sender_as_receiver(success=True):
    with _mock_simple_api_response('https://peppol.test.odoo.com/api/peppol/1/register_sender_as_receiver', success) as mock_response:
        yield mock_response


@contextmanager
def mock_get_participant_status(peppol_state: str | None):
    expected_url = 'https://peppol.test.odoo.com/api/peppol/2/participant_status'
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
    with _mock_simple_api_response('https://peppol.test.odoo.com/api/peppol/1/cancel_peppol_registration', success) as mock_response:
        yield mock_response


@contextmanager
def mock_update_user(success=True):
    with _mock_simple_api_response('https://peppol.test.odoo.com/api/peppol/1/update_user', success) as mock_response:
        yield mock_response


@contextmanager
def mock_send_document(messages: list[dict] | None = None):
    def return_json(request: PreparedRequest):
        body = json.loads(request.body)
        num_invoices = len(body['params']['documents'])
        returned_messages = messages if messages is not None else [{'message_uuid': '11111111-1111-4111-8111-111111111111'}] * num_invoices
        assert len(returned_messages) == num_invoices, f"Expected {num_invoices} messages but got {len(returned_messages)}"
        return {'result': {'messages': returned_messages}}
    with MockHTTPClient(method='POST', url='https://peppol.test.odoo.com/api/peppol/1/send_document', return_json=return_json) as mock_response:
        yield mock_response


@contextmanager
def mock_send_response(messages: list[dict] | None = None):
    def return_json(request: PreparedRequest):
        body = json.loads(request.body)
        num_responses = len(body['params']['reference_uuids'])
        returned_messages = messages if messages is not None else [{'message_uuid': '22222222-2222-4222-8222-222222222222'}] * num_responses
        assert len(returned_messages) == num_responses, f"Expected {num_responses} messages but got {len(returned_messages)}"
        return {'result': {'messages': returned_messages}}
    with MockHTTPClient(method='POST', url='https://peppol.test.odoo.com/api/peppol/1/send_response', return_json=return_json) as mock_response:
        yield mock_response


@contextmanager
def mock_documents_retrieval(messages=None, identifier=None):
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
                    'document_type': message.get('document_type', 'Invoice'),
                    'sender': message.get('sender', '0208:2718281828'),
                    'receiver': '0208:0477472701',
                    'timestamp': '2022-12-30',
                    'error': 'Test error' if message.get('state') == 'error' else False,
                } for message in messages
            ],
        }
    }

    send_response_response_json = {
        'result': {
            'messages': [
                {'message_uuid': '22222222-2222-4222-8222-222222222222'}
                for message in all_documents_json['result']['messages']
                if message['direction'] == 'incoming' and message['document_type'] == 'Invoice'
            ],
        },
    }

    def get_document_response_json(request: PreparedRequest):
        uuids = json.loads(request.body)['params']['message_uuids']
        messages_params = {m['uuid']: m for m in messages if m['uuid'] in uuids}

        return {'result': {
            uuid: {
                'accounting_supplier_party': message_params.get('sender', False),
                'filename': f"{message_params.get('filename', 'incoming_invoice')}.xml",
                'enc_key': file_open('account_peppol/tests/assets/enc_key', mode='r').read() if message_params.get('direction', 'incoming') == 'incoming' else '',
                'document': b64encode(file_open(f'account_peppol/tests/assets/{message_params.get("filename", "incoming_invoice")}', mode='rb').read()).decode('utf-8') if message_params.get('direction', 'incoming') == 'incoming' else '',
                'state': message_params.get('state', 'done'),
                'direction': message_params.get('direction', 'incoming'),
                'document_type': message_params.get('document_type', 'Invoice'),
                'origin_message_uuid': message_params.get('origin_message_uuid', uuid),
            } for uuid, message_params in messages_params.items()
        }}

    with (
        MockHTTPClient(method='POST', url='https://peppol.test.odoo.com/api/peppol/1/get_all_documents', return_json=all_documents_json),
        MockHTTPClient(method='POST', url='https://peppol.test.odoo.com/api/peppol/1/get_document', return_json=get_document_response_json),
        MockHTTPClient(method='POST', url='https://peppol.test.odoo.com/api/peppol/1/send_response', return_json=send_response_response_json),
        mock_lookup_success(identifier or '0088:9482348239847239874'),
    ):
        yield
