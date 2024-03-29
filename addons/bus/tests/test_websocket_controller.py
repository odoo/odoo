# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo.tests import JsonRpcException
from odoo.addons.base.tests.common import HttpCaseWithUserDemo


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
        session = self.authenticate(None, None)
        # first rpc should be fine
        self.make_jsonrpc_request('/websocket/peek_notifications', {
            'channels': [],
            'last': 0,
            'is_first_poll': True,
        })

        self.authenticate('admin', 'admin')
        # rpc with outdated session should lead to error.
        headers = {'Cookie': f'session_id={session.sid};'}
        with self.assertRaises(JsonRpcException, msg='odoo.http.SessionExpiredException'):
            self.make_jsonrpc_request('/websocket/peek_notifications', {
                'channels': [],
                'last': 0,
                'is_first_poll': False,
            }, headers=headers)

    def test_websocket_peek_session_expired_logout(self):
        session = self.authenticate('demo', 'demo')
        # first rpc should be fine
        self.make_jsonrpc_request('/websocket/peek_notifications', {
            'channels': [],
            'last': 0,
            'is_first_poll': True,
        })
        self.url_open('/web/session/logout')
        # rpc with outdated session should lead to error.
        headers = {'Cookie': f'session_id={session.sid};'}
        with self.assertRaises(JsonRpcException, msg='odoo.http.SessionExpiredException'):
            self.make_jsonrpc_request('/websocket/peek_notifications', {
                'channels': [],
                'last': 0,
                'is_first_poll': False,
            }, headers=headers)
