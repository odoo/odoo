import base64
import bisect
import functools
import hashlib
import logging
import os
import random
import selectors
import socket
import struct
import sys
import threading
import time
from collections import defaultdict, deque
from contextlib import contextmanager, suppress
from enum import IntEnum
from itertools import count
from queue import PriorityQueue
from urllib.parse import urlparse
from weakref import WeakSet

import psycopg
from werkzeug.datastructures import ImmutableMultiDict, MultiDict
from werkzeug.exceptions import BadRequest, HTTPException, ServiceUnavailable
from werkzeug.local import LocalStack

from odoo import api, modules
from odoo.db import PoolError, db_connect
from odoo.exceptions import AccessDenied
from odoo.http import (
    Request,
    Response,
    SessionExpiredException,
    prepare_default_session,
    root,
)
from odoo.modules.registry import Registry
from odoo.service.security import is_session_valid
from odoo.service.server import CommonServer
from odoo.service.transaction import retrying
from odoo.tools import config

from .models.bus import NOTIFICATION_HOLD_BACK_SECONDS, dispatch
from .tools import orjson

_logger = logging.getLogger(__name__)


MAX_TRY_ON_POOL_ERROR = 10
DELAY_ON_POOL_ERROR = 0.15
JITTER_ON_POOL_ERROR = 0.3


@contextmanager
def acquire_cursor(db):
    delay = DELAY_ON_POOL_ERROR
    for attempt in range(1, MAX_TRY_ON_POOL_ERROR + 1):
        try:
            cm = db_connect(db).cursor()
            cr = cm.__enter__()
        except PoolError:
            if attempt == MAX_TRY_ON_POOL_ERROR:
                raise PoolError(
                    f"Failed to acquire cursor after {MAX_TRY_ON_POOL_ERROR} retries"
                ) from None
        else:
            try:
                yield cr
                return
            finally:
                cm.__exit__(*sys.exc_info())
        time.sleep(delay + random.uniform(0, JITTER_ON_POOL_ERROR))
        delay *= 1.5


class UpgradeRequired(HTTPException):
    code = 426
    description = "Wrong websocket version was given during the handshake"

    def get_headers(self, environ=None):
        headers = super().get_headers(environ)
        headers.append(
            (
                "Sec-WebSocket-Version",
                ", ".join(sorted(WebsocketConnectionHandler.SUPPORTED_VERSIONS)),
            )
        )
        return headers


class WebsocketError(Exception):
    pass


class ConnectionClosedError(WebsocketError):
    pass


class InvalidCloseCodeError(WebsocketError):
    def __init__(self, code):
        super().__init__(f"Invalid close code: {code}")


class InvalidDatabaseError(WebsocketError):
    pass


class InvalidStateError(WebsocketError):
    pass


class InvalidWebsocketRequestError(WebsocketError):
    pass


class PayloadTooLargeError(WebsocketError):
    pass


class ProtocolError(WebsocketError):
    pass


class RateLimitExceededError(Exception):
    pass


class PollablePriorityQueue(PriorityQueue):
    def __init__(self, maxsize=0):
        super().__init__(maxsize)
        self._putsocket, self._getsocket = socket.socketpair()

    def fileno(self):
        return self._getsocket.fileno()

    def put(self, item, *args, **kwargs):
        super().put(item, *args, **kwargs)
        self._putsocket.send(b".")

    def get(self, *args, **kwargs):
        self._getsocket.recv(1)
        return super().get(*args, **kwargs)

    def close(self):
        self._putsocket.close()
        self._getsocket.close()


class LifecycleEvent(IntEnum):
    OPEN = 0
    CLOSE = 1


class Opcode(IntEnum):
    CONTINUE = 0x00
    TEXT = 0x01
    BINARY = 0x02
    CLOSE = 0x08
    PING = 0x09
    PONG = 0x0A


class CloseCode(IntEnum):
    CLEAN = 1000
    GOING_AWAY = 1001
    PROTOCOL_ERROR = 1002
    INCORRECT_DATA = 1003
    ABNORMAL_CLOSURE = 1006
    INCONSISTENT_DATA = 1007
    MESSAGE_VIOLATING_POLICY = 1008
    MESSAGE_TOO_BIG = 1009
    EXTENSION_NEGOTIATION_FAILED = 1010
    SERVER_ERROR = 1011
    RESTART = 1012
    TRY_LATER = 1013
    BAD_GATEWAY = 1014
    SESSION_EXPIRED = 4001
    KEEP_ALIVE_TIMEOUT = 4002
    KILL_NOW = 4003


class ConnectionState(IntEnum):
    OPEN = 0
    CLOSING = 1
    CLOSED = 2


_command_uid = count(0)


class ControlCommand(IntEnum):
    CLOSE = 0
    DISPATCH = 1


DATA_OP = {Opcode.TEXT, Opcode.BINARY}
CTRL_OP = {Opcode.CLOSE, Opcode.PING, Opcode.PONG}
HEARTBEAT_OP = {Opcode.PING, Opcode.PONG}

VALID_CLOSE_CODES = {
    code for code in CloseCode if code is not CloseCode.ABNORMAL_CLOSURE
}
RESERVED_CLOSE_CODES = range(3000, 5000)

_XOR_TABLE = [bytes(a ^ b for a in range(256)) for b in range(256)]


class Frame:
    __slots__ = ("fin", "opcode", "payload", "rsv1", "rsv2", "rsv3")

    def __init__(
        self, opcode, payload=b"", fin=True, rsv1=False, rsv2=False, rsv3=False
    ):
        self.opcode = opcode
        self.payload = payload
        self.fin = fin
        self.rsv1 = rsv1
        self.rsv2 = rsv2
        self.rsv3 = rsv3


class CloseFrame(Frame):
    __slots__ = ("code", "reason")

    MAX_REASON_LENGTH = 123

    def __init__(self, code, reason):
        if code not in VALID_CLOSE_CODES and code not in RESERVED_CLOSE_CODES:
            raise InvalidCloseCodeError(code)
        payload = struct.pack("!H", code)
        if reason:
            encoded_reason = reason.encode("utf-8")
            if len(encoded_reason) > self.MAX_REASON_LENGTH:
                reason = encoded_reason[: self.MAX_REASON_LENGTH].decode(
                    "utf-8", errors="ignore"
                )
                encoded_reason = reason.encode("utf-8")
            payload += encoded_reason
        self.code = code
        self.reason = reason
        super().__init__(Opcode.CLOSE, payload)


_public_session_lock = threading.Lock()
_public_session_sid_by_db = {}


_websocket_instances = WeakSet()
_websocket_instances_lock = threading.Lock()


class NotificationDispatchState:
    __slots__ = ("_clock", "_history", "_retention_sec", "last_id")

    MAX_HISTORY_LENGTH = 5000

    def __init__(self, retention_sec, clock=None):
        self._clock = clock if clock is not None else time.monotonic
        self._retention_sec = retention_sec
        self.last_id = 0
        self._history = []

    @property
    def ignore_ids(self):
        return [nid for nid, _sent_at in self._history]

    def initialize_last_id(self, last):
        if self.last_id == 0:
            self.last_id = last

    def record_dispatched(self, notif_ids):
        now = self._clock()
        for nid in notif_ids:
            bisect.insort(self._history, (nid, now), key=lambda entry: entry[0])
        last_index = -1
        for i, (_nid, sent_at) in enumerate(self._history):
            if now - sent_at > self._retention_sec:
                last_index = i
            else:
                break
        if last_index != -1:
            self.last_id = self._history[last_index][0]
            self._history = self._history[last_index + 1 :]
        overflow = len(self._history) - self.MAX_HISTORY_LENGTH
        if overflow > 0:
            self.last_id = self._history[overflow - 1][0]
            del self._history[:overflow]
            _logger.debug(
                "Notification dispatch history capped: dropped %s ids still "
                "within the retention window",
                overflow,
            )


class Websocket:
    __event_callbacks = defaultdict(set)
    MESSAGE_MAX_SIZE = 2**20
    MAX_NOTIFICATION_HISTORY_SEC = NOTIFICATION_HOLD_BACK_SECONDS
    RL_BURST = max(1, int(config["websocket_rate_limit_burst"]))
    RL_DELAY = float(config["websocket_rate_limit_delay"])
    RL_CONTROL_FACTOR = 10
    SESSION_VALIDITY_TTL = 60
    FRAME_RECEIVE_TIMEOUT = 15

    # The dispatch round a batched wake authorised this connection to share an
    # answer in, None otherwise. Declared on the class so a connection that
    # never went through a wake reads None rather than raising.
    _poll_round = None

    def __init__(self, sock, session, cookies, *, clock=None):
        self._clock = clock if clock is not None else time.monotonic
        self._session = session
        self._cookies = cookies
        self._db = session.db
        self.__socket = sock
        sock.settimeout(self.FRAME_RECEIVE_TIMEOUT)
        self._close_sent = False
        self._close_received = False
        self._timeout_manager = TimeoutManager(clock=self._clock)
        self._incoming_frame_timestamps = deque(maxlen=self.RL_BURST)
        self._incoming_control_frame_timestamps = deque(
            maxlen=self.RL_BURST * self.RL_CONTROL_FACTOR
        )
        self.__cmd_queue = PollablePriorityQueue()
        self._waiting_for_dispatch = False
        self._channels = set()
        self._session_validated_until = 0.0
        self._validated_session_sid = None
        self._dispatch_state = NotificationDispatchState(
            self.MAX_NOTIFICATION_HISTORY_SEC
        )
        self.__selector = selectors.DefaultSelector()
        self.__selector.register(self.__socket, selectors.EVENT_READ)
        self.__selector.register(self.__cmd_queue, selectors.EVENT_READ)
        self.state = ConnectionState.OPEN
        with _websocket_instances_lock:
            _websocket_instances.add(self)
        self._trigger_lifecycle_event(LifecycleEvent.OPEN)

    def get_messages(self):
        while self.state is not ConnectionState.CLOSED:
            try:
                readables = {
                    selector_key[0].fileobj
                    for selector_key in self.__selector.select(TimeoutManager.TIMEOUT)
                }
                if (
                    self._timeout_manager.has_keep_alive_timed_out()
                    and self.state is ConnectionState.OPEN
                ):
                    self._disconnect(CloseCode.KEEP_ALIVE_TIMEOUT)
                    continue
                if self._timeout_manager.has_frame_response_timed_out():
                    self._terminate()
                    continue
                if not readables and self._timeout_manager.is_ping_frame_required():
                    self._send_ping_frame()
                    continue
                if self.__cmd_queue in readables:
                    cmd, _, data = self.__cmd_queue.get_nowait()
                    self._process_control_command(cmd, data)
                    if self.state is ConnectionState.CLOSED:
                        continue
                if self.__socket in readables:
                    message = self._process_next_message()
                    if message is not None:
                        yield message
            except Exception as exc:
                self._handle_transport_error(exc)

    def close(self, code, reason=None):
        with suppress(OSError):
            self._send_control_command(
                ControlCommand.CLOSE, {"code": code, "reason": reason}
            )

    @classmethod
    def onopen(cls, func):
        cls.__event_callbacks[LifecycleEvent.OPEN].add(func)
        return func

    @classmethod
    def onclose(cls, func):
        cls.__event_callbacks[LifecycleEvent.CLOSE].add(func)
        return func

    def subscribe(self, channels, last):
        self._channels = channels
        self._session_validated_until = 0.0
        self._dispatch_state.initialize_last_id(last)
        self.trigger_notification_dispatching()

    def trigger_notification_dispatching(self, poll_round=None):
        if self.state is not ConnectionState.OPEN or self._waiting_for_dispatch:
            return
        self._waiting_for_dispatch = True
        # Only a caller that woke a BATCH passes a round, and only that round
        # lets this connection share another's answer. A lone trigger -- a
        # re-arm, a test, anything outside the dispatcher -- shares nothing.
        self._poll_round = poll_round
        with suppress(OSError):
            self._send_control_command(ControlCommand.DISPATCH)

    def _get_next_frame(self):
        frame_deadline = self._clock() + self.FRAME_RECEIVE_TIMEOUT

        def recv_bytes(n):
            data = bytearray()
            while len(data) < n:
                if self._clock() > frame_deadline:
                    raise ConnectionClosedError(
                        "Peer did not complete the frame within "
                        f"{self.FRAME_RECEIVE_TIMEOUT}s"
                    )
                received_data = self.__socket.recv(n - len(data))
                if not received_data:
                    raise ConnectionClosedError
                data.extend(received_data)
            return data

        def is_bit_set(byte, n):
            return byte & (1 << (7 - n))

        def apply_mask(payload, mask):
            a, b, c, d = (_XOR_TABLE[n] for n in mask)
            payload[::4] = payload[::4].translate(a)
            payload[1::4] = payload[1::4].translate(b)
            payload[2::4] = payload[2::4].translate(c)
            payload[3::4] = payload[3::4].translate(d)
            return payload

        first_byte, second_byte = recv_bytes(2)
        fin, rsv1, rsv2, rsv3 = (is_bit_set(first_byte, n) for n in range(4))
        try:
            opcode = Opcode(first_byte & 0b00001111)
        except ValueError as exc:
            raise ProtocolError(exc) from exc
        self._limit_rate(opcode)
        payload_length = second_byte & 0b01111111

        if rsv1 or rsv2 or rsv3:
            raise ProtocolError("Reserved bits must be unset")
        if not is_bit_set(second_byte, 0):
            raise ProtocolError("Frame must be masked")
        if opcode in CTRL_OP:
            if not fin:
                raise ProtocolError("Control frames cannot be fragmented")
            if payload_length > 125:
                raise ProtocolError("Control frames payload must be smaller than 126")
        if payload_length == 126:
            payload_length = struct.unpack("!H", recv_bytes(2))[0]
        elif payload_length == 127:
            payload_length = struct.unpack("!Q", recv_bytes(8))[0]
        if payload_length > self.MESSAGE_MAX_SIZE:
            raise PayloadTooLargeError

        mask = recv_bytes(4)
        payload = apply_mask(recv_bytes(payload_length), mask)
        frame = Frame(opcode, bytes(payload), fin, rsv1, rsv2, rsv3)
        self._timeout_manager.acknowledge_frame_receipt(frame)
        return frame

    def _process_next_message(self):
        frame = self._get_next_frame()
        if frame.opcode in CTRL_OP:
            self._handle_control_frame(frame)
            return None
        if self.state is not ConnectionState.OPEN:
            return None
        if frame.opcode is Opcode.CONTINUE:
            raise ProtocolError("Unexpected continuation frame")
        message = frame.payload
        if not frame.fin:
            message = self._recover_fragmented_message(frame)
        return (
            message.decode("utf-8")
            if message is not None and frame.opcode is Opcode.TEXT
            else message
        )

    def _recover_fragmented_message(self, initial_frame):
        message_fragments = bytearray(initial_frame.payload)
        while True:
            frame = self._get_next_frame()
            if frame.opcode in CTRL_OP:
                self._handle_control_frame(frame)
                if self.state is not ConnectionState.OPEN:
                    return None
                continue
            if frame.opcode is not Opcode.CONTINUE:
                raise ProtocolError("A continuation frame was expected")
            message_fragments.extend(frame.payload)
            if len(message_fragments) > self.MESSAGE_MAX_SIZE:
                raise PayloadTooLargeError
            if frame.fin:
                return bytes(message_fragments)

    def _send(self, message):
        if self.state is not ConnectionState.OPEN:
            raise InvalidStateError("Trying to send a frame on a closed socket")
        opcode = Opcode.BINARY
        if not isinstance(message, (bytes, bytearray)):
            opcode = Opcode.TEXT
        self._send_frame(Frame(opcode, message))

    def _send_frame(self, frame):
        if frame.opcode in CTRL_OP and len(frame.payload) > 125:
            raise ProtocolError(
                "Control frames should have a payload length smaller than 126"
            )
        if isinstance(frame.payload, str):
            frame.payload = frame.payload.encode("utf-8")
        elif not isinstance(frame.payload, (bytes, bytearray)):
            frame.payload = orjson.dumps(frame.payload)

        output = bytearray()
        first_byte = (
            (0b10000000 if frame.fin else 0)
            | (0b01000000 if frame.rsv1 else 0)
            | (0b00100000 if frame.rsv2 else 0)
            | (0b00010000 if frame.rsv3 else 0)
            | frame.opcode
        )
        payload_length = len(frame.payload)
        if payload_length < 126:
            output.extend(struct.pack("!BB", first_byte, payload_length))
        elif payload_length < 65536:
            output.extend(struct.pack("!BBH", first_byte, 126, payload_length))
        else:
            output.extend(struct.pack("!BBQ", first_byte, 127, payload_length))
        output.extend(frame.payload)
        self.__socket.sendall(output)
        self._timeout_manager.acknowledge_frame_sent(frame)
        if not isinstance(frame, CloseFrame):
            return
        self.state = ConnectionState.CLOSING
        self._close_sent = True
        if (
            frame.code in (CloseCode.ABNORMAL_CLOSURE, CloseCode.KILL_NOW)
            or self._close_received
        ):
            self._terminate()
            return
        self.__selector.unregister(self.__cmd_queue)

    def _send_close_frame(self, code, reason=None):
        self._send_frame(CloseFrame(code, reason))

    def _send_ping_frame(self):
        self._send_frame(Frame(Opcode.PING))

    def _send_pong_frame(self, payload):
        self._send_frame(Frame(Opcode.PONG, payload))

    def _disconnect(self, code, reason=None):
        if code in (CloseCode.ABNORMAL_CLOSURE, CloseCode.KILL_NOW):
            self._terminate()
        else:
            self._send_close_frame(code, reason)

    def _terminate(self):
        if self.state == ConnectionState.CLOSED:
            return
        self.state = ConnectionState.CLOSED
        dispatch.unsubscribe(self)
        with suppress(OSError, TimeoutError):
            self.__socket.shutdown(socket.SHUT_WR)
            self.__socket.settimeout(1)
            drain_deadline = self._clock() + 5
            while self.__socket.recv(4096):
                if self._clock() > drain_deadline:
                    break
        with suppress(KeyError):
            self.__selector.unregister(self.__socket)
        with suppress(OSError):
            self.__selector.close()
        with suppress(OSError):
            self.__socket.close()
        with suppress(OSError):
            self.__cmd_queue.close()
        try:
            self._trigger_lifecycle_event(LifecycleEvent.CLOSE)
            with acquire_cursor(self._db) as cr:
                env = self.new_env(cr, self._session)
                retrying(
                    functools.partial(
                        env["ir.websocket"]._on_websocket_closed, self._cookies
                    ),
                    env,
                )
        except Exception:
            _logger.warning("Error during websocket teardown cleanup", exc_info=True)

    def _handle_control_frame(self, frame):
        if frame.opcode is Opcode.PING:
            self._send_pong_frame(frame.payload)
        elif frame.opcode is Opcode.CLOSE:
            self.state = ConnectionState.CLOSING
            self._close_received = True
            code, reason = CloseCode.CLEAN, None
            if len(frame.payload) >= 2:
                code = struct.unpack("!H", frame.payload[:2])[0]
                if code not in VALID_CLOSE_CODES and code not in RESERVED_CLOSE_CODES:
                    code, reason = CloseCode.PROTOCOL_ERROR, "Invalid close code"
                else:
                    try:
                        reason = frame.payload[2:].decode("utf-8")
                    except UnicodeDecodeError:
                        code = CloseCode.INCONSISTENT_DATA
                        reason = "Malformed close reason"
            elif frame.payload:
                code, reason = CloseCode.PROTOCOL_ERROR, "Malformed closing frame"
            if not self._close_sent:
                self._send_close_frame(code, reason)
            else:
                self._terminate()

    def _handle_transport_error(self, exc):
        code, reason = CloseCode.SERVER_ERROR, str(exc)
        if isinstance(exc, (ConnectionClosedError, OSError)):
            code = CloseCode.ABNORMAL_CLOSURE
            if isinstance(exc, TimeoutError):
                _logger.warning(
                    "Websocket timed out after %ss mid-frame; the peer is too "
                    "slow for the frame being written and will reconnect. "
                    "Channels: %.200s",
                    self.FRAME_RECEIVE_TIMEOUT,
                    self._channels,
                )
        elif isinstance(exc, (ProtocolError, InvalidCloseCodeError)):
            code = CloseCode.PROTOCOL_ERROR
        elif isinstance(exc, UnicodeDecodeError):
            code = CloseCode.INCONSISTENT_DATA
        elif isinstance(exc, PayloadTooLargeError):
            code = CloseCode.MESSAGE_TOO_BIG
        elif isinstance(exc, (PoolError, RateLimitExceededError)):
            code = CloseCode.TRY_LATER
        elif isinstance(exc, SessionExpiredException):
            code = CloseCode.SESSION_EXPIRED
        if code is CloseCode.SERVER_ERROR:
            reason = None
            try:
                registry = Registry(self._session.db)
                sequence = registry.registry_sequence
                registry = registry.check_signaling()
                registry_reloaded = sequence != registry.registry_sequence
            except Exception:
                registry_reloaded = False
            if registry_reloaded:
                _logger.warning("Bus operation aborted; registry has been reloaded")
            else:
                _logger.error("Unhandled exception in websocket handler", exc_info=exc)
        if self.state is ConnectionState.OPEN:
            try:
                self._disconnect(code, reason)
            except Exception:
                _logger.debug("Failed to emit close frame, terminating", exc_info=True)
                self._terminate()
        else:
            self._terminate()

    def _limit_rate(self, opcode):
        if opcode in DATA_OP:
            timestamps = self._incoming_frame_timestamps
            delay = self.RL_DELAY
        else:
            timestamps = self._incoming_control_frame_timestamps
            delay = self.RL_DELAY / self.RL_CONTROL_FACTOR
        now = self._clock()
        if (
            len(timestamps) == timestamps.maxlen
            and now - timestamps[0] < delay * timestamps.maxlen
        ):
            raise RateLimitExceededError
        timestamps.append(now)

    def _trigger_lifecycle_event(self, event_type):
        if not self.__event_callbacks[event_type]:
            return
        with acquire_cursor(self._db) as cr:
            env = self.new_env(cr, self._session, set_lang=True)
            for callback in self.__event_callbacks[event_type]:
                try:
                    retrying(functools.partial(callback, env, self), env)
                except Exception:
                    _logger.warning(
                        "Error during Websocket %s callback",
                        LifecycleEvent(event_type).name,
                        exc_info=True,
                    )

    def _send_control_command(self, command, data=None):
        self.__cmd_queue.put((command, next(_command_uid), data))

    def _process_control_command(self, command, data):
        match command:
            case ControlCommand.DISPATCH:
                self._dispatch_bus_notifications()
            case ControlCommand.CLOSE:
                self._disconnect(data["code"], data.get("reason"))

    def _dispatch_bus_notifications(self):
        now = self._clock()
        must_validate = (
            now >= self._session_validated_until
            or self._session.sid != self._validated_session_sid
        )
        if must_validate:
            self._session = _follow_session_chain(self._session)
        session = self._session
        self._waiting_for_dispatch = False
        # Subscribers to a busy channel converge on one cursor, so a dispatch
        # round asks the same question once per connection. Each wake
        # authorises at most one shared answer, in the round that wake belongs
        # to: a dispatch nobody woke, or a second dispatch inside one round,
        # queries for itself. That keeps a hit to rows committed before the
        # notification that opened the round; anything later wakes the
        # connection again, because _waiting_for_dispatch is cleared above.
        # The result is read-only downstream -- _send only serialises it.
        poll_round = self._poll_round
        self._poll_round = None
        memo_key = (
            session.db,
            frozenset(self._channels),
            self._dispatch_state.last_id,
            tuple(self._dispatch_state.ignore_ids),
        )
        cached = None
        if poll_round is not None and not must_validate:
            cached = dispatch.poll_memo_get(poll_round, memo_key)
        if cached is not None:
            notifications, truncated = cached
        else:
            with acquire_cursor(session.db) as cr:
                env = self.new_env(cr, session)
                if must_validate:
                    if session.uid is not None and not is_session_valid(session, env):
                        raise SessionExpiredException
                    self._session_validated_until = now + self.SESSION_VALIDITY_TTL
                    self._validated_session_sid = session.sid
                notifications, truncated = env["bus.bus"]._poll_batch(
                    self._channels,
                    self._dispatch_state.last_id,
                    self._dispatch_state.ignore_ids,
                )
            if poll_round is not None:
                dispatch.poll_memo_set(poll_round, memo_key, (notifications, truncated))
        if not notifications:
            return
        self._dispatch_state.record_dispatched([notif["id"] for notif in notifications])
        self._send(notifications)
        if truncated:
            self.trigger_notification_dispatching()

    def new_env(self, cr, session, *, set_lang=False):
        uid = session.uid
        ctx = dict(session.context, lang=None)
        env = api.Environment(cr, uid, ctx)
        if set_lang:
            lang = env["res.lang"]._get_code(ctx["lang"])
            env = env(context=dict(ctx, lang=lang))
        if not env.transaction.default_env:
            env.transaction.default_env = env
        return env


class TimeoutManager:
    TIMEOUT = 15
    KEEP_ALIVE_TIMEOUT = int(config["websocket_keep_alive_timeout"])
    CONNECTION_TIMEOUT = 60
    INACTIVITY_TIMEOUT = CONNECTION_TIMEOUT - 20

    def __init__(self, clock=None):
        super().__init__()
        self._clock = clock if clock is not None else time.monotonic
        self._expiration_time_by_opcode = {}
        self._keep_alive_timeout = self.KEEP_ALIVE_TIMEOUT + random.uniform(
            0, self.KEEP_ALIVE_TIMEOUT / 2
        )
        now = self._clock()
        self._keep_alive_expiration_time = now + self._keep_alive_timeout
        self._next_ping_time = now + self.INACTIVITY_TIMEOUT

    def acknowledge_frame_receipt(self, frame):
        self._next_ping_time = self._clock() + self.INACTIVITY_TIMEOUT
        self._expiration_time_by_opcode.pop(frame.opcode, None)

    def acknowledge_frame_sent(self, frame):
        now = self._clock()
        self._next_ping_time = now + self.INACTIVITY_TIMEOUT
        if frame.opcode in (Opcode.PING, Opcode.CLOSE):
            self._expiration_time_by_opcode[
                Opcode.PONG if frame.opcode is Opcode.PING else Opcode.CLOSE
            ] = now + self.TIMEOUT

    def has_keep_alive_timed_out(self):
        return self._clock() >= self._keep_alive_expiration_time

    def has_frame_response_timed_out(self):
        now = self._clock()
        return any(
            now >= expiration for expiration in self._expiration_time_by_opcode.values()
        )

    def is_ping_frame_required(self):
        return (
            not self.has_frame_response_timed_out()
            and not self.has_keep_alive_timed_out()
            and self._clock() >= self._next_ping_time
        )


def _follow_session_chain(initial_session):
    session = root.session_store.get(initial_session.sid)
    for _ in range(10):
        if not session:
            raise SessionExpiredException
        if "next_sid" not in session:
            return session
        session = root.session_store.get(session["next_sid"])
    raise SessionExpiredException


_wsrequest_stack = LocalStack()
wsrequest = _wsrequest_stack()


class WebsocketRequest:
    def __init__(self, db, httprequest, websocket):
        self.db = db
        self.httprequest = httprequest
        self.session = None
        self.ws = websocket
        self.app = root
        self.registry = None

    def __enter__(self):
        _wsrequest_stack.push(self)
        return self

    def __exit__(self, *args):
        _wsrequest_stack.pop()

    def serve_websocket_message(self, message):
        try:
            jsonrequest = orjson.loads(message)
            if not isinstance(jsonrequest, dict):
                raise InvalidWebsocketRequestError(
                    "Websocket request must be a JSON object"
                )
            event_name = jsonrequest["event_name"]
        except KeyError as exc:
            raise InvalidWebsocketRequestError(
                f"Key {exc.args[0]!r} is missing from request"
            ) from exc
        except ValueError as exc:
            raise InvalidWebsocketRequestError(
                f"Invalid JSON data, {exc.args[0]}"
            ) from exc
        data = jsonrequest.get("data")
        self.session = self._get_session()

        try:
            self.registry = Registry(self.db).check_signaling()
            threading.current_thread().dbname = self.registry.db_name
        except (
            AttributeError,
            psycopg.OperationalError,
            psycopg.ProgrammingError,
        ) as exc:
            raise InvalidDatabaseError from exc

        with acquire_cursor(self.db) as cr:
            self.env = self.ws.new_env(cr, self.session, set_lang=True)
            retrying(
                functools.partial(self._serve_ir_websocket, event_name, data),
                self.env,
            )

    def _serve_ir_websocket(self, event_name, data):
        self.env["ir.websocket"]._authenticate()
        if event_name == "subscribe":
            self.env["ir.websocket"]._subscribe(data)
        self.env["ir.websocket"]._serve_ir_websocket(event_name, data)

    def _get_session(self):
        session = _follow_session_chain(self.ws._session)
        self.ws._session = session
        return session

    def update_env(self, user=None, context=None, su=None):
        Request.update_env(self, user, context, su)

    def update_context(self, **overrides):
        self.update_env(context=dict(self.env.context, **overrides))

    @functools.cached_property
    def cookies(self):
        cookies = MultiDict(self.httprequest.cookies)
        if self.registry:
            self.registry["ir.http"]._update_cookies(cookies)
        return ImmutableMultiDict(cookies)


class WebsocketConnectionHandler:
    SUPPORTED_VERSIONS = {"13"}
    _HANDSHAKE_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
    _REQUIRED_HANDSHAKE_HEADERS = {
        "connection",
        "host",
        "sec-websocket-key",
        "sec-websocket-version",
        "upgrade",
    }
    _VERSION = "19.0-10"

    @classmethod
    def websocket_allowed(cls, request):
        return not modules.module.current_test

    @classmethod
    def open_connection(cls, request, version):
        if not cls.websocket_allowed(request):
            raise ServiceUnavailable("Websocket is disabled in test mode")
        try:
            response = cls._get_handshake_response(request.httprequest.headers)
            socket = request.httprequest.raw_environ["odoo.socket"]
            public_session = cls._handle_public_configuration(request)
            session, db, httprequest = (
                (public_session or request.session),
                request.db,
                request.httprequest,
            )
            response.call_on_close(
                lambda: cls._serve_forever(
                    Websocket(socket, session, httprequest.cookies),
                    db,
                    httprequest,
                    version,
                )
            )
            if public_session is None:
                request.session.is_dirty = True
            return response
        except KeyError as err:
            raise ServiceUnavailable(
                "Websocket unavailable on this port. Use the evented service port."
            ) from err
        except HTTPException as exc:
            _logger.error(exc)
            raise

    @classmethod
    def _get_handshake_response(cls, headers):
        cls._assert_handshake_validity(headers)
        accept_header = hashlib.sha1(
            (headers["sec-websocket-key"] + cls._HANDSHAKE_GUID).encode()
        ).digest()
        accept_header = base64.b64encode(accept_header)
        return Response(
            status=101,
            headers={
                "Upgrade": "websocket",
                "Connection": "Upgrade",
                "Sec-WebSocket-Accept": accept_header.decode(),
            },
        )

    @classmethod
    def _handle_public_configuration(cls, request):
        origin = request.httprequest.headers.get("origin", "")
        if cls._is_trusted_origin(origin, request):
            return None
        _logger.warning(
            "Downgrading websocket session. Host=%(host)s, Origin=%(origin)s, "
            "Scheme=%(scheme)s.",
            {
                "host": request.httprequest.host,
                "origin": origin,
                "scheme": request.httprequest.scheme,
            },
        )
        return cls._get_shared_public_session(request.session.db)

    @staticmethod
    def _get_shared_public_session(db):
        with _public_session_lock:
            sid = _public_session_sid_by_db.get(db)
            session = root.session_store.get(sid) if sid else None
            if not session:
                session = root.session_store.new()
                session.update(prepare_default_session(), db=db)
                root.session_store.save(session)
                _public_session_sid_by_db[db] = session.sid
            return session

    @staticmethod
    def _normalize_origin(origin):
        url = urlparse(origin.strip())
        scheme = url.scheme.lower()
        netloc = url.netloc.lower()
        default_port = {"http": ":80", "https": ":443", "ws": ":80", "wss": ":443"}
        suffix = default_port.get(scheme)
        if suffix and netloc.endswith(suffix):
            netloc = netloc.removesuffix(suffix)
        return f"{scheme}://{netloc}"

    @classmethod
    def _is_trusted_origin(cls, origin, request):
        origin = cls._normalize_origin(origin)
        expected = cls._normalize_origin(
            f"{request.httprequest.scheme}://{request.httprequest.host}"
        )
        if origin == expected:
            return True
        trusted_origins = os.getenv("ODOO_BUS_TRUSTED_ORIGINS", "")
        return origin in {
            cls._normalize_origin(trusted)
            for trusted in trusted_origins.split(",")
            if trusted.strip()
        }

    @classmethod
    def _assert_handshake_validity(cls, headers):
        missing_or_empty_headers = {
            header
            for header in cls._REQUIRED_HANDSHAKE_HEADERS
            if not headers.get(header)
        }
        if missing_or_empty_headers:
            raise BadRequest(
                f"""Empty or missing header(s): {", ".join(missing_or_empty_headers)}"""
            )

        if headers["upgrade"].lower() != "websocket":
            raise BadRequest("Invalid upgrade header")
        if "upgrade" not in headers["connection"].lower():
            raise BadRequest("Invalid connection header")
        if headers["sec-websocket-version"] not in cls.SUPPORTED_VERSIONS:
            raise UpgradeRequired

        key = headers["sec-websocket-key"]
        try:
            decoded_key = base64.b64decode(key, validate=True)
        except ValueError as err:
            raise BadRequest("Sec-WebSocket-Key should be b64 encoded") from err
        if len(decoded_key) != 16:
            raise BadRequest("Sec-WebSocket-Key should be of length 16 once decoded")

    @classmethod
    def _serve_forever(cls, websocket, db, httprequest, version):
        current_thread = threading.current_thread()
        current_thread.type = "websocket"
        if httprequest.user_agent and version != cls._VERSION:
            websocket.close(CloseCode.CLEAN, "OUTDATED_VERSION")
        for message in websocket.get_messages():
            if message == b"\x00":
                continue
            cls._serve_message(db, httprequest, websocket, message)

    @classmethod
    def _serve_message(cls, db, httprequest, websocket, message):
        with WebsocketRequest(db, httprequest, websocket) as req:
            try:
                req.serve_websocket_message(message)
            except SessionExpiredException:
                websocket.close(CloseCode.SESSION_EXPIRED)
            except PoolError:
                websocket.close(CloseCode.TRY_LATER)
            except InvalidDatabaseError:
                _logger.warning(
                    "Closing websocket: database %r is unavailable or "
                    "incompatible with this server",
                    db,
                )
                websocket.close(CloseCode.TRY_LATER)
            except (
                InvalidWebsocketRequestError,
                ValueError,
                AccessDenied,
            ) as exc:
                _logger.warning("Invalid websocket request: %s", exc)
            except Exception:
                _logger.exception(
                    "Exception occurred during websocket request handling"
                )


def _kick_all(code=CloseCode.GOING_AWAY):
    with _websocket_instances_lock:
        websockets = list(_websocket_instances)
    for websocket in websockets:
        if websocket.state is ConnectionState.OPEN:
            websocket.close(code)


CommonServer.register_on_stop_hook(_kick_all)
