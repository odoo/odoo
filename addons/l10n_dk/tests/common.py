import json

from base64 import b64encode
from contextlib import contextmanager
from urllib.parse import parse_qs, quote_plus, urlsplit

from odoo.tests.common import MockHTTPClient
from odoo.tools.misc import file_open

ID_CLIENT = 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'
REFRESH_TOKEN = 'rrrrrrrr-rrrr-rrrr-rrrr-rrrrrrrrrrrr'
OUTGOING_MESSAGE_UUID = 'yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy'
INCOMING_MESSAGE_UUID = 'zzzzzzzz-zzzz-zzzz-zzzz-zzzzzzzzzzzz'
FILE_PATH = 'l10n_dk/tests/assets'
NEMHANDEL_PROXY_URL = 'https://nemhandel.test.odoo.com'


def _is_lookup_of(identifiers):
    return lambda r: (
        r.method == 'GET'
        and urlsplit(r.url).path.endswith('/lookup')
        and parse_qs(urlsplit(r.url).query)['peppol_identifier'][0] in identifiers
    )


@contextmanager
def mock_nemhandel_lookup_success(identifiers, services=True):
    def result(request):
        identifier = parse_qs(urlsplit(request.url).query)['peppol_identifier'][0]
        quoted = quote_plus(identifier)
        return {'result': {
            'identifier': identifier,
            'smp_base_url': "https://smp-demo.nemhandel.dk",
            'ttl': 60,
            'service_group_url': f'http:///smp-demo.nemhandel.dk/iso6523-actorid-upis%3A%3A{quoted}',
            'services': [{
                'href': f"https://smp-demo.nemhandel.dk/iso6523-actorid-upis%3A%3A{quoted}/services/busdox-docid-qns%3A%3Aurn%3Aoasis%3Anames%3Aspecification%3Aubl%3Aschema%3Axsd%3ACreditNote-2%3A%3ACreditNote%23%23OIOUBL-2.1%3A%3A2.1",
                'document_id': "busdox-docid-qns::urn:oasis:names:specification:ubl:schema:xsd:Invoice-2::Invoice##OIOUBL-2.1::2.1",
            }] if services else [],
        }}

    with MockHTTPClient(matcher=_is_lookup_of(identifiers), return_json=result) as mock_response:
        yield mock_response


@contextmanager
def mock_nemhandel_lookup_not_found(identifiers):
    with MockHTTPClient(
        matcher=_is_lookup_of(identifiers),
        return_status=404,
        return_json={'error': {'code': "NOT_FOUND", 'message': "no naptr record", 'retryable': False}},
    ) as mock_response:
        yield mock_response


@contextmanager
def mock_nemhandel_smp(participants):
    # ``participants`` maps an identifier to the SMP ServiceGroup XML to serve, or ``None`` for a 404.
    def served(request):
        for identifier, body in participants.items():
            if request.url.endswith(quote_plus(f"iso6523-actorid-upis::{identifier}")):
                return body
        return None
    with MockHTTPClient(
        matcher=lambda r: r.method == 'GET' and 'dataudveksling.dk' in r.url,
        return_status=lambda r: 404 if served(r) is None else 200,
        return_body=lambda r: served(r) or b'',
    ) as mock_response:
        yield mock_response


def _nemhandel_jsonrpc_mock(endpoint, result):
    return MockHTTPClient(
        method='POST',
        matcher=lambda r: r.headers.get('Content-Type') == 'application/json',
        url=f'{NEMHANDEL_PROXY_URL}{endpoint}',
        return_json=(lambda r: {'result': result(r)}) if callable(result) else {'result': result},
    )


@contextmanager
def mock_nemhandel_registration(nemhandel_state='receiver'):
    with (
        _nemhandel_jsonrpc_mock('/api/nemhandel/1/connect', {'id_client': ID_CLIENT, 'refresh_token': REFRESH_TOKEN}),
        _nemhandel_jsonrpc_mock('/api/nemhandel/1/register_participant', {}),
        _nemhandel_jsonrpc_mock('/api/nemhandel/1/participant_status', {'nemhandel_state': nemhandel_state}),
        _nemhandel_jsonrpc_mock('/api/nemhandel/1/cancel_nemhandel_registration', {}),
        _nemhandel_jsonrpc_mock('/api/nemhandel/1/update_user', {}),
        _nemhandel_jsonrpc_mock('/api/nemhandel/1/verify_phone_number', {}),
        _nemhandel_jsonrpc_mock('/api/nemhandel/1/send_verification_code', {}),
        _nemhandel_jsonrpc_mock('/api/nemhandel/1/check_user_valid', {'status': 'valid'}),
    ):
        yield


@contextmanager
def mock_nemhandel_send_document():
    def result(request):
        documents = json.loads(request.body)['params']['documents']
        return {'messages': [{'message_uuid': OUTGOING_MESSAGE_UUID}] * len(documents)}
    with _nemhandel_jsonrpc_mock('/api/nemhandel/1/send_document', result):
        yield


@contextmanager
def mock_nemhandel_documents_retrieval(error=False):
    state = 'error' if error else 'done'
    documents = {
        OUTGOING_MESSAGE_UUID: {
            'accounting_supplier_party': False, 'filename': 'test_outgoing.xml', 'enc_key': '', 'document': '',
            'state': state, 'direction': 'outgoing', 'document_type': 'Invoice', 'origin_message_uuid': OUTGOING_MESSAGE_UUID,
        },
        INCOMING_MESSAGE_UUID: {
            'accounting_supplier_party': '0184:16356706', 'filename': 'test_incoming',
            'enc_key': file_open(f'{FILE_PATH}/enc_key', mode='r').read(),
            'document': b64encode(file_open(f'{FILE_PATH}/document', mode='rb').read()).decode(),
            'state': state, 'direction': 'incoming', 'document_type': 'Invoice', 'origin_message_uuid': INCOMING_MESSAGE_UUID,
        },
    }

    def get_document(request):
        uuid = json.loads(request.body)['params']['message_uuids'][0]
        return {uuid: documents[uuid]}

    def send_response(request):
        reference_uuids = json.loads(request.body)['params']['reference_uuids']
        return {'messages': [{'message_uuid': 'rrrrrrrr-rrrr-rrrr-rrrr-rrrrrrrrrrrr'}] * len(reference_uuids)}

    with (
        _nemhandel_jsonrpc_mock('/api/nemhandel/1/ack', {}),
        _nemhandel_jsonrpc_mock('/api/nemhandel/1/get_all_documents', {'messages': [{
            'accounting_supplier_party': '0184:16356706', 'filename': 'test_incoming.xml', 'uuid': INCOMING_MESSAGE_UUID,
            'state': 'done', 'direction': 'incoming', 'document_type': 'Invoice',
            'sender': '0184:16356706', 'receiver': '0088:5798009811512', 'timestamp': '2022-12-30',
            'error': 'Test error' if error else False,
        }]}),
        _nemhandel_jsonrpc_mock('/api/nemhandel/1/get_document', get_document),
        _nemhandel_jsonrpc_mock('/api/nemhandel/1/send_response', send_response),
    ):
        yield
