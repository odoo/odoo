# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from freezegun import freeze_time

from odoo.http.session import SESSION_ROTATION_INTERVAL
from odoo.tests import HttpCase, JsonRpcException, new_test_user, tagged

from odoo.addons.bus.tools import notifications as bus_notifications

from .common import BusCase


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestWebsocketController(HttpCase, BusCase):
    def test_websocket_peek(self):
        self._reset_bus()
        self.env["bus.bus"]._sendone("dummy", "dummy_notification", None)  # Subscribing with 0 would fallback to last id.
        self.env.cr.precommit.run()  # Trigger bus record creation.
        initial_last_id = self.env["bus.bus"]._bus_last_id()
        self.env['bus.bus']._sendone('channel_A', 'channel_a_notification', None)
        self.env.cr.precommit.run()  # Trigger bus record creation.
        result = self.make_jsonrpc_request('/websocket/peek_notifications', {
            'channels': ['channel_A'],
            'last': initial_last_id,
            'is_first_poll': True,
        })
        # Response containing channels/notifications is retrieved and is
        # conform to excpectations.
        self.assertIsNotNone(result)
        channels = result.get('channels')
        self.assertIsNotNone(channels)
        self.assertIsInstance(channels, list)
        notifications = result.get('notifications')
        self.assertEqual(notifications[0]['message']['type'], 'channel_a_notification')
        result = self.make_jsonrpc_request('/websocket/peek_notifications', {
            'channels': [],
            'last': initial_last_id,
            'is_first_poll': False,
        })

        # Reponse is received as long as the session is valid.
        self.assertIsNotNone(result)

    def test_websocket_peek_is_paged(self):
        self._reset_bus()
        self.env["bus.bus"]._sendone("dummy", "dummy_notification", None)  # Subscribing with 0 would fallback to last id.
        self.env.cr.precommit.run()  # Trigger bus record creation.
        last = self.env["bus.bus"]._bus_last_id()
        sent_types = [f"notification_{i}" for i in range(5)]
        for type_ in sent_types:
            self.env["bus.bus"]._sendone("channel_A", type_, "x" * 100)
        self.env.cr.precommit.run()  # Trigger bus record creation.
        received_types = []
        is_first_poll = True
        # About 130 bytes per notification. Pages of 3 notifications at most.
        with patch.object(bus_notifications, "BUS_FETCH_MAX_BYTES", 300):
            for _ in range(len(sent_types) + 1):
                result = self.make_jsonrpc_request("/websocket/peek_notifications", {
                    "channels": ["channel_A"],
                    "last": last,
                    "is_first_poll": is_first_poll,
                })
                is_first_poll = False
                if not result["notifications"]:
                    break
                self.assertLessEqual(len(result["notifications"]), 3)
                received_types += [n["message"]["type"] for n in result["notifications"]]
                last = max(n["id"] for n in result["notifications"])
        self.assertEqual(received_types, sent_types)

    def test_websocket_peek_session_expired_login(self):
        # first rpc should be fine
        self.make_jsonrpc_request('/websocket/peek_notifications', {
            'channels': [],
            'last': 0,
            'is_first_poll': True,
        })

        self.authenticate('admin', 'admin')
        # rpc with outdated session should lead to error.
        with self.assertRaises(JsonRpcException, msg='odoo.http.session.SessionExpiredException'):
            self.make_jsonrpc_request('/websocket/peek_notifications', {
                'channels': [],
                'last': 0,
                'is_first_poll': False,
            })

    def test_websocket_peek_session_expired_logout(self):
        test_user = new_test_user(self.env, login="test_user", password="test_user")
        self.authenticate(test_user.login, test_user.password)
        # first rpc should be fine
        self.make_jsonrpc_request('/websocket/peek_notifications', {
            'channels': [],
            'last': 0,
            'is_first_poll': True,
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
                'last': 0,
                'is_first_poll': False,
            })

    @freeze_time("2026-03-03", as_kwarg='clock')
    def test_do_not_rotate_session(self, clock):
        self.authenticate('admin', 'admin')
        self.url_open('/odoo').raise_for_status()
        original_session = self.opener.cookies['session_id']
        clock.tick(SESSION_ROTATION_INTERVAL + 1)
        self.make_jsonrpc_request('/websocket/peek_notifications', {
            'channels': [],
            'last': 0,
            'is_first_poll': True,
        })
        self.make_jsonrpc_request('/websocket/on_closed')
        self.assertEqual(self.opener.cookies['session_id'], original_session,
            "Session rotation must not occur at the websocket routes "
            "that are re-exposed on HTTP for convenience.")
        self.url_open('/odoo').raise_for_status()
        self.assertNotEqual(self.opener.cookies['session_id'], original_session,
            "Session rotation should occur with other URLs.")
