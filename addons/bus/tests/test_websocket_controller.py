# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.tests import tagged, JsonRpcException
from odoo.addons.base.tests.common import HttpCaseWithUserDemo


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestWebsocketController(HttpCaseWithUserDemo):
    def test_websocket_peek(self):
        result = self.make_jsonrpc_request('/websocket/peek_notifications', {
            'channels': [],
            'last': 0,
            'is_first_poll': True,
        })

        # Response containing channels/notifications is retrieved and is
        # conform to excpectations.
        self.assertIsNotNone(result)
        channels = result.get('channels')
        self.assertIsNotNone(channels)
        self.assertIsInstance(channels, list)
        notifications = result.get('notifications')
        self.assertIsNotNone(notifications)
        self.assertIsInstance(notifications, list)

        result = self.make_jsonrpc_request('/websocket/peek_notifications', {
            'channels': [],
            'last': 0,
            'is_first_poll': False,
        })

        # Reponse is received as long as the session is valid.
        self.assertIsNotNone(result)

    def test_websocket_peek_session_expired_login(self):
        # first rpc should be fine
        self.make_jsonrpc_request('/websocket/peek_notifications', {
            'channels': [],
            'last': 0,
            'is_first_poll': True,
        })

        self.authenticate('admin', 'admin')
        # rpc with outdated session should lead to error.
        with self.assertRaises(JsonRpcException, msg='odoo.http.SessionExpiredException'):
            self.make_jsonrpc_request('/websocket/peek_notifications', {
                'channels': [],
                'last': 0,
                'is_first_poll': False,
            })

    def test_websocket_peek_session_expired_logout(self):
        self.authenticate('demo', 'demo')
        # first rpc should be fine
        self.make_jsonrpc_request('/websocket/peek_notifications', {
            'channels': [],
            'last': 0,
            'is_first_poll': True,
        })
        self.url_open('/web/session/logout',
            method='POST',
            data={
                "csrf_token": http.Request.csrf_token(self),
            },
        )
        # rpc with outdated session should lead to error.
        with self.assertRaises(JsonRpcException, msg='odoo.http.SessionExpiredException'):
            self.make_jsonrpc_request('/websocket/peek_notifications', {
                'channels': [],
                'last': 0,
                'is_first_poll': False,
            })

    def test_do_not_rotate_session(self):
        self.authenticate('admin', 'admin')
        self.url_open('/odoo')
        original_session = self.opener.cookies['session_id']
        original_session_obj = http.root.session_store.get(original_session)
        original_session_obj['create_time'] -= http.SESSION_ROTATION_INTERVAL
        http.root.session_store.save(original_session_obj)
        self.make_jsonrpc_request('/websocket/peek_notifications', {
            'channels': [],
            'last': 0,
            'is_first_poll': True,
        })
        self.assertEqual(self.opener.cookies['session_id'], original_session)
        self.url_open("/odoo")
        self.assertNotEqual(self.opener.cookies['session_id'], original_session)
        original_session = self.opener.cookies['session_id']
        original_session_obj = http.root.session_store.get(original_session)
        original_session_obj['create_time'] -= http.SESSION_ROTATION_INTERVAL
        http.root.session_store.save(original_session_obj)
        self.make_jsonrpc_request('/websocket/on_closed')
        self.assertEqual(self.opener.cookies['session_id'], original_session)
