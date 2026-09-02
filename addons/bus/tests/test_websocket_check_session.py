import os
import time
from datetime import timedelta
from threading import Event
from unittest.mock import patch

from freezegun import freeze_time

from odoo.http.session import session_store
from odoo.tests import HttpCase, mute_logger, new_test_user
from odoo.tools import SQL
from odoo.tools.lru import LRU

from odoo.addons.bus.session_helpers import (
    _get_session_token_query_params,
    _query_params_by_dbname,
    check_sessions,
)
from odoo.addons.bus.tests.common import WebsocketCase
from odoo.addons.bus.websocket import CloseCode, WebsocketConnectionHandler


class TestWebsocketCheckSession(WebsocketCase, HttpCase):
    def test_check_session_deletion_time(self):
        bob = new_test_user(self.env, "bob", groups="base.group_user")
        self.authenticate(bob.login, bob.password)
        with freeze_time() as frozen_time:
            self.session["deletion_time"] = time.time() + 3600
            session_store().save(self.session)
            self.assertIn(self.session.sid, check_sessions(self.env.cr, [self.session]))
            frozen_time.tick(delta=timedelta(hours=2))
            self.assertNotIn(self.session.sid, check_sessions(self.env.cr, [self.session]))

    def test_check_session_token_field_changes(self):
        bob = new_test_user(self.env, "bob", groups="base.group_user")
        self.authenticate(bob.login, bob.password)
        self.assertIn(self.session.sid, check_sessions(self.env.cr, [self.session]))
        bob.password = "bob_new_password"
        self.assertNotIn(self.session.sid, check_sessions(self.env.cr, [self.session]))

    def test_check_session_multiple(self):
        bob = new_test_user(self.env, "bob", groups="base.group_user")
        jane = new_test_user(self.env, "jane", groups="base.group_user")
        john = new_test_user(self.env, "john", groups="base.group_user")
        bob_session = self.authenticate(bob.login, bob.password)
        jane_session = self.authenticate(jane.login, jane.password)
        john_session = self.authenticate(john.login, john.password)
        sessions = [bob_session, jane_session, john_session]
        store = session_store()
        # `authenticate` drops the previous session from the store, put them all back.
        for session in sessions:
            store.save(session)
        self.assertEqual(
            set(check_sessions(self.env.cr, sessions)),
            {bob_session.sid, jane_session.sid, john_session.sid},
        )
        # Invalidate bob (token field change) and john (past deletion time),
        # jane is left untouched. Only jane is returned, unaffected by the
        # invalid sessions surrounding her.
        bob.password = "bob_new_password"
        john_session["deletion_time"] = time.time() - 3600
        store.save(john_session)
        self.assertEqual(set(check_sessions(self.env.cr, sessions)), {jane_session.sid})

    @patch("odoo.addons.bus.session_helpers._stat_by_sid", new_callable=lambda: LRU(4096))
    def test_check_session_cache_hit_skips_session_creation(self, stat_by_sid):
        bob = new_test_user(self.env, "bob", groups="base.group_user")
        self.authenticate(bob.login, bob.password)
        self.assertIn(self.session.sid, check_sessions(self.env.cr, [self.session]))
        self.assertIn(self.session.sid, stat_by_sid)
        with patch.object(
            session_store(),
            "get",
            side_effect=AssertionError("cache hit must not reload the session from disk"),
        ):
            resolved = check_sessions(self.env.cr, [self.session])
            self.assertIs(resolved[self.session.sid], self.session)
        # A real mutation (rotation/logout/save) must still be picked up on the next check.
        self.update_session(deletion_time=time.time() - 3600)
        self.assertNotIn(self.session.sid, check_sessions(self.env.cr, [self.session]))

    @patch("odoo.addons.bus.session_helpers._stat_by_sid", new_callable=lambda: LRU(4096))
    def test_check_session_mtime_collision(self, stat_by_sid):
        bob = new_test_user(self.env, "bob", groups="base.group_user")
        self.authenticate(bob.login, bob.password)
        self.assertIn(self.session.sid, check_sessions(self.env.cr, [self.session]))
        real_fstat = os.fstat

        class _FrozenStat:
            def __init__(self, st):
                self.st_mtime_ns = 123456789
                self.st_ino = st.st_ino

        with patch(
            "odoo.addons.bus.session_helpers.os.fstat",
            side_effect=lambda fd: _FrozenStat(real_fstat(fd)),
        ):
            self.update_session(deletion_time=time.time() - 3600)
            self.assertNotIn(self.session.sid, check_sessions(self.env.cr, [self.session]))

    def test_query_shape_is_user_agnostic(self):
        """The shape cached by `_get_session_token_query_params` must hold
        nothing user specific, since a single entry serves every user."""
        bob = new_test_user(self.env, "bob", groups="base.group_user")
        jane = new_test_user(self.env, "jane", groups="base.group_user")
        model_params = self.env["res.users"]._get_session_token_query_params()
        self.assertEqual(model_params["where"], SQL("res_users.id = %s", False))
        bob_params = _get_session_token_query_params(self.env.cr, [bob.id])
        jane_params = _get_session_token_query_params(self.env.cr, [jane.id])
        self.assertEqual(
            {key: sql for key, sql in bob_params.items() if key != "where"},
            {key: sql for key, sql in jane_params.items() if key != "where"},
        )
        self.assertEqual(bob_params["where"], SQL("res_users.id IN %s", (bob.id,)))
        self.assertEqual(jane_params["where"], SQL("res_users.id IN %s", (jane.id,)))

    def test_update_cache_when_registry_changes(self):
        bob = new_test_user(self.env, "bob", groups="base.group_user")
        self.authenticate(bob.login, bob.password)
        _get_session_token_query_params(self.env.cr, [bob.id])
        bob_params = _query_params_by_dbname[self.env.cr.dbname]["query_params"]
        _get_session_token_query_params(self.env.cr, [bob.id])
        # Cached once, and reused.
        self.assertIs(bob_params, _query_params_by_dbname[self.env.cr.dbname]["query_params"])
        jane = new_test_user(self.env, "jane", groups="base.group_user")
        self.authenticate(jane.login, jane.password)
        current_registry_sequence = self.env.registry.registry_sequence
        _query_params_by_dbname.pop(self.env.cr.dbname, None)
        # Signaling is patched during test, simulate the entry being stored from an old registry.
        with patch.object(self.env.registry, "registry_sequence", current_registry_sequence - 1):
            _get_session_token_query_params(self.env.cr, [jane.id])
        stale_params = _query_params_by_dbname[self.env.cr.dbname]["query_params"]
        _get_session_token_query_params(self.env.cr, [jane.id])
        next_params = _query_params_by_dbname[self.env.cr.dbname]["query_params"]
        # Registry moved on since the stored entry: the shape is rebuilt.
        self.assertIsNot(stale_params, next_params)
        _get_session_token_query_params(self.env.cr, [jane.id])
        self.assertIs(next_params, _query_params_by_dbname[self.env.cr.dbname]["query_params"])

    def test_user_login(self):
        websocket = self.websocket_connect()
        new_test_user(self.env, login='test_user', password='Password!1')
        self.authenticate('test_user', 'Password!1')
        # The session with whom the websocket connected has been
        # deleted. WebSocket should disconnect in order for the
        # session to be updated.
        self.subscribe(websocket, last=self.env["bus.bus"]._bus_last_id(), wait_for_dispatch=False)
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
        self.subscribe(websocket, last=self.env["bus.bus"]._bus_last_id(), wait_for_dispatch=False)
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
            self.wait_for_event(serve_forever_called_event)
            self.assertTrue(mock.called)
