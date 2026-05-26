# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time

from odoo.http.session import SESSION_ROTATION_INTERVAL
from odoo.tests import JsonRpcException

from odoo.addons.base.tests.common import HttpCaseWithUserDemo
from odoo.addons.bus.models.bus import BusBus


class TestWebsocketController(HttpCaseWithUserDemo):
    def test_websocket_peek(self):
        self.env['bus.bus']._sendone('channel_A', 'channel_a_notification', None)
        self.env.cr.precommit.run()  # Trigger notification creation.
        result = self.make_jsonrpc_request('/websocket/peek_notifications', {
            'channels': ['channel_A'],
            'is_first_poll': True,
            'from_snapshot': BusBus.get_current_pg_snapshot(self.env.cr),
        })
        # Response containing channels/notifications is retrieved and is
        # conform to excpectations.
        self.assertIsNotNone(result)
        channels = result.get('channels')
        self.assertIsNotNone(channels)
        self.assertIsInstance(channels, list)
        notifications = result.get('notifications')
        self.assertIsInstance(notifications, list)
        self.assertEqual(notifications[0]['message']['type'], 'channel_a_notification')
        self.assertIn('last_fetch_snapshot', result)
        result = self.make_jsonrpc_request('/websocket/peek_notifications', {
            'channels': [],
            'is_first_poll': False,
            'from_snapshot': BusBus.get_current_pg_snapshot(self.env.cr),
        })
        # Reponse is received as long as the session is valid.
        self.assertIsNotNone(result)

    def test_websocket_peek_session_expired_login(self):
        # first rpc should be fine
        self.make_jsonrpc_request('/websocket/peek_notifications', {
            'channels': [],
            'is_first_poll': True,
            'from_snapshot': BusBus.get_current_pg_snapshot(self.env.cr),
        })

        self.authenticate('admin', 'admin')
        # rpc with outdated session should lead to error.
        with self.assertRaises(JsonRpcException, msg='odoo.http.session.SessionExpiredException'):
            self.make_jsonrpc_request('/websocket/peek_notifications', {
                'channels': [],
                'is_first_poll': False,
                'from_snapshot': BusBus.get_current_pg_snapshot(self.env.cr),
            })

    def test_websocket_peek_session_expired_logout(self):
        self.authenticate('demo', 'demo')
        # first rpc should be fine
        self.make_jsonrpc_request('/websocket/peek_notifications', {
            'channels': [],
            'is_first_poll': True,
            'from_snapshot': BusBus.get_current_pg_snapshot(self.env.cr),
        })
        self.url_open('/web/session/logout',
            method='POST',
            data={
                "csrf_token": self.csrf_token(),
            },
        )
        # rpc with outdated session should lead to error.
        with self.assertRaises(JsonRpcException, msg='odoo.http.session.SessionExpiredException'):
            self.make_jsonrpc_request('/websocket/peek_notifications', {
                'channels': [],
                'is_first_poll': False,
                'from_snapshot': BusBus.get_current_pg_snapshot(self.env.cr),
            })

    @freeze_time("2026-03-03", as_kwarg='clock')
    def test_do_not_rotate_session(self, clock):
        self.authenticate('admin', 'admin')
        self.url_open('/odoo').raise_for_status()
        original_session = self.opener.cookies['session_id']
        clock.tick(SESSION_ROTATION_INTERVAL + 1)
        self.make_jsonrpc_request('/websocket/peek_notifications', {
            'channels': [],
            'is_first_poll': True,
            'from_snapshot': BusBus.get_current_pg_snapshot(self.env.cr),
        })
        self.make_jsonrpc_request('/websocket/on_closed')
        self.assertEqual(self.opener.cookies['session_id'], original_session,
            "Session rotation must not occur at the websocket routes "
            "that are re-exposed on HTTP for convenience.")
        self.url_open('/odoo').raise_for_status()
        self.assertNotEqual(self.opener.cookies['session_id'], original_session,
            "Session rotation should occur with other URLs.")
