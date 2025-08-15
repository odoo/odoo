import json
from odoo.tools import mute_logger
from odoo.tests import tagged
from odoo.addons.test_http.controllers import CT_JSON
from .test_common import TestHttpBase


@tagged('post_install', '-at_install')
class TestHttpErrorHttp(TestHttpBase):
    @mute_logger('odoo.http')  # UserError("Walter is AFK")
    def test_httperror0_exceptions_as_404(self):
        with self.subTest('Decorator/AccessError'):
            res = self.nodb_url_open('/test_http/hide_errors/decorator?error=AccessError')
            self.assertEqual(res.status_code, 404, "AccessError are configured to be hidden, they should be re-thrown as NotFound")
            self.assertNotIn("Wrong iris code", res.text, "The real AccessError message should be hidden.")

        with self.subTest('Decorator/UserError'):
            res = self.nodb_url_open('/test_http/hide_errors/decorator?error=UserError')
            self.assertEqual(res.status_code, 400, "UserError are not configured to be hidden, they should be kept as-is.")
            self.assertIn("Walter is AFK", res.text, "The real UserError message should be kept")

        with self.subTest('Context-Manager/AccessError'):
            res = self.nodb_url_open('/test_http/hide_errors/context-manager?error=AccessError')
            self.assertEqual(res.status_code, 404, "AccessError are configured to be hidden, they should be re-thrown as NotFound")
            self.assertNotIn("Wrong iris code", res.text, "The real AccessError message should be hidden.")

        with self.subTest('Context-Manager/UserError'):
            res = self.nodb_url_open('/test_http/hide_errors/context-manager?error=UserError')
            self.assertEqual(res.status_code, 400, "UserError are not configured to be hidden, they should be kept as-is.")
            self.assertIn("Walter is AFK", res.text, "The real UserError message should be kept")


@tagged('post_install', '-at_install')
class TestHttpJsonError(TestHttpBase):

    jsonrpc_error_structure = {
        'error': {
            'code': ...,
            'data': {
                'arguments': ...,
                'context': ...,
                'debug': ...,
                'message': ...,
                'name': ...,
            },
            'message': ...,
        },
        'id': ...,
        'jsonrpc': ...,
    }

    def assertIsErrorPayload(self, payload):
        self.assertEqual(
            set(payload),
            set(self.jsonrpc_error_structure),
        )
        self.assertEqual(
            set(payload['error']),
            set(self.jsonrpc_error_structure['error']),
        )
        self.assertEqual(
            set(payload['error']['data']),
            set(self.jsonrpc_error_structure['error']['data']),
        )


    @mute_logger('odoo.http')
    def test_errorjson0_value_error(self):
        res = self.db_url_open('/test_http/json_value_error',
            data=json.dumps({'jsonrpc': '2.0', 'id': 1234, 'params': {}}),
            headers=CT_JSON
        )
        res.raise_for_status()

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get('Content-Type', ''), 'application/json; charset=utf-8')

        payload = res.json()
        self.assertIsErrorPayload(payload)

        error_data = payload['error']['data']
        self.assertEqual(error_data['name'], 'builtins.ValueError')
        self.assertEqual(error_data['message'], 'Unknown destination')
        self.assertEqual(error_data['arguments'], ['Unknown destination'])
        self.assertEqual(error_data['context'], {})
