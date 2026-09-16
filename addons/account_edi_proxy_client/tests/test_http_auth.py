import base64
import hashlib
import hmac
import json
import os
from types import SimpleNamespace
from unittest.mock import patch

import requests
import werkzeug.urls
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from odoo.fields import Selection
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.account_edi_proxy_client.models.account_edi_proxy_auth import OdooEdiProxyAuth
from odoo.addons.account_edi_proxy_client.models.account_edi_proxy_user import AccountEdiProxyError

ID_CLIENT = 'id_client_http_test'
TOKEN = base64.b64encode(os.urandom(32)).decode()
TS = 1700000000
AUTH_TIME = 'odoo.addons.account_edi_proxy_client.models.account_edi_proxy_auth.time.time'
USER_LOGGER = 'odoo.addons.account_edi_proxy_client.models.account_edi_proxy_user'


def expected_sig(message):
    # server-side hmac formula
    return hmac.new(base64.b64decode(TOKEN), message.encode(), digestmod=hashlib.sha256).hexdigest()


def sha(body=b''):
    return hashlib.sha256(body).hexdigest()


def make_response(status, payload=None, content=b''):
    resp = requests.Response()
    resp.status_code = status
    if payload is not None:
        resp._content = json.dumps(payload).encode()
        resp.headers['Content-Type'] = 'application/json'
    else:
        resp._content = content
    return resp


def rte():
    # 401 refresh_token_expired, http shape
    return make_response(401, {'proxy_error': {'code': 'refresh_token_expired', 'message': ''}})


class TestOdooEdiProxyAuthHttp(TransactionCase):
    """ Signer only: no DB record, no HTTP call. """

    def setUp(self):
        super().setUp()
        self.user = SimpleNamespace(id_client=ID_CLIENT, refresh_token=TOKEN, private_key_id=False)
        self.user.sudo = lambda: self.user

    def _sign(self, prepared, **auth_kw):
        with patch(AUTH_TIME, return_value=TS):
            return OdooEdiProxyAuth(user=self.user, **auth_kw)(prepared)

    def test_json_message_unchanged(self):
        payload = {'jsonrpc': '2.0', 'params': {'b': 1, 'a': 2}}
        prepared = requests.Request('POST', 'http://p/api/x', json=payload).prepare()
        signed = self._sign(prepared, routing_type='json')
        message = '%s|%s|%s|%s|%s' % (TS, '/api/x', ID_CLIENT, '{}', json.dumps(payload, sort_keys=True))
        self.assertEqual(signed.headers['odoo-edi-signature'], expected_sig(message))
        self.assertEqual(signed.headers['odoo-edi-signature-type'], 'hmac')

    def test_http_get_with_query(self):
        prepared = requests.Request('GET', 'http://p/api/x?b=1&a=&a=2').prepare()
        signed = self._sign(prepared, routing_type='http')
        message = '%s|%s|%s|%s|%s' % (TS, '/api/x', ID_CLIENT, '{"a": "", "b": "1"}', sha())
        self.assertEqual(signed.headers['odoo-edi-signature'], expected_sig(message))

    def test_http_post_empty_body(self):
        prepared = requests.Request('POST', 'http://p/api/x').prepare()
        signed = self._sign(prepared, routing_type='http')
        message = '%s|%s|%s|%s|%s' % (TS, '/api/x', ID_CLIENT, '{}', sha(b''))
        self.assertEqual(signed.headers['odoo-edi-signature'], expected_sig(message))

    def test_http_post_raw_bytes(self):
        prepared = requests.Request('POST', 'http://p/api/x', data=b'{"k": 1}').prepare()
        signed = self._sign(prepared, routing_type='http')
        message = '%s|%s|%s|%s|%s' % (TS, '/api/x', ID_CLIENT, '{}', sha(b'{"k": 1}'))
        self.assertEqual(signed.headers['odoo-edi-signature'], expected_sig(message))

        prepared2 = requests.Request('POST', 'http://p/api/x', data=b'{"k":1}').prepare()
        signed2 = self._sign(prepared2, routing_type='http')
        self.assertNotEqual(signed.headers['odoo-edi-signature'], signed2.headers['odoo-edi-signature'])

    def test_http_str_body_encoded(self):
        prepared = requests.Request('POST', 'http://p/api/x', data='a=1').prepare()
        signed = self._sign(prepared, routing_type='http')
        message = '%s|%s|%s|%s|%s' % (TS, '/api/x', ID_CLIENT, '{}', sha(b'a=1'))
        self.assertEqual(signed.headers['odoo-edi-signature'], expected_sig(message))

    def test_http_no_headers_without_client_id(self):
        # No routing_type passed: with id_client falsy, __call__ returns before routing_type is ever consulted,
        # so this stays green both before and after the GREEN change (the one RED exception, per the plan).
        self.user.id_client = False
        prepared = requests.Request('GET', 'http://p/api/x').prepare()
        signed = self._sign(prepared)
        self.assertNotIn('odoo-edi-signature', signed.headers)
        self.assertNotIn('odoo-edi-client-id', signed.headers)


@tagged('post_install', '-at_install')
class TestMakeHttpRequest(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        key = cls.env['certificate.key']._generate_rsa_private_key(cls.env.company, name='http_auth_test.key')
        # Overcome the abstract selection field `proxy_type` that has no selection, same workaround as
        # TestAccountEdiProxyUser.
        with patch.object(Selection, 'convert_to_cache', side_effect=lambda value, record, validate=True: value):
            cls.user = cls.env['account_edi_proxy_client.user'].create({
                'id_client': ID_CLIENT,
                'company_id': cls.env.company.id,
                'edi_identification': '1234567890',
                'private_key_id': key.id,
                'edi_mode': 'test',
                'proxy_type': 'test',
                'refresh_token': TOKEN,
            })

    def setUp(self):
        super().setUp()
        type(self).sent, type(self).responses = [], []

    @classmethod
    def _request_handler(cls, s, r, **kw):
        cls.sent.append(r)
        if cls.responses:
            response = cls.responses.pop(0)
            if callable(response):
                return response()
            return response
        return make_response(200, {'ok': True})

    def _assert_signed(self, prepared, body=b''):
        parsed_url = werkzeug.urls.url_parse(prepared.path_url)
        message = '%s|%s|%s|%s|%s' % (
            prepared.headers['odoo-edi-timestamp'],
            parsed_url.path,
            ID_CLIENT,
            json.dumps(werkzeug.urls.url_decode(parsed_url.query), sort_keys=True),
            sha(body),
        )
        self.assertEqual(prepared.headers['odoo-edi-signature'], expected_sig(message))
        self.assertEqual(prepared.headers['odoo-edi-client-id'], ID_CLIENT)

    def test_make_request_json_still_dispatches_proxy_error(self):
        """ Pins the existing (pre-refactor) proxy_error dispatch behaviour of `_make_request`, so the Phase 1
            refactor into `_handle_proxy_error` can be checked against it. """
        # _request_handler is a classmethod bound to the test class at patch time, so it reads `cls.responses` /
        # `cls.sent` — assignments here must go through `type(self)`, not the instance, or they're invisible to it.
        type(self).responses = [make_response(200, {
            'jsonrpc': '2.0', 'id': 1,
            'result': {'proxy_error': {'code': 'client_gone', 'message': 'x'}},
        })]
        with self.assertRaises(AccountEdiProxyError) as cm:
            self.user._make_request('http://proxy.test/api/j', params={})
        self.assertEqual(cm.exception.code, 'client_gone')
        self.assertEqual(cm.exception.message, 'x')

        type(self).sent = []
        type(self).responses = [
            make_response(200, {
                'jsonrpc': '2.0', 'id': 1,
                'result': {'proxy_error': {'code': 'refresh_token_expired', 'message': ''}},
            }),
            make_response(200, {'jsonrpc': '2.0', 'id': 1, 'result': {'v': 1}}),
        ]
        # _make_request commits after _renew_token() (to persist the new token before the retry); TransactionCase
        # forbids cr.commit() from inside a test, so it must be locally re-patched to a no-op for this call.
        with patch.object(type(self.user), '_renew_token') as renew, patch.object(self.env.cr, 'commit'):
            result = self.user._make_request('http://proxy.test/api/j', params={})
        self.assertEqual(result, {'v': 1})
        renew.assert_called_once()
        self.assertEqual(len(self.sent), 2)

    def test_get_ok(self):
        res = self.user._make_http_request('http://proxy.test/api/x', params={'b': '1', 'a': ''})
        self.assertIsInstance(res, requests.Response)
        self.assertEqual(res.json(), {'ok': True})
        self.assertEqual(len(self.sent), 1)
        self.assertEqual(self.sent[0].method, 'GET')
        self.assertEqual(self.sent[0].path_url, '/api/x?b=1&a=')
        self._assert_signed(self.sent[0])

    def test_post_bytes_ok(self):
        self.user._make_http_request(
            'http://proxy.test/api/x', method='POST', data=b'{"k": 1}',
            headers={'content-type': 'application/json'})
        self.assertEqual(self.sent[0].body, b'{"k": 1}')
        self.assertEqual(self.sent[0].headers['content-type'], 'application/json')
        self._assert_signed(self.sent[0], b'{"k": 1}')

    def test_non_bytes_body_refused(self):
        for data in ({'a': '1'}, 'a=1'):
            with self.assertRaises(AccountEdiProxyError) as cm:
                self.user._make_http_request('http://proxy.test/api/x', method='POST', data=data)
            self.assertEqual(cm.exception.code, 'unsupported_content_type')
        self.assertEqual(self.sent, [])

    def test_demo_mode_blocked(self):
        self.user.edi_mode = 'demo'
        with self.assertRaises(AccountEdiProxyError) as cm:
            self.user._make_http_request('http://proxy.test/api/x')
        self.assertEqual(cm.exception.code, 'block_demo_mode')
        self.assertEqual(self.sent, [])

    def test_401_proxy_error_raises(self):
        type(self).responses = [make_response(401, {'proxy_error': {'code': 'client_gone', 'message': 'x'}})]
        with self.assertRaises(AccountEdiProxyError) as cm:
            self.user._make_http_request('http://proxy.test/api/x')
        self.assertEqual(cm.exception.code, 'client_gone')
        self.assertEqual(cm.exception.message, 'x')
        self.assertEqual(len(self.sent), 1)

        type(self).sent = []
        type(self).responses = [make_response(401, {'proxy_error': {'code': 'invalid_signature', 'message': ''}})]
        with self.assertRaises(AccountEdiProxyError) as cm:
            self.user._make_http_request('http://proxy.test/api/x')
        self.assertEqual(cm.exception.code, 'invalid_signature')

    def test_401_refresh_token_expired_retries_once(self):
        type(self).responses = [rte(), make_response(200, {'ok': True})]
        # _handle_proxy_error commits after _renew_token(); re-patch cr.commit to a no-op for this call, see the
        # Phase 1 pin test for why.
        with patch.object(type(self.user), '_renew_token') as renew, patch.object(self.env.cr, 'commit'):
            res = self.user._make_http_request('http://proxy.test/api/x')
        self.assertEqual(res.json(), {'ok': True})
        renew.assert_called_once()
        self.assertEqual(len(self.sent), 2)
        self._assert_signed(self.sent[1])
        self.assertEqual(self.sent[1].method, self.sent[0].method)
        self.assertEqual(self.sent[1].path_url, self.sent[0].path_url)
        self.assertEqual(self.sent[1].body, self.sent[0].body)

    def test_401_refresh_token_expired_twice(self):
        type(self).responses = [rte(), rte()]
        with patch.object(type(self.user), '_renew_token') as renew, patch.object(self.env.cr, 'commit'):
            with self.assertRaises(AccountEdiProxyError) as cm:
                self.user._make_http_request('http://proxy.test/api/x')
        self.assertEqual(cm.exception.code, 'connection_error')
        self.assertEqual(renew.call_count, 2)
        self.assertEqual(len(self.sent), 2)

    def test_401_without_proxy_error(self):
        type(self).responses = [make_response(401, content=b'nope')]
        with self.assertRaises(AccountEdiProxyError) as cm:
            self.user._make_http_request('http://proxy.test/api/x')
        self.assertEqual(cm.exception.code, 'connection_error')
        self.assertEqual(len(self.sent), 1)

    def test_4xx_proxy_error_raises(self):
        # A business-logic error (not an auth failure) can be carried on any non-2xx status, not just 401 —
        # the client must still unpack and preserve the code/message rather than collapsing it into a generic
        # connection_error.
        type(self).responses = [make_response(400, {'proxy_error': {'code': 'invalid_request', 'message': 'bad'}})]
        with self.assertRaises(AccountEdiProxyError) as cm:
            self.user._make_http_request('http://proxy.test/api/x')
        self.assertEqual(cm.exception.code, 'invalid_request')
        self.assertEqual(cm.exception.message, 'bad')
        self.assertEqual(len(self.sent), 1)

    def test_http_error_500(self):
        type(self).responses = [make_response(500)]
        with self.assertLogs(USER_LOGGER, level='WARNING'):
            with self.assertRaises(AccountEdiProxyError) as cm:
                self.user._make_http_request('http://proxy.test/api/x')
        self.assertEqual(cm.exception.code, 'connection_error')

    def test_connection_error(self):
        type(self).responses = [lambda: (_ for _ in ()).throw(requests.exceptions.ConnectionError('boom'))]
        with self.assertRaises(AccountEdiProxyError) as cm:
            self.user._make_http_request('http://proxy.test/api/x')
        self.assertEqual(cm.exception.code, 'connection_error')
        self.assertEqual(len(self.sent), 1)

    def test_asymmetric_http(self):
        res = self.user._make_http_request('http://proxy.test/api/x', auth_type='asymmetric')
        self.assertEqual(res.json(), {'ok': True})
        prepared = self.sent[0]
        self.assertEqual(prepared.headers['odoo-edi-signature-type'], 'asymmetric')

        parsed_url = werkzeug.urls.url_parse(prepared.path_url)
        message = '%s|%s|%s|%s|%s' % (
            prepared.headers['odoo-edi-timestamp'],
            parsed_url.path,
            ID_CLIENT,
            json.dumps(werkzeug.urls.url_decode(parsed_url.query), sort_keys=True),
            sha(),
        )
        public_key = serialization.load_pem_public_key(
            self.user.private_key_id._get_public_key_bytes(encoding='pem', formatting='raw'))
        # Raises cryptography.exceptions.InvalidSignature (failing the test) if the signature doesn't verify.
        public_key.verify(
            base64.b64decode(prepared.headers['odoo-edi-signature']),
            message.encode(),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
