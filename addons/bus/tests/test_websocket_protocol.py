import base64
import json
import os
import struct
import time
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from werkzeug.exceptions import BadRequest, ServiceUnavailable

from odoo.db import PoolError
from odoo.http import MemorySessionStore, Session, SessionExpiredException
from odoo.tests.common import BaseCase, tagged

try:
    from websocket import ABNF, WebSocketConnectionClosedException
except ImportError:
    ABNF = WebSocketConnectionClosedException = None

from .. import websocket as websocket_module
from ..websocket import (
    MAX_TRY_ON_POOL_ERROR,
    CloseCode,
    CloseFrame,
    ConnectionClosedError,
    ConnectionState,
    ControlCommand,
    Frame,
    InvalidCloseCodeError,
    NotificationDispatchState,
    Opcode,
    PayloadTooLargeError,
    PollablePriorityQueue,
    ProtocolError,
    TimeoutManager,
    UpgradeRequired,
    Websocket,
    WebsocketConnectionHandler,
    _follow_session_chain,
    acquire_cursor,
)
from .common import WebsocketCase


class _ManualClock:
    def __init__(self, now=0.0):
        self.now = now

    def __call__(self):
        return self.now


class _FakeSocket:
    def __init__(self, data=b""):
        self._buf = bytearray(data)
        self.sent = bytearray()

    def recv(self, n):
        if not self._buf:
            return b""
        chunk = bytes(self._buf[:n])
        del self._buf[:n]
        return chunk

    def sendall(self, data):
        self.sent.extend(data)


class _StallingSocket:
    def __init__(self, header):
        self._header = bytearray(header)
        self.sent = bytearray()
        self.recv_calls = 0

    def recv(self, n):
        self.recv_calls += 1
        if self._header:
            chunk = bytes(self._header[:n])
            del self._header[:n]
            return chunk
        return b"\x00"

    def sendall(self, data):
        self.sent.extend(data)


def _client_frame(
    opcode, payload=b"", *, fin=True, rsv1=False, masked=True, seven_bit_len=None
):
    b0 = (0x80 if fin else 0) | (0x40 if rsv1 else 0) | int(opcode)
    out = bytearray([b0])
    length = len(payload) if seven_bit_len is None else seven_bit_len
    mask_bit = 0x80 if masked else 0
    if length < 126:
        out.append(mask_bit | length)
    elif length < 65536:
        out.append(mask_bit | 126)
        out += struct.pack("!H", length)
    else:
        out.append(mask_bit | 127)
        out += struct.pack("!Q", length)
    if masked:
        out += b"\x00\x00\x00\x00"
    out += payload
    return bytes(out)


@tagged("-at_install", "post_install")
class TestHandshakeValidation(BaseCase):
    def _valid_headers(self):
        return {
            "connection": "Upgrade",
            "host": "localhost:8069",
            "sec-websocket-key": base64.b64encode(b"0123456789abcdef").decode(),
            "sec-websocket-version": "13",
            "upgrade": "websocket",
            "origin": "http://localhost:8069",
        }

    def test_valid_handshake_succeeds(self):
        WebsocketConnectionHandler._assert_handshake_validity(self._valid_headers())

    def test_missing_required_header(self):
        for header in WebsocketConnectionHandler._REQUIRED_HANDSHAKE_HEADERS:
            headers = self._valid_headers()
            del headers[header]
            with self.assertRaises(BadRequest, msg=f"Missing {header!r} should raise"):
                WebsocketConnectionHandler._assert_handshake_validity(headers)

    def test_origin_is_not_a_required_header(self):
        self.assertNotIn(
            "origin", WebsocketConnectionHandler._REQUIRED_HANDSHAKE_HEADERS
        )
        headers = self._valid_headers()
        del headers["origin"]
        WebsocketConnectionHandler._assert_handshake_validity(headers)

    def test_empty_required_header_rejected(self):
        for header in WebsocketConnectionHandler._REQUIRED_HANDSHAKE_HEADERS:
            headers = self._valid_headers()
            headers[header] = ""
            with self.assertRaises(
                (BadRequest, UpgradeRequired), msg=f"Empty {header!r} should raise"
            ):
                WebsocketConnectionHandler._assert_handshake_validity(headers)

    def test_upgrade_required_lists_versions_comma_separated(self):
        headers = dict(UpgradeRequired().get_headers())
        self.assertEqual(
            headers["Sec-WebSocket-Version"],
            ", ".join(sorted(WebsocketConnectionHandler.SUPPORTED_VERSIONS)),
        )
        self.assertNotIn(";", headers["Sec-WebSocket-Version"])

    def test_wrong_upgrade_value(self):
        headers = self._valid_headers()
        headers["upgrade"] = "h2c"
        with self.assertRaises(BadRequest):
            WebsocketConnectionHandler._assert_handshake_validity(headers)

    def test_wrong_connection_value(self):
        headers = self._valid_headers()
        headers["connection"] = "keep-alive"
        with self.assertRaises(BadRequest):
            WebsocketConnectionHandler._assert_handshake_validity(headers)

    def test_unsupported_version(self):
        headers = self._valid_headers()
        headers["sec-websocket-version"] = "8"
        with self.assertRaises(UpgradeRequired):
            WebsocketConnectionHandler._assert_handshake_validity(headers)

    def test_key_not_valid_base64(self):
        headers = self._valid_headers()
        headers["sec-websocket-key"] = "not!valid!base64"
        with self.assertRaises(BadRequest):
            WebsocketConnectionHandler._assert_handshake_validity(headers)

    def test_key_wrong_decoded_length(self):
        headers = self._valid_headers()
        headers["sec-websocket-key"] = base64.b64encode(b"short").decode()
        with self.assertRaises(BadRequest):
            WebsocketConnectionHandler._assert_handshake_validity(headers)

    def test_handshake_response_has_correct_status(self):
        headers = self._valid_headers()
        response = WebsocketConnectionHandler._get_handshake_response(headers)
        self.assertEqual(response.status_code, 101)
        self.assertEqual(response.headers["Upgrade"], "websocket")
        self.assertEqual(response.headers["Connection"], "Upgrade")
        self.assertIn("Sec-WebSocket-Accept", response.headers)


@tagged("-at_install", "post_install")
class TestFrameClasses(BaseCase):
    def test_frame_has_slots(self):
        frame = Frame(Opcode.TEXT, b"hello")
        self.assertFalse(hasattr(frame, "__dict__"))
        self.assertEqual(frame.opcode, Opcode.TEXT)
        self.assertEqual(frame.payload, b"hello")
        self.assertTrue(frame.fin)

    def test_frame_defaults(self):
        frame = Frame(Opcode.PING)
        self.assertEqual(frame.payload, b"")
        self.assertTrue(frame.fin)
        self.assertFalse(frame.rsv1)
        self.assertFalse(frame.rsv2)
        self.assertFalse(frame.rsv3)

    def test_close_frame_valid_code(self):
        frame = CloseFrame(CloseCode.CLEAN, "goodbye")
        self.assertEqual(frame.code, CloseCode.CLEAN)
        self.assertEqual(frame.reason, "goodbye")
        self.assertEqual(frame.opcode, Opcode.CLOSE)
        self.assertEqual(len(frame.payload), 2 + len(b"goodbye"))

    def test_close_frame_no_reason(self):
        frame = CloseFrame(CloseCode.GOING_AWAY, None)
        self.assertEqual(len(frame.payload), 2)

    def test_close_frame_invalid_code(self):
        with self.assertRaises(InvalidCloseCodeError):
            CloseFrame(9999, "bad code")

    def test_close_frame_reserved_code_accepted(self):
        frame = CloseFrame(4001, "custom")
        self.assertEqual(frame.code, 4001)

    def test_close_frame_has_slots(self):
        frame = CloseFrame(CloseCode.CLEAN, None)
        self.assertFalse(hasattr(frame, "__dict__"))

    def test_close_frame_reason_truncated(self):
        frame = CloseFrame(CloseCode.CLEAN, "x" * 500)
        self.assertEqual(len(frame.payload), 2 + CloseFrame.MAX_REASON_LENGTH)
        self.assertEqual(frame.reason, "x" * CloseFrame.MAX_REASON_LENGTH)

    def test_close_frame_reason_truncation_keeps_utf8_valid(self):
        frame = CloseFrame(CloseCode.CLEAN, "é" * 100)
        self.assertLessEqual(len(frame.payload), 125)
        self.assertEqual(frame.reason, "é" * 61)
        frame.payload[2:].decode("utf-8")


@tagged("-at_install", "post_install")
class TestFollowSessionChain(BaseCase):
    def setUp(self):
        super().setUp()
        self.store = MemorySessionStore(Session)
        patcher = patch.object(websocket_module.root, "session_store", self.store)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _stored(self):
        session = self.store.new()
        session["uid"] = None
        self.store.save(session)
        return session

    def test_direct_session_no_chain(self):
        session = self._stored()
        self.assertEqual(_follow_session_chain(session).sid, session.sid)

    def test_soft_rotations_are_followed_to_the_live_successor(self):
        session = self._stored()
        initial_sid = session.sid
        self.store.rotate(session, env=None, soft=True)
        self.store.rotate(session, env=None, soft=True)
        initial = self.store.get(initial_sid)
        self.assertEqual(_follow_session_chain(initial).sid, session.sid)

    def test_missing_session_raises(self):
        with self.assertRaises(SessionExpiredException):
            _follow_session_chain(self.store.new())

    def test_a_revoked_successor_raises(self):
        session = self._stored()
        initial_sid = session.sid
        self.store.rotate(session, env=None, soft=True)
        self.store.delete(session)
        with self.assertRaises(SessionExpiredException):
            _follow_session_chain(self.store.get(initial_sid))

    def test_a_successor_outside_the_family_raises(self):
        session = self._stored()
        stranger = self._stored()
        session["next_sid"] = stranger.sid
        self.store.save(session)
        with self.assertRaises(SessionExpiredException):
            _follow_session_chain(session)


@tagged("-at_install", "post_install")
class TestAcquireCursor(BaseCase):
    def test_succeeds_on_first_try(self):
        mock_cr = MagicMock()
        mock_cm = MagicMock()
        mock_cm.__enter__ = MagicMock(return_value=mock_cr)
        mock_cm.__exit__ = MagicMock(return_value=False)
        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cm

        with (
            patch("odoo.addons.bus.websocket.db_connect", return_value=mock_connection),
            patch("time.sleep"),
        ):
            with acquire_cursor("testdb") as cr:
                self.assertIs(cr, mock_cr)

    def test_retries_on_transient_pool_error(self):
        mock_cr = MagicMock()
        mock_cm = MagicMock()
        mock_cm.__enter__ = MagicMock(return_value=mock_cr)
        mock_cm.__exit__ = MagicMock(return_value=False)

        call_count = 0

        def cursor_side_effect():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise PoolError("pool exhausted")
            return mock_cm

        mock_connection = MagicMock()
        mock_connection.cursor.side_effect = cursor_side_effect

        with (
            patch("odoo.addons.bus.websocket.db_connect", return_value=mock_connection),
            patch("time.sleep"),
        ):
            with acquire_cursor("testdb") as cr:
                self.assertIs(cr, mock_cr)
        self.assertEqual(call_count, 2)

    def test_raises_after_max_retries(self):
        mock_connection = MagicMock()
        mock_connection.cursor.side_effect = PoolError("always busy")

        with (
            patch("odoo.addons.bus.websocket.db_connect", return_value=mock_connection),
            patch("time.sleep"),
        ):
            with self.assertRaises(PoolError):
                with acquire_cursor("testdb"):
                    pass  # pragma: no cover

    def test_no_backoff_sleep_after_final_attempt(self):
        mock_connection = MagicMock()
        mock_connection.cursor.side_effect = PoolError("always busy")

        with (
            patch("odoo.addons.bus.websocket.db_connect", return_value=mock_connection),
            patch("time.sleep") as mock_sleep,
        ):
            with self.assertRaises(PoolError):
                with acquire_cursor("testdb"):
                    pass  # pragma: no cover
        backoff_sleeps = [
            call for call in mock_sleep.call_args_list if call.args[0] > 0
        ]
        self.assertEqual(len(backoff_sleeps), MAX_TRY_ON_POOL_ERROR - 1)

    def test_pool_error_from_body_not_swallowed(self):
        mock_cr = MagicMock()
        mock_cm = MagicMock()
        mock_cm.__enter__ = MagicMock(return_value=mock_cr)
        mock_cm.__exit__ = MagicMock(return_value=False)
        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cm

        with (
            patch("odoo.addons.bus.websocket.db_connect", return_value=mock_connection),
            patch("time.sleep"),
        ):
            with self.assertRaises(PoolError):
                with acquire_cursor("testdb"):
                    raise PoolError("raised by caller body")
        self.assertEqual(mock_connection.cursor.call_count, 1)
        mock_cm.__exit__.assert_called_once()


@tagged("-at_install", "post_install")
class TestNotificationDispatchState(BaseCase):
    def _make_state(self, retention_sec=10, now=100.0):
        clock = _ManualClock(now)
        return NotificationDispatchState(retention_sec, clock=clock), clock

    def test_initialize_last_id_only_adopts_client_value_once(self):
        state, _clock = self._make_state()
        state.initialize_last_id(5)
        self.assertEqual(state.last_id, 5)
        state.initialize_last_id(99)
        self.assertEqual(state.last_id, 5)

    def test_dispatched_ids_are_held_as_ignore_ids(self):
        state, _clock = self._make_state()
        state.record_dispatched([3, 7])
        self.assertEqual(state.last_id, 0)
        self.assertEqual(state.ignore_ids, [3, 7])

    def test_out_of_order_lower_id_is_still_held(self):
        state, clock = self._make_state()
        state.record_dispatched([3, 7])
        clock.now = 101.0
        state.record_dispatched([6])
        self.assertEqual(state.ignore_ids, [3, 6, 7])
        self.assertEqual(state.last_id, 0)

    def test_last_id_advances_past_contiguous_expired_prefix(self):
        state, clock = self._make_state()
        state.record_dispatched([3, 6, 7])
        clock.now = 111.0
        state.record_dispatched([])
        self.assertEqual(state.last_id, 7)
        self.assertEqual(state.ignore_ids, [])

    def test_recent_low_id_blocks_trimming_of_older_higher_id(self):
        state, clock = self._make_state()
        state.record_dispatched([6])
        clock.now = 108.0
        state.record_dispatched([3])
        clock.now = 109.0
        state.record_dispatched([])
        self.assertEqual(state.last_id, 0)
        self.assertEqual(state.ignore_ids, [3, 6])
        clock.now = 200.0
        state.record_dispatched([])
        self.assertEqual(state.last_id, 6)
        self.assertEqual(state.ignore_ids, [])

    def test_history_is_capped(self):
        state, _clock = self._make_state()
        with patch.object(NotificationDispatchState, "MAX_HISTORY_LENGTH", 4):
            state.record_dispatched([1, 2, 3, 4])
            self.assertEqual(state.ignore_ids, [1, 2, 3, 4])
            with self.assertLogs("odoo.addons.bus.websocket", level="DEBUG") as log:
                state.record_dispatched([5, 6])
            self.assertIn("history capped", log.output[0])
            self.assertEqual(state.ignore_ids, [3, 4, 5, 6])
            self.assertEqual(state.last_id, 2)

    def test_cap_does_not_bite_below_limit(self):
        state, clock = self._make_state()
        with patch.object(NotificationDispatchState, "MAX_HISTORY_LENGTH", 4):
            state.record_dispatched([1, 2, 3])
            clock.now = 105.0
            state.record_dispatched([4])
            self.assertEqual(state.ignore_ids, [1, 2, 3, 4])
            self.assertEqual(state.last_id, 0)


@tagged("-at_install", "post_install")
class TestSessionValidityCache(BaseCase):
    def _make_ws(self, clock, session):
        ws = Websocket.__new__(Websocket)
        ws._clock = time.monotonic
        ws._clock = clock
        ws._session = session
        ws._session_validated_until = 0.0
        ws._validated_session_sid = None
        ws._waiting_for_dispatch = True
        ws._channels = set()
        ws._dispatch_state = NotificationDispatchState(10, clock=clock)
        return ws

    @contextmanager
    def _dispatch_env(self, check_session_return=True):
        env = MagicMock()
        env.__getitem__.return_value._poll_batch.return_value = ([], False)

        @contextmanager
        def fake_acquire_cursor(db):
            yield MagicMock()

        with (
            patch(
                "odoo.addons.bus.websocket._follow_session_chain",
                side_effect=lambda session: session,
            ),
            patch(
                "odoo.addons.bus.websocket.is_session_valid",
                return_value=check_session_return,
            ) as check_session_mock,
            patch("odoo.addons.bus.websocket.acquire_cursor", fake_acquire_cursor),
            patch.object(Websocket, "new_env", return_value=env),
        ):
            yield check_session_mock

    def test_cache_expires_after_ttl(self):
        clock = _ManualClock(100.0)
        session = MagicMock(sid="sid-A", uid=1, db="testdb")
        ws = self._make_ws(clock, session)
        with self._dispatch_env() as check_session_mock:
            ws._dispatch_bus_notifications()
            self.assertEqual(check_session_mock.call_count, 1)
            clock.now += Websocket.SESSION_VALIDITY_TTL - 1
            ws._dispatch_bus_notifications()
            self.assertEqual(check_session_mock.call_count, 1)
            clock.now += 1
            ws._dispatch_bus_notifications()
            self.assertEqual(check_session_mock.call_count, 2)

    def test_session_swap_forces_revalidation_before_ttl(self):
        clock = _ManualClock(100.0)
        session = MagicMock(sid="sid-A", uid=1, db="testdb")
        ws = self._make_ws(clock, session)
        with self._dispatch_env() as check_session_mock:
            ws._dispatch_bus_notifications()
            self.assertEqual(check_session_mock.call_count, 1)
            ws._session = MagicMock(sid="sid-B", uid=1, db="testdb")
            ws._dispatch_bus_notifications()
            self.assertEqual(check_session_mock.call_count, 2)

    def test_invalid_session_raises_session_expired(self):
        clock = _ManualClock(100.0)
        session = MagicMock(sid="sid-A", uid=1, db="testdb")
        ws = self._make_ws(clock, session)
        with self._dispatch_env(check_session_return=False):
            with self.assertRaises(SessionExpiredException):
                ws._dispatch_bus_notifications()

    def test_waiting_for_dispatch_reset_even_without_notifications(self):
        clock = _ManualClock(100.0)
        session = MagicMock(sid="sid-A", uid=1, db="testdb")
        ws = self._make_ws(clock, session)
        with self._dispatch_env():
            ws._dispatch_bus_notifications()
        self.assertFalse(ws._waiting_for_dispatch)


@tagged("-at_install", "post_install")
class TestFrameCodec(BaseCase):
    def _make_ws(self, incoming=b""):
        ws = Websocket.__new__(Websocket)
        ws._clock = time.monotonic
        sock = _FakeSocket(incoming)
        ws._Websocket__socket = sock
        ws._timeout_manager = TimeoutManager()
        ws.state = ConnectionState.OPEN
        ws._close_sent = False
        ws._close_received = False
        ws._limit_rate = lambda opcode: None
        return ws, sock

    def test_single_text_frame(self):
        ws, _ = self._make_ws(_client_frame(Opcode.TEXT, b"hello"))
        self.assertEqual(ws._process_next_message(), "hello")

    def test_fragmented_text_message_is_reassembled(self):
        data = _client_frame(Opcode.TEXT, b"Hello ", fin=False) + _client_frame(
            Opcode.CONTINUE, b"World", fin=True
        )
        ws, _ = self._make_ws(data)
        self.assertEqual(ws._process_next_message(), "Hello World")

    def test_control_frame_interleaved_in_fragmented_message(self):
        data = (
            _client_frame(Opcode.TEXT, b"Hello ", fin=False)
            + _client_frame(Opcode.PING, b"ka", fin=True)
            + _client_frame(Opcode.CONTINUE, b"World", fin=True)
        )
        ws, sock = self._make_ws(data)
        self.assertEqual(ws._process_next_message(), "Hello World")
        self.assertTrue(sock.sent)
        self.assertEqual(sock.sent[0] & 0x0F, int(Opcode.PONG))

    def test_reserved_bit_set_raises(self):
        ws, _ = self._make_ws(_client_frame(Opcode.TEXT, b"x", rsv1=True))
        with self.assertRaises(ProtocolError):
            ws._process_next_message()

    def test_unmasked_client_frame_raises(self):
        ws, _ = self._make_ws(_client_frame(Opcode.TEXT, b"x", masked=False))
        with self.assertRaises(ProtocolError):
            ws._process_next_message()

    def test_invalid_opcode_raises(self):
        frame = bytes([0x80 | 0x03, 0x80, 0, 0, 0, 0])
        ws, _ = self._make_ws(frame)
        with self.assertRaises(ProtocolError):
            ws._process_next_message()

    def test_oversized_control_frame_raises(self):
        ws, _ = self._make_ws(_client_frame(Opcode.CLOSE, b"", seven_bit_len=126))
        with self.assertRaises(ProtocolError):
            ws._process_next_message()

    def test_fragmented_control_frame_raises(self):
        ws, _ = self._make_ws(_client_frame(Opcode.PING, b"x", fin=False))
        with self.assertRaises(ProtocolError):
            ws._process_next_message()

    def test_payload_too_large_single_frame_raises(self):
        frame = (
            bytes([0x80 | int(Opcode.TEXT), 0x80 | 127])
            + struct.pack("!Q", Websocket.MESSAGE_MAX_SIZE + 1)
            + b"\x00\x00\x00\x00"
        )
        ws, _ = self._make_ws(frame)
        with self.assertRaises(PayloadTooLargeError):
            ws._process_next_message()

    def test_unexpected_top_level_continuation_raises(self):
        ws, _ = self._make_ws(_client_frame(Opcode.CONTINUE, b"x", fin=True))
        with self.assertRaises(ProtocolError):
            ws._process_next_message()

    def test_data_frame_where_continuation_expected_raises(self):
        data = _client_frame(Opcode.TEXT, b"a", fin=False) + _client_frame(
            Opcode.TEXT, b"b", fin=True
        )
        ws, _ = self._make_ws(data)
        with self.assertRaises(ProtocolError):
            ws._process_next_message()

    def test_payload_too_large_during_reassembly_raises(self):
        ws, _ = self._make_ws(
            _client_frame(Opcode.TEXT, b"12345", fin=False)
            + _client_frame(Opcode.CONTINUE, b"67890", fin=True)
        )
        ws.MESSAGE_MAX_SIZE = 8
        with self.assertRaises(PayloadTooLargeError):
            ws._process_next_message()

    def test_stalled_frame_is_abandoned_at_the_deadline(self):
        header = struct.pack("!BBH", 0x81, 0x80 | 126, 1000) + b"\x00\x00\x00\x00"
        sock = _StallingSocket(header)
        clock = _ManualClock()
        ws = Websocket.__new__(Websocket)
        ws._clock = clock
        ws._Websocket__socket = sock
        ws._timeout_manager = TimeoutManager(clock=clock)
        ws.state = ConnectionState.OPEN
        ws._limit_rate = lambda opcode: None

        original_recv = sock.recv

        def ticking_recv(n):
            clock.now += 1
            return original_recv(n)

        sock.recv = ticking_recv

        with self.assertRaises(ConnectionClosedError):
            ws._get_next_frame()
        self.assertLess(sock.recv_calls, 1000)
        self.assertGreaterEqual(clock.now, Websocket.FRAME_RECEIVE_TIMEOUT)

    def test_frame_deadline_does_not_disturb_a_prompt_peer(self):
        clock = _ManualClock()
        ws, _ = self._make_ws(_client_frame(Opcode.TEXT, b"hello"))
        ws._clock = clock
        self.assertEqual(ws._process_next_message(), "hello")

    def test_truncated_frame_raises_connection_closed(self):
        truncated = _client_frame(Opcode.TEXT, b"hello")[:-3]
        ws, _ = self._make_ws(truncated)
        with self.assertRaises(ConnectionClosedError):
            ws._process_next_message()

    def test_close_interleaved_in_fragmented_message_abandons_message(self):
        data = _client_frame(Opcode.TEXT, b"Hello ", fin=False) + _client_frame(
            Opcode.CLOSE, struct.pack("!H", CloseCode.CLEAN)
        )
        ws, sock = self._make_ws(data)
        ws._terminate = MagicMock()
        self.assertIsNone(ws._process_next_message())
        opcode, payload = _parse_server_frame(sock.sent)
        self.assertEqual(opcode, Opcode.CLOSE)
        self.assertEqual(struct.unpack("!H", payload[:2])[0], CloseCode.CLEAN)
        ws._terminate.assert_called_once()

    def test_data_frame_received_while_closing_is_discarded(self):
        ws, _ = self._make_ws(_client_frame(Opcode.TEXT, b"late data"))
        ws.state = ConnectionState.CLOSING
        self.assertIsNone(ws._process_next_message())


def _parse_server_frame(data):
    first_byte, second_byte = data[0], data[1]
    opcode = Opcode(first_byte & 0x0F)
    length = second_byte & 0x7F
    offset = 2
    if length == 126:
        length = struct.unpack("!H", data[2:4])[0]
        offset = 4
    elif length == 127:
        length = struct.unpack("!Q", data[2:10])[0]
        offset = 10
    return opcode, bytes(data[offset : offset + length])


@tagged("-at_install", "post_install")
class TestCloseFrameHandling(BaseCase):
    def _make_ws(self, incoming=b""):
        ws = Websocket.__new__(Websocket)
        ws._clock = time.monotonic
        sock = _FakeSocket(incoming)
        ws._Websocket__socket = sock
        ws._timeout_manager = TimeoutManager()
        ws.state = ConnectionState.OPEN
        ws._close_sent = False
        ws._close_received = False
        ws._limit_rate = lambda opcode: None
        ws._terminate = MagicMock()
        return ws, sock

    def _assert_close_answer(self, sock, expected_code, expected_reason=None):
        opcode, payload = _parse_server_frame(sock.sent)
        self.assertEqual(opcode, Opcode.CLOSE)
        self.assertEqual(struct.unpack("!H", payload[:2])[0], expected_code)
        if expected_reason is not None:
            self.assertEqual(payload[2:].decode(), expected_reason)

    def test_legal_close_is_echoed(self):
        payload = struct.pack("!H", CloseCode.CLEAN) + b"bye"
        ws, sock = self._make_ws(_client_frame(Opcode.CLOSE, payload))
        ws._process_next_message()
        self._assert_close_answer(sock, CloseCode.CLEAN, "bye")
        ws._terminate.assert_called_once()

    def test_reserved_range_close_code_is_echoed(self):
        payload = struct.pack("!H", 4242)
        ws, sock = self._make_ws(_client_frame(Opcode.CLOSE, payload))
        ws._process_next_message()
        self._assert_close_answer(sock, 4242)

    def test_invalid_close_code_answered_with_protocol_error(self):
        for bad_code in (999, 1005, 1006, 1015, 2999):
            ws, sock = self._make_ws(
                _client_frame(Opcode.CLOSE, struct.pack("!H", bad_code))
            )
            ws._process_next_message()
            self._assert_close_answer(sock, CloseCode.PROTOCOL_ERROR)
            ws._terminate.assert_called_once()

    def test_one_byte_close_payload_answered_with_protocol_error(self):
        ws, sock = self._make_ws(_client_frame(Opcode.CLOSE, b"\x01"))
        ws._process_next_message()
        self._assert_close_answer(sock, CloseCode.PROTOCOL_ERROR)

    def test_invalid_utf8_close_reason_answered_with_inconsistent_data(self):
        payload = struct.pack("!H", CloseCode.CLEAN) + b"\xff\xfe"
        ws, sock = self._make_ws(_client_frame(Opcode.CLOSE, payload))
        ws._process_next_message()
        self._assert_close_answer(sock, CloseCode.INCONSISTENT_DATA)

    def test_empty_close_payload_answered_with_clean(self):
        ws, sock = self._make_ws(_client_frame(Opcode.CLOSE))
        ws._process_next_message()
        self._assert_close_answer(sock, CloseCode.CLEAN)


@tagged("-at_install", "post_install")
class TestOpenConnection(BaseCase):
    def test_service_unavailable_when_websocket_disabled(self):
        request = MagicMock()
        with patch.object(
            WebsocketConnectionHandler, "websocket_allowed", return_value=False
        ):
            with self.assertRaises(ServiceUnavailable):
                WebsocketConnectionHandler.open_connection(request, "19.0-5")

    def test_public_configuration_runs_after_handshake_validation(self):
        request = MagicMock()
        with (
            patch.object(
                WebsocketConnectionHandler, "websocket_allowed", return_value=True
            ),
            patch.object(
                WebsocketConnectionHandler,
                "_get_handshake_response",
                side_effect=BadRequest("bad handshake"),
            ),
            patch.object(
                WebsocketConnectionHandler, "_handle_public_configuration"
            ) as public_config_mock,
        ):
            with self.assertRaises(BadRequest):
                WebsocketConnectionHandler.open_connection(request, "19.0-5")
        public_config_mock.assert_not_called()


@tagged("-at_install", "post_install")
class TestTrustedOrigin(BaseCase):
    def _request(self, scheme, host):
        request = MagicMock()
        request.httprequest.scheme = scheme
        request.httprequest.host = host
        return request

    def test_matching_origin_is_trusted(self):
        request = self._request("http", "example.com:8069")
        self.assertTrue(
            WebsocketConnectionHandler._is_trusted_origin(
                "http://example.com:8069", request
            )
        )

    def test_default_port_is_normalized(self):
        request = self._request("https", "example.com")
        self.assertTrue(
            WebsocketConnectionHandler._is_trusted_origin(
                "https://example.com:443", request
            )
        )

    def test_mismatched_origin_is_not_trusted(self):
        request = self._request("http", "example.com:8069")
        self.assertFalse(
            WebsocketConnectionHandler._is_trusted_origin(
                "http://attacker.example.com", request
            )
        )

    def test_scheme_mismatch_is_not_trusted(self):
        request = self._request("https", "example.com")
        self.assertFalse(
            WebsocketConnectionHandler._is_trusted_origin("http://example.com", request)
        )

    def test_allowlisted_origin_is_trusted(self):
        request = self._request("http", "example.com:8069")
        with patch.dict(
            os.environ,
            {"ODOO_BUS_TRUSTED_ORIGINS": "https://cdn.example.com, http://x.test:9000"},
        ):
            self.assertTrue(
                WebsocketConnectionHandler._is_trusted_origin(
                    "http://x.test:9000", request
                )
            )
            self.assertFalse(
                WebsocketConnectionHandler._is_trusted_origin(
                    "http://not-listed.test", request
                )
            )


@tagged("-at_install", "post_install")
class TestControlCommandPriority(BaseCase):
    def test_queued_close_beats_pending_dispatch(self):
        queue = PollablePriorityQueue()
        try:
            queue.put((ControlCommand.DISPATCH, 1, None))
            queue.put((ControlCommand.CLOSE, 2, {"code": CloseCode.CLEAN}))
            command, _, data = queue.get()
            self.assertIs(command, ControlCommand.CLOSE)
            self.assertEqual(data["code"], CloseCode.CLEAN)
            command, _, _data = queue.get()
            self.assertIs(command, ControlCommand.DISPATCH)
        finally:
            queue.close()


@tagged("post_install", "-at_install")
class TestCloseCodesOverWire(WebsocketCase):
    def test_invalid_utf8_text_frame_closes_1007(self):
        ws = self.websocket_connect()
        ws.send(b"\xff\xfe\xfd", opcode=ABNF.OPCODE_TEXT)
        self.assert_close_with_code(ws, CloseCode.INCONSISTENT_DATA)

    def test_oversized_frame_closes_1009(self):
        self.startPatcher(patch.object(Websocket, "MESSAGE_MAX_SIZE", 1024))
        ws = self.websocket_connect()
        ws.send("x" * 2048)
        self.assert_close_with_code(ws, CloseCode.MESSAGE_TOO_BIG)

    def test_protocol_violation_closes_1002(self):
        ws = self.websocket_connect()
        ws.sock.sendall(_client_frame(Opcode.TEXT, b"x", rsv1=True))
        self.assert_close_with_code(ws, CloseCode.PROTOCOL_ERROR)

    def test_invalid_close_code_answered_with_1002(self):
        ws = self.websocket_connect()
        ws.sock.sendall(_client_frame(Opcode.CLOSE, struct.pack("!H", 999)))
        self.assert_close_with_code(ws, CloseCode.PROTOCOL_ERROR, "Invalid close code")

    def test_one_byte_close_payload_answered_with_1002(self):
        ws = self.websocket_connect()
        ws.sock.sendall(_client_frame(Opcode.CLOSE, b"\x01"))
        self.assert_close_with_code(
            ws, CloseCode.PROTOCOL_ERROR, "Malformed closing frame"
        )

    def test_legal_close_code_and_reason_echoed(self):
        ws = self.websocket_connect()
        ws.sock.sendall(
            _client_frame(Opcode.CLOSE, struct.pack("!H", CloseCode.CLEAN) + b"bye")
        )
        self.assert_close_with_code(ws, CloseCode.CLEAN, "bye")

    def test_malformed_envelope_keeps_connection_alive(self):
        self.startPatcher(patch.object(Websocket, "RL_BURST", 100))
        ws = self.websocket_connect()
        for message in ("not-json{", json.dumps(["top-level-list"]), json.dumps({})):
            with self.assertLogs(
                "odoo.addons.bus.websocket", level="WARNING"
            ) as capture:
                ws.send(message)
                ws.ping()
                ws.recv_data_frame(control_frame=True)
            self.assertTrue(
                any("Invalid websocket request" in line for line in capture.output),
                f"message {message!r} should be rejected with a warning",
            )
        ws.ping()
        opcode, _ = ws.recv_data_frame(control_frame=True)
        self.assertEqual(opcode, ABNF.OPCODE_PONG)

    def test_kill_now_terminates_without_close_handshake(self):
        ws = self.websocket_connect()
        server_ws = next(
            websocket
            for websocket in list(websocket_module._websocket_instances)
            if websocket.state is ConnectionState.OPEN
        )
        server_ws.close(CloseCode.KILL_NOW)
        with self.assertRaises(WebSocketConnectionClosedException):
            ws.recv_data_frame(control_frame=True)

    def test_kick_all_sends_going_away(self):
        ws = self.websocket_connect()
        websocket_module._kick_all()
        self.assert_close_with_code(ws, CloseCode.GOING_AWAY)

    def test_server_pings_after_inactivity_timeout(self):
        self.startPatcher(patch.object(TimeoutManager, "INACTIVITY_TIMEOUT", 0))
        self.startPatcher(patch.object(TimeoutManager, "TIMEOUT", 0.2))
        ws = self.websocket_connect(ping_after_connect=False)
        opcode, _ = ws.recv_data_frame(control_frame=True)
        self.assertEqual(opcode, ABNF.OPCODE_PING)
