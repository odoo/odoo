# Part of Odoo. See LICENSE file for full copyright and licensing details.

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

    def test_on_websocket_closed(self):
        session = self.authenticate("demo", "demo")
        headers = {"Cookie": f"session_id={session.sid};"}
        self.env["bus.presence"]._update_presence(
            inactivity_period=0, identity_field="user_id", identity_value=self.user_demo.id
        )
        self.env.cr.precommit.run()  # trigger the creation of bus.bus records
        self.env["bus.bus"].search([]).unlink()
        self.make_jsonrpc_request("/websocket/on_closed", {}, headers=headers)
        self.env.cr.precommit.run()  # trigger the creation of bus.bus records
        message = self.make_jsonrpc_request(
            "/websocket/peek_notifications",
            {"channels": [], "last": 0, "is_first_poll": True},
            headers=headers,
        )["notifications"][0]["message"]
        self.assertEqual(message["type"], "bus.bus/im_status_updated")
        self.assertEqual(message["payload"]["partner_id"], self.partner_demo.id)
        self.assertEqual(message["payload"]["im_status"], "offline")
