from unittest.mock import MagicMock, patch

import websocket

from odoo.tests import BaseCase, tagged

from ..tools import websocket_protocol
from odoo.addons.integration.tools.stream_protocol import (
    STREAM_PROTOCOLS,
    StreamSnapshot,
)


def _snapshot(url="ws://feed.example:8080/live", **overrides):
    values = {
        "id": 3,
        "db_name": "probe",
        "name": "Feed",
        "protocol": "websocket",
        "url": url,
        "secret": "t0ken",
        "login": "feed",
        "subscriptions": {},
        "heartbeat_seconds": 30,
        "options": {"auth": "bearer", "headers": ["X-Client: odoo"]},
        "addresses": ("10.0.0.5",),
    }
    values.update(overrides)
    return StreamSnapshot(**values)


@tagged("post_install", "-at_install", "integration")
class TestWebsocketProtocol(BaseCase):
    def setUp(self):
        super().setUp()
        self.app = MagicMock()
        self.app.sock = MagicMock(connected=True)
        self.thread = MagicMock()
        self.thread.is_alive.return_value = True
        app_patch = patch.object(
            websocket_protocol.websocket, "WebSocketApp", return_value=self.app
        )
        thread_patch = patch.object(
            websocket_protocol.threading, "Thread", return_value=self.thread
        )
        app_patch.start()
        thread_patch.start()
        self.addCleanup(app_patch.stop)
        self.addCleanup(thread_patch.stop)
        self.protocol = websocket_protocol.WebsocketProtocol()
        self.frames = []
        self.states = []

    def _open(self, snapshot=None):
        return self.protocol.open(
            snapshot or _snapshot(),
            lambda payload, meta: self.frames.append((payload, dict(meta))),
            lambda state, message: self.states.append((state, message)),
        )

    def _app_kwargs(self):
        return websocket_protocol.websocket.WebSocketApp.call_args

    def test_the_protocol_is_registered_under_websocket(self):
        self.assertIs(
            STREAM_PROTOCOLS["websocket"], websocket_protocol.WebsocketProtocol
        )
        self.assertEqual(websocket_protocol.WebsocketProtocol.schemes, ("ws", "wss"))

    def test_a_plain_connection_dials_the_pinned_address_and_names_the_host(self):
        self._open()
        args = self._app_kwargs()
        self.assertEqual(args.args[0], "ws://10.0.0.5:8080/live")
        self.assertIn("Host: feed.example", args.kwargs["header"])
        self.assertIn("Authorization: Bearer t0ken", args.kwargs["header"])
        self.assertIn("X-Client: odoo", args.kwargs["header"])
        self.thread.start.assert_called_once()

    def test_a_tls_connection_dials_by_name_with_the_stream_s_material(self):
        with patch.object(websocket_protocol, "tls_context", return_value="ctx"):
            self._open(_snapshot(url="wss://feed.example/live"))
        args = self._app_kwargs()
        self.assertEqual(args.args[0], "wss://feed.example/live")
        self.assertFalse(any(h.startswith("Host:") for h in args.kwargs["header"]))
        run_kwargs = websocket_protocol.threading.Thread.call_args.kwargs["kwargs"]
        self.assertEqual(run_kwargs["sslopt"], {"context": "ctx"})

    def test_a_plain_connection_carries_no_tls_options(self):
        self._open()
        run_kwargs = websocket_protocol.threading.Thread.call_args.kwargs["kwargs"]
        self.assertNotIn("sslopt", run_kwargs)

    def test_a_basic_login_is_encoded(self):
        self._open(_snapshot(options={"auth": "basic"}))
        header = self._app_kwargs().kwargs["header"]
        self.assertIn("Authorization: Basic ZmVlZDp0MGtlbg==", header)

    def test_the_thread_pings_on_the_heartbeat(self):
        self._open()
        kwargs = websocket_protocol.threading.Thread.call_args.kwargs
        self.assertEqual(kwargs["kwargs"]["ping_interval"], 30)
        self.assertTrue(kwargs["daemon"])

    def test_messages_are_frames_and_events_are_states(self):
        handle = self._open()
        callbacks = self._app_kwargs().kwargs
        callbacks["on_open"](self.app)
        callbacks["on_message"](self.app, '{"kg": 1}')
        callbacks["on_message"](self.app, b"\x00\x01")
        callbacks["on_close"](self.app, 1006, "gone")
        self.assertEqual(
            self.frames,
            [(b'{"kg": 1}', {"binary": False}), (b"\x00\x01", {"binary": True})],
        )
        self.assertEqual(self.states[0], ("open", None))
        self.assertEqual(self.states[1][0], "backoff")
        self.assertIn("1006", self.states[1][1])
        self.assertFalse(handle.closing)

    def test_a_close_the_worker_asked_for_is_not_a_redial(self):
        handle = self._open()
        callbacks = self._app_kwargs().kwargs
        self.protocol.close(handle)
        callbacks["on_close"](self.app, 1000, None)
        callbacks["on_error"](self.app, OSError("closed"))
        self.assertEqual(self.states, [])
        self.app.close.assert_called_once()
        self.thread.join.assert_called_once()

    def test_a_send_is_text_unless_the_frame_says_binary(self):
        handle = self._open()
        self.protocol.send(handle, b"hello", {})
        self.protocol.send(handle, b"\x00", {"binary": True})
        calls = self.app.send.call_args_list
        self.assertEqual(calls[0].kwargs["opcode"], websocket.ABNF.OPCODE_TEXT)
        self.assertEqual(calls[1].kwargs["opcode"], websocket.ABNF.OPCODE_BINARY)

    def test_alive_reads_the_socket_and_the_thread(self):
        handle = self._open()
        self.assertTrue(self.protocol.alive(handle))
        self.app.sock.connected = False
        self.assertFalse(self.protocol.alive(handle))
        self.app.sock.connected = True
        self.thread.is_alive.return_value = False
        self.assertFalse(self.protocol.alive(handle))
