# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo.addons.base.tests.common import HttpCaseWithUserDemo


class TestWebsocketController(HttpCaseWithUserDemo):
    def _make_rpc(self, route, params, headers=None):
        data = json.dumps({
            'id': 0,
            'jsonrpc': '2.0',
            'method': 'call',
            'params': params,
        }).encode()
        headers = headers or {}
        headers['Content-Type'] = 'application/json'
        return self.url_open(route, data, headers=headers)

    def test_websocket_peek(self):
        response = json.loads(
            self._make_rpc('/websocket/peek_notifications', {
                'channels': [],
                'last': 0,
                'is_first_poll': True,
            }).content.decode()
        )
        # Response containing channels/notifications is retrieved and is
        # conform to excpectations.
        result = response.get('result')
        self.assertIsNotNone(result)
        channels = result.get('channels')
        self.assertIsNotNone(channels)
        self.assertIsInstance(channels, list)
        notifications = result.get('notifications')
        self.assertIsNotNone(notifications)
        self.assertIsInstance(notifications, list)

        response = json.loads(
            self._make_rpc('/websocket/peek_notifications', {
                'channels': [],
                'last': 0,
                'is_first_poll': False,
            }).content.decode()
        )
        # Reponse is received as long as the session is valid.
        self.assertIn('result', response)

    def test_websocket_peek_session_expired_login(self):
        session = self.authenticate(None, None)
        # first rpc should be fine
        self._make_rpc('/websocket/peek_notifications', {
            'channels': [],
            'last': 0,
            'is_first_poll': True,
        })

        self.authenticate('admin', 'admin')
        # rpc with outdated session should lead to error.
        headers = {'Cookie': f'session_id={session.sid};'}
        response = json.loads(
            self._make_rpc('/websocket/peek_notifications', {
                'channels': [],
                'last': 0,
                'is_first_poll': False,
            }, headers=headers).content.decode()
        )
        error = response.get('error')
        self.assertIsNotNone(error, 'Sending a poll with an outdated session should lead to error')
        self.assertEqual('odoo.http.SessionExpiredException', error['data']['name'])

    def test_websocket_peek_session_expired_logout(self):
        session = self.authenticate('demo', 'demo')
        # first rpc should be fine
        self._make_rpc('/websocket/peek_notifications', {
            'channels': [],
            'last': 0,
            'is_first_poll': True,
        })
        self.url_open('/web/session/logout')
        # rpc with outdated session should lead to error.
        headers = {'Cookie': f'session_id={session.sid};'}
        response = json.loads(
            self._make_rpc('/websocket/peek_notifications', {
                'channels': [],
                'last': 0,
                'is_first_poll': False,
            }, headers=headers).content.decode()
        )
        error = response.get('error')
        self.assertIsNotNone(error, 'Sending a poll with an outdated session should lead to error')
        self.assertEqual('odoo.http.SessionExpiredException', error['data']['name'])
