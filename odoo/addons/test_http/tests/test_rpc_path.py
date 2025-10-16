import logging

from odoo.tests import Like, tagged

from odoo.addons.base.tests.common import HttpCaseWithUserDemo


@tagged('-at_install', 'post_install')
class TestRpcPath(HttpCaseWithUserDemo):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.session = cls.authenticate(cls, 'demo', 'demo')

    def setUp(self):
        super().setUp()
        self.opener.cookies['session_id'] = self.session.sid

    def test_rpc_path_call_button(self):
        with self.assertLogs('werkzeug', logging.INFO) as capture:
            self.make_jsonrpc_request('/web/dataset/call_button', {
                'model': 'res.users',
                'method': 'read',
                'args': [self.user_demo.id],
                'kwargs': {'fields': ['login']}
            })
        self.assertEqual(capture.output, [
            Like('...POST /web/dataset/call_button#res.users.read HTTP/...'),
        ])

    def test_rpc_path_call_kw(self):
        with self.assertLogs('werkzeug', logging.INFO) as capture:
            self.make_jsonrpc_request('/web/dataset/call_kw', {
                'model': 'res.users',
                'method': 'read',
                'args': [self.user_demo.id],
                'kwargs': {'fields': ['login']}
            })
        self.assertEqual(capture.output, [
            Like('...POST /web/dataset/call_kw#res.users.read HTTP/...'),
        ])

    def test_rpc_path_call_kw_with_path(self):
        with self.assertLogs('werkzeug', logging.INFO) as capture:
            self.make_jsonrpc_request('/web/dataset/call_kw/res.users.read', {
                'model': 'res.users',
                'method': 'read',
                'args': [self.user_demo.id],
                'kwargs': {'fields': ['login']}
            })
        self.assertEqual(capture.output, [
            Like('...POST /web/dataset/call_kw/res.users.read HTTP/...'),
        ])
