import os
import time
from datetime import timedelta
from threading import Event
from unittest.mock import patch

from freezegun import freeze_time

from odoo.http.session import SessionExpiredException
from odoo.tests import HttpCase, mute_logger, new_test_user

from odoo.addons.bus.session_helpers import _get_session_token_query_params, check_session
from odoo.addons.bus.tests.common import WebsocketCase
from odoo.addons.bus.websocket import CloseCode, WebsocketConnectionHandler


class TestWebsocketCheckSession(WebsocketCase, HttpCase):
    def test_check_session_deletion_time(self):
        bob = new_test_user(self.env, "bob", groups="base.group_user")
        self.authenticate(bob.login, bob.password)
        with freeze_time() as frozen_time:
            self.session["deletion_time"] = time.time() + 3600
            check_session(self.env.cr, self.session)  # assert it doesn't raise
            frozen_time.tick(delta=timedelta(hours=2))
            with self.assertRaises(SessionExpiredException):
                check_session(self.env.cr, self.session)

    def test_check_session_token_field_changes(self):
        bob = new_test_user(self.env, "bob", groups="base.group_user")
        self.authenticate(bob.login, bob.password)
        check_session(self.env.cr, self.session)  # assert it doesn't raise
        bob.password = "bob_new_password"
        with self.assertRaises(SessionExpiredException):
            check_session(self.env.cr, self.session)

    def test_update_cache_when_registry_changes(self):
        bob = new_test_user(self.env, "bob", groups="base.group_user")
        self.authenticate(bob.login, bob.password)
        bob_query_params = _get_session_token_query_params(self.env.cr, self.session)
        self.assertIs(
            bob_query_params,
            _get_session_token_query_params(self.env.cr, self.session),
        )
        jane = new_test_user(self.env, "jane", groups="base.group_user")
        self.authenticate(jane.login, jane.password)
        current_registry_sequence = self.env.registry.registry_sequence
        # Signaling is patched during test, simulate first entry coming from an old registry.
        with patch.object(self.env.registry, "registry_sequence", current_registry_sequence - 1):
            jane_query_params = _get_session_token_query_params(self.env.cr, self.session)
        next_jane_query_params = _get_session_token_query_params(self.env.cr, self.session)
        self.assertIsNot(jane_query_params, next_jane_query_params)
        self.assertIs(next_jane_query_params, _get_session_token_query_params(self.env.cr, self.session))

    def test_user_login(self):
        websocket = self.websocket_connect()
        new_test_user(self.env, login='test_user', password='Password!1')
        self.authenticate('test_user', 'Password!1')
        # The session with whom the websocket connected has been
        # deleted. WebSocket should disconnect in order for the
        # session to be updated.
        self.subscribe(websocket, wait_for_dispatch=False)
        self.assert_close_with_code(websocket, CloseCode.SESSION_EXPIRED)

    def test_user_logout_incoming_message(self):
        new_test_user(self.env, login='test_user', password='Password!1')
        user_session = self.authenticate('test_user', 'Password!1')
        websocket = self.websocket_connect(cookie=f'session_id={user_session.sid};')
        self.url_open(
            '/web/session/logout',
            method='POST',
            data={
                "csrf_token": self.csrf_token(),
            },
        )
        # The session with whom the websocket connected has been
        # deleted. WebSocket should disconnect in order for the
        # session to be updated.
        self.subscribe(websocket, wait_for_dispatch=False)
        self.assert_close_with_code(websocket, CloseCode.SESSION_EXPIRED)

    def test_user_logout_outgoing_message(self):
        new_test_user(self.env, login='test_user', password='Password!1')
        user_session = self.authenticate('test_user', 'Password!1')
        websocket = self.websocket_connect(cookie=f'session_id={user_session.sid};')
        self.subscribe(websocket, ['channel1'], self.env['bus.bus']._bus_last_id())
        self.url_open(
            '/web/session/logout',
            method='POST',
            data={
                "csrf_token": self.csrf_token(),
            },
        )
        # Simulate postgres notify. The session with whom the websocket
        # connected has been deleted. WebSocket should be closed without
        # receiving the message.
        self.env['bus.bus']._sendone('channel1', 'notif type', 'message')
        self.trigger_notification_dispatching()
        self.assert_close_with_code(websocket, CloseCode.SESSION_EXPIRED)

    @patch.dict(os.environ, {"ODOO_BUS_PUBLIC_SAMESITE_WS": "True"})
    def test_public_configuration(self):
        new_test_user(self.env, login='test_user', password='Password!1')
        user_session = self.authenticate('test_user', 'Password!1')
        serve_forever_called_event = Event()
        original_serve_forever = WebsocketConnectionHandler._serve_forever

        def serve_forever(websocket, *args):
            original_serve_forever(websocket, *args)
            self.assertNotEqual(websocket._session.sid, user_session.sid)
            self.assertNotEqual(websocket._session.uid, user_session.uid)
            serve_forever_called_event.set()

        with (
            patch.object(
                WebsocketConnectionHandler,
                '_serve_forever',
                side_effect=serve_forever,
            ) as mock,
            mute_logger('odoo.addons.bus.websocket'),
        ):
            ws = self.websocket_connect(
                cookie=f'session_id={user_session.sid};',
                origin='http://example.com',
            )
            self.assertTrue(
                ws.getheaders().get('set-cookie').startswith(f'session_id={user_session.sid}'),
                "The set-cookie response header must be the origin request session rather than the websocket session",
            )
            serve_forever_called_event.wait(timeout=5)
            self.assertTrue(mock.called)
