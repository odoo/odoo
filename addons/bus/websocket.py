import base64
import bisect
import functools
import hashlib
import logging
import os
import psycopg2
import random
import socket
import struct
import selectors
import threading
import time
from collections import defaultdict, deque
from contextlib import contextmanager, suppress
from enum import IntEnum
from psycopg2.pool import PoolError
from urllib.parse import urlparse
from weakref import WeakSet

from werkzeug.local import LocalStack
from werkzeug.datastructures import ImmutableMultiDict, MultiDict
from werkzeug.exceptions import BadRequest, HTTPException, ServiceUnavailable

import odoo
from odoo import api, modules
from .models.bus import dispatch
from .tools import orjson
from odoo.http import root, Request, Response, SessionExpiredException, get_default_session
from odoo.modules.registry import Registry
from odoo.service import model as service_model
from odoo.service.server import CommonServer
from odoo.service.security import check_session
from odoo.tools import config, lazy_property

_logger = logging.getLogger(__name__)


MAX_TRY_ON_POOL_ERROR = 10
DELAY_ON_POOL_ERROR = 0.15
JITTER_ON_POOL_ERROR = 0.3


@contextmanager
def acquire_cursor(db):
    """ Try to acquire a cursor up to `MAX_TRY_ON_POOL_ERROR` """
    delay = DELAY_ON_POOL_ERROR
    try:
        for _ in range(MAX_TRY_ON_POOL_ERROR):
            # Yield before trying to acquire the cursor to let other
            # greenlets release their cursor.
            time.sleep(0)
            with suppress(PoolError), Registry(db).cursor() as cr:
                yield cr
                return
            time.sleep(delay + random.uniform(0, JITTER_ON_POOL_ERROR))
            delay *= 1.5
        raise PoolError('Failed to acquire cursor after %s retries' % MAX_TRY_ON_POOL_ERROR)
    finally:
        # Yield after releasing the cursor to let waiting greenlets
        # immediately pick up the freed connection.
        time.sleep(0)

# ------------------------------------------------------
# EXCEPTIONS
# ------------------------------------------------------

class UpgradeRequired(HTTPException):
    code = 426
    description = "Wrong websocket version was given during the handshake"

    def get_headers(self, environ=None):
        headers = super().get_headers(environ)
        headers.append((
            'Sec-WebSocket-Version',
            '; '.join(WebsocketConnectionHandler.SUPPORTED_VERSIONS)
        ))
        return headers


class WebsocketException(Exception):
    """ Base class for all websockets exceptions """


class ConnectionClosed(WebsocketException):
    """
    Raised when the other end closes the socket without performing
    the closing handshake.
    """


class InvalidCloseCodeException(WebsocketException):
    def __init__(self, code):
        super().__init__(f"Invalid close code: {code}")


class InvalidDatabaseException(WebsocketException):
    """
    When raised: the database probably does not exists anymore, the
    database is corrupted or the database version doesn't match the
    server version.
    """


class InvalidStateException(WebsocketException):
    """
    Raised when an operation is forbidden in the current state.
    """


class InvalidWebsocketRequest(WebsocketException):
    """
    Raised when a websocket request is invalid (format, wrong args).
    """


class PayloadTooLargeException(WebsocketException):
    """
    Raised when a websocket message is too large.
    """


class ProtocolError(WebsocketException):
    """
    Raised when a frame format doesn't match expectations.
    """


class RateLimitExceededException(Exception):
    """
    Raised when a client exceeds the number of request in a given
    time.
    """


# ------------------------------------------------------
# WEBSOCKET LIFECYCLE
# ------------------------------------------------------


class LifecycleEvent(IntEnum):
    OPEN = 0
    CLOSE = 1


# ------------------------------------------------------
# WEBSOCKET
# ------------------------------------------------------


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


class ConnectionState(IntEnum):
    OPEN = 0
    CLOSING = 1
    CLOSED = 2


DATA_OP = {Opcode.TEXT, Opcode.BINARY}
CTRL_OP = {Opcode.CLOSE, Opcode.PING, Opcode.PONG}
HEARTBEAT_OP = {Opcode.PING, Opcode.PONG}

VALID_CLOSE_CODES = {
    code for code in CloseCode if code is not CloseCode.ABNORMAL_CLOSURE
}
RESERVED_CLOSE_CODES = range(3000, 5000)

_XOR_TABLE = [bytes(a ^ b for a in range(256)) for b in range(256)]


class Frame:
    def __init__(
        self,
        opcode,
        payload=b'',
        fin=True,
        rsv1=False,
        rsv2=False,
        rsv3=False
    ):
        self.opcode = opcode
        self.payload = payload
        self.fin = fin
        self.rsv1 = rsv1
        self.rsv2 = rsv2
        self.rsv3 = rsv3


class CloseFrame(Frame):
    def __init__(self, code, reason):
        if code not in VALID_CLOSE_CODES and code not in RESERVED_CLOSE_CODES:
            raise InvalidCloseCodeException(code)
        payload = struct.pack('!H', code)
        if reason:
            payload += reason.encode('utf-8')
        self.code = code
        self.reason = reason
        super().__init__(Opcode.CLOSE, payload)


_websocket_instances = WeakSet()


class Websocket:
    __event_callbacks = defaultdict(set)
    # Maximum size for a message in bytes, whether it is sent as one
    # frame or many fragmented ones.
    MESSAGE_MAX_SIZE = 2 ** 20
    # How much time (in second) the history of last dispatched notifications is
    # kept in memory for each websocket.
    # To avoid duplicate notifications, we fetch them based on their ids.
    # However during parallel transactions, ids are assigned immediately (when
    # they are requested), but the notifications are dispatched at the time of
    # the commit. This means lower id notifications might be dispatched after
    # higher id notifications.
    # Simply incrementing the last id is sufficient to guarantee no duplicates,
    # but it is not sufficient to guarantee all notifications are dispatched,
    # and in particular not sufficient for those with a lower id coming after a
    # higher id was dispatched.
    # To solve the issue of missed notifications, the lowest id, stored in
    # ``_last_notif_sent_id``, is held back by a few seconds to give time for
    # concurrent transactions to finish. To avoid dispatching duplicate
    # notifications, the history of already dispatched notifications during this
    # period is kept in memory in ``_notif_history`` and the corresponding
    # notifications are discarded from subsequent dispatching even if their id
    # is higher than ``_last_notif_sent_id``.
    # In practice, what is important functionally is the time between the create
    # of the notification and the commit of the transaction in business code.
    # If this time exceeds this threshold, the notification will never be
    # dispatched if the target user receive any other notification in the
    # meantime.
    # Transactions known to be long should therefore create their notifications
    # at the end, as close as possible to their commit.
    MAX_NOTIFICATION_HISTORY_SEC = 10
    # How many requests can be made in excess of the given rate.
    RL_BURST = int(config['websocket_rate_limit_burst'])
    # How many seconds between each request.
    RL_DELAY = float(config['websocket_rate_limit_delay'])

    def __init__(self, sock, session, cookies):
        # Session linked to the current websocket connection.
        self._session = session
        # Cookies linked to the current websocket connection.
        self._cookies = cookies
        self._db = session.db
        self.__socket = sock
        self._close_sent = False
        self._close_received = False
        self._timeout_manager = TimeoutManager()
        # Used for rate limiting.
        self._incoming_frame_timestamps = deque(maxlen=self.RL_BURST)
        # Used to notify the websocket that bus notifications are
        # available.
        self.__notif_sock_w, self.__notif_sock_r = socket.socketpair()
        self._channels = set()
        # For ``_last_notif_sent_id and ``_notif_history``, see
        # ``MAX_NOTIFICATION_HISTORY_SEC`` for more details.
        # id of the last sent notification that is no longer in _notif_history
        self._last_notif_sent_id = 0
        # history of last sent notifications in the format (notif_id, send_time)
        # always sorted by notif_id ASC
        self._notif_history = []
        # Websocket start up
        self.__selector = (
            selectors.PollSelector()
            if odoo.evented and hasattr(selectors, 'PollSelector')
            else selectors.DefaultSelector()
        )
        self.__selector.register(self.__socket, selectors.EVENT_READ)
        self.__selector.register(self.__notif_sock_r, selectors.EVENT_READ)
        self.state = ConnectionState.OPEN
        _websocket_instances.add(self)
        self._trigger_lifecycle_event(LifecycleEvent.OPEN)

    # ------------------------------------------------------
    # PUBLIC METHODS
    # ------------------------------------------------------

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
                    self.disconnect(CloseCode.KEEP_ALIVE_TIMEOUT)
                    continue
                if self._timeout_manager.has_frame_response_timed_out():
                    self._terminate()
                    continue
                if not readables and self._timeout_manager.should_send_ping_frame():
                    self._send_ping_frame()
                    continue
                if self.__notif_sock_r in readables:
                    self._dispatch_bus_notifications()
                if self.__socket in readables:
                    message = self._process_next_message()
                    if message is not None:
                        yield message
            except Exception as exc:
                self._handle_transport_error(exc)

    def disconnect(self, code, reason=None):
        """
        Initiate the closing handshake that is, send a close frame
        to the other end which will then send us back an
        acknowledgment. Upon the reception of this acknowledgment,
        the `_terminate` method will be called to perform an
        orderly shutdown. Note that we don't need to wait for the
        acknowledgment if the connection was failed beforewards.
        """
        if code is not CloseCode.ABNORMAL_CLOSURE:
            self._send_close_frame(code, reason)
        else:
            self._terminate()

    @classmethod
    def onopen(cls, func):
        cls.__event_callbacks[LifecycleEvent.OPEN].add(func)
        return func

    @classmethod
    def onclose(cls, func):
        cls.__event_callbacks[LifecycleEvent.CLOSE].add(func)
        return func

    def subscribe(self, channels, last):
        """ Subscribe to bus channels. """
        self._channels = channels
        # Only assign the last id according to the client once: the server is
        # more reliable later on, see ``MAX_NOTIFICATION_HISTORY_SEC``.
        if self._last_notif_sent_id == 0:
            self._last_notif_sent_id = last
        # Dispatch past notifications if there are any.
        self.trigger_notification_dispatching()

    def trigger_notification_dispatching(self):
        """
        Warn the socket that notifications are available. Ignore if a
        dispatch is already planned or if the socket is already in the
        closing state.
        """
        if self.state is not ConnectionState.OPEN:
            return
        readables = {
            selector_key[0].fileobj for selector_key in
            self.__selector.select(0)
        }
        if self.__notif_sock_r not in readables:
            # Send a random bit to mark the socket as readable.
            # Ignore if the socket was closed in the meantime.
            with suppress(OSError):
                self.__notif_sock_w.send(b'x')

    # ------------------------------------------------------
    # PRIVATE METHODS
    # ------------------------------------------------------

    def _get_next_frame(self):
        #     0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
        #    +-+-+-+-+-------+-+-------------+-------------------------------+
        #    |F|R|R|R| opcode|M| Payload len |    Extended payload length    |
        #    |I|S|S|S|  (4)  |A|     (7)     |             (16/64)           |
        #    |N|V|V|V|       |S|             |   (if payload len==126/127)   |
        #    | |1|2|3|       |K|             |                               |
        #    +-+-+-+-+-------+-+-------------+ - - - - - - - - - - - - - - - +
        #    |     Extended payload length continued, if payload len == 127  |
        #    + - - - - - - - - - - - - - - - +-------------------------------+
        #    |                               |Masking-key, if MASK set to 1  |
        #    +-------------------------------+-------------------------------+
        #    | Masking-key (continued)       |          Payload Data         |
        #    +-------------------------------- - - - - - - - - - - - - - - - +
        #    :                     Payload Data continued ...                :
        #    + - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - +
        #    |                     Payload Data continued ...                |
        #    +---------------------------------------------------------------+
        def recv_bytes(n):
            """ Pull n bytes from the socket """
            data = bytearray()
            while len(data) < n:
                received_data = self.__socket.recv(n - len(data))
                if not received_data:
                    raise ConnectionClosed()
                data.extend(received_data)
            return data

        def is_bit_set(byte, n):
            """
            Check whether nth bit of byte is set or not (from left
            to right).
             """
            return byte & (1 << (7 - n))

        def apply_mask(payload, mask):
            # see: https://www.willmcgugan.com/blog/tech/post/speeding-up-websockets-60x/
            a, b, c, d = (_XOR_TABLE[n] for n in mask)
            payload[::4] = payload[::4].translate(a)
            payload[1::4] = payload[1::4].translate(b)
            payload[2::4] = payload[2::4].translate(c)
            payload[3::4] = payload[3::4].translate(d)
            return payload

        self._limit_rate()
        first_byte, second_byte = recv_bytes(2)
        fin, rsv1, rsv2, rsv3 = (is_bit_set(first_byte, n) for n in range(4))
        try:
            opcode = Opcode(first_byte & 0b00001111)
        except ValueError as exc:
            raise ProtocolError(exc)
        payload_length = second_byte & 0b01111111

        if rsv1 or rsv2 or rsv3:
            raise ProtocolError("Reserved bits must be unset")
        if not is_bit_set(second_byte, 0):
            raise ProtocolError("Frame must be masked")
        if opcode in CTRL_OP:
            if not fin:
                raise ProtocolError("Control frames cannot be fragmented")
            if payload_length > 125:
                raise ProtocolError(
                    "Control frames payload must be smaller than 126"
                )
        if payload_length == 126:
            payload_length = struct.unpack('!H', recv_bytes(2))[0]
        elif payload_length == 127:
            payload_length = struct.unpack('!Q', recv_bytes(8))[0]
        if payload_length > self.MESSAGE_MAX_SIZE:
            raise PayloadTooLargeException()

        mask = recv_bytes(4)
        payload = apply_mask(recv_bytes(payload_length), mask)
        frame = Frame(opcode, bytes(payload), fin, rsv1, rsv2, rsv3)
        self._timeout_manager.acknowledge_frame_receipt(frame)
        return frame

    def _process_next_message(self):
        """
        Process the next message coming throught the socket. If a
        data message can be extracted, return its decoded payload.
        As per the RFC, only control frames will be processed once
        the connection reaches the closing state.
        """
        frame = self._get_next_frame()
        if frame.opcode in CTRL_OP:
            self._handle_control_frame(frame)
            return
        if self.state is not ConnectionState.OPEN:
            # After receiving a control frame indicating the connection
            # should be closed, a peer discards any further data
            # received.
            return
        if frame.opcode is Opcode.CONTINUE:
            raise ProtocolError("Unexpected continuation frame")
        message = frame.payload
        if not frame.fin:
            message = self._recover_fragmented_message(frame)
        return (
            message.decode('utf-8')
            if message is not None and frame.opcode is Opcode.TEXT else message
        )

    def _recover_fragmented_message(self, initial_frame):
        message_fragments = bytearray(initial_frame.payload)
        while True:
            frame = self._get_next_frame()
            if frame.opcode in CTRL_OP:
                # Control frames can be received in the middle of a
                # fragmented message, process them as soon as possible.
                self._handle_control_frame(frame)
                if self.state is not ConnectionState.OPEN:
                    return
                continue
            if frame.opcode is not Opcode.CONTINUE:
                raise ProtocolError("A continuation frame was expected")
            message_fragments.extend(frame.payload)
            if len(message_fragments) > self.MESSAGE_MAX_SIZE:
                raise PayloadTooLargeException()
            if frame.fin:
                return bytes(message_fragments)

    def _send(self, message):
        if self.state is not ConnectionState.OPEN:
            raise InvalidStateException(
                "Trying to send a frame on a closed socket"
            )
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
            frame.payload = frame.payload.encode('utf-8')
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
            output.extend(
                struct.pack('!BB', first_byte, payload_length)
            )
        elif payload_length < 65536:
            output.extend(
                struct.pack('!BBH', first_byte, 126, payload_length)
            )
        else:
            output.extend(
                struct.pack('!BBQ', first_byte, 127, payload_length)
            )
        output.extend(frame.payload)
        self.__socket.sendall(output)
        self._timeout_manager.acknowledge_frame_sent(frame)
        if not isinstance(frame, CloseFrame):
            return
        self.state = ConnectionState.CLOSING
        self._close_sent = True
        if frame.code is CloseCode.ABNORMAL_CLOSURE or self._close_received:
            self._terminate()
            return
        # After sending a control frame indicating the connection
        # should be closed, a peer does not send any further data.
        self.__selector.unregister(self.__notif_sock_r)

    def _send_close_frame(self, code, reason=None):
        """ Send a close frame. """
        self._send_frame(CloseFrame(code, reason))

    def _send_ping_frame(self):
        """ Send a ping frame """
        self._send_frame(Frame(Opcode.PING))

    def _send_pong_frame(self, payload):
        """ Send a pong frame """
        self._send_frame(Frame(Opcode.PONG, payload))

    def _terminate(self):
        """ Close the underlying TCP socket. """
        if self.state == ConnectionState.CLOSED:
            return
        self.state = ConnectionState.CLOSED
        with suppress(OSError, TimeoutError):
            self.__socket.shutdown(socket.SHUT_WR)
            # Call recv until obtaining a return value of 0 indicating
            # the other end has performed an orderly shutdown. A timeout
            # is set to ensure the connection will be closed even if
            # the other end does not close the socket properly.
            self.__socket.settimeout(1)
            while self.__socket.recv(4096):
                pass
        self.__selector.unregister(self.__socket)
        self.__selector.close()
        self.__socket.close()
        self.__notif_sock_r.close()
        self.__notif_sock_w.close()
        dispatch.unsubscribe(self)
        self._trigger_lifecycle_event(LifecycleEvent.CLOSE)
        with acquire_cursor(self._db) as cr:
            env = api.Environment(cr, self._session.uid, self._session.context)
            env["ir.websocket"]._on_websocket_closed(self._cookies)

    def _handle_control_frame(self, frame):
        if frame.opcode is Opcode.PING:
            self._send_pong_frame(frame.payload)
        elif frame.opcode is Opcode.CLOSE:
            self.state = ConnectionState.CLOSING
            self._close_received = True
            code, reason = CloseCode.CLEAN, None
            if len(frame.payload) >= 2:
                code = struct.unpack('!H', frame.payload[:2])[0]
                reason = frame.payload[2:].decode('utf-8')
            elif frame.payload:
                raise ProtocolError("Malformed closing frame")
            if not self._close_sent:
                self._send_close_frame(code, reason)
            else:
                self._terminate()

    def _handle_transport_error(self, exc):
        """
        Find out which close code should be sent according to given
        exception and call `self.disconnect` in order to close the
        connection cleanly.
        """
        code, reason = CloseCode.SERVER_ERROR, str(exc)
        if isinstance(exc, (ConnectionClosed, OSError)):
            code = CloseCode.ABNORMAL_CLOSURE
        elif isinstance(exc, (ProtocolError, InvalidCloseCodeException)):
            code = CloseCode.PROTOCOL_ERROR
        elif isinstance(exc, UnicodeDecodeError):
            code = CloseCode.INCONSISTENT_DATA
        elif isinstance(exc, PayloadTooLargeException):
            code = CloseCode.MESSAGE_TOO_BIG
        elif isinstance(exc, (PoolError, RateLimitExceededException)):
            code = CloseCode.TRY_LATER
        elif isinstance(exc, SessionExpiredException):
            code = CloseCode.SESSION_EXPIRED
        if code is CloseCode.SERVER_ERROR:
            reason = None
            registry = Registry(self._session.db)
            sequence = registry.registry_sequence
            registry = registry.check_signaling()
            if sequence != registry.registry_sequence:
                _logger.warning("Bus operation aborted; registry has been reloaded")
            else:
                _logger.error(exc, exc_info=True)
        if self.state is ConnectionState.OPEN:
            self.disconnect(code, reason)
        else:
            self._terminate()

    def _limit_rate(self):
        """
        This method is a simple rate limiter designed not to allow
        more than one request by `RL_DELAY` seconds. `RL_BURST` specify
        how many requests can be made in excess of the given rate at the
        begining. When requests are received too fast, raises the
        `RateLimitExceededException`.
        """
        now = time.time()
        if len(self._incoming_frame_timestamps) >= self.RL_BURST:
            elapsed_time = now - self._incoming_frame_timestamps[0]
            if elapsed_time < self.RL_DELAY * self.RL_BURST:
                raise RateLimitExceededException()
        self._incoming_frame_timestamps.append(now)

    def _trigger_lifecycle_event(self, event_type):
        """
        Trigger a lifecycle event that is, call every function
        registered for this event type. Every callback is given both the
        environment and the related websocket.
        """
        if not self.__event_callbacks[event_type]:
            return
        with acquire_cursor(self._db) as cr:
            lang = api.Environment(cr, self._session.uid, {})['res.lang']._get_code(self._session.context.get('lang'))
            env = api.Environment(cr, self._session.uid, dict(self._session.context, lang=lang))
            for callback in self.__event_callbacks[event_type]:
                try:
                    service_model.retrying(functools.partial(callback, env, self), env)
                except Exception:
                    _logger.warning(
                        'Error during Websocket %s callback',
                        LifecycleEvent(event_type).name,
                        exc_info=True
                    )

    def _dispatch_bus_notifications(self):
        """
        Dispatch notifications related to the registered channels. If
        the session is expired, close the connection with the
        `SESSION_EXPIRED` close code. If no cursor can be acquired,
        close the connection with the `TRY_LATER` close code.
        """
        session = root.session_store.get(self._session.sid)
        if not session:
            raise SessionExpiredException()
        with acquire_cursor(session.db) as cr:
            env = api.Environment(cr, session.uid, dict(session.context, lang=None))
            if session.uid is not None and not check_session(session, env):
                raise SessionExpiredException()
            # Mark the notification request as processed.
            self.__notif_sock_r.recv(1)
            notifications = env["bus.bus"]._poll(
                self._channels, self._last_notif_sent_id, [n[0] for n in self._notif_history]
            )
        if not notifications:
            return
        for notif in notifications:
            bisect.insort(self._notif_history, (notif["id"], time.time()), key=lambda x: x[0])
        # Discard all the smallest notification ids that have expired and
        # increment the last id accordingly. History can only be trimmed of ids
        # that are below the new last id otherwise some notifications might be
        # dispatched again.
        # For example, if the theshold is 10s, and the state is:
        # last id 2, history [(3, 8s), (6, 10s), (7, 7s)]
        # If 6 is removed because it is above the threshold, the next query will
        # be (id > 2 AND id NOT IN (3, 7)) which will fetch 6 again.
        # 6 can only be removed after 3 reaches the threshold and is removed as
        # well, and if 4 appears in the meantime, 3 can be removed but 6 will
        # have to wait for 4 to reach the threshold as well.
        last_index = -1
        for i, notif in enumerate(self._notif_history):
            if time.time() - notif[1] > self.MAX_NOTIFICATION_HISTORY_SEC:
                last_index = i
            else:
                break
        if last_index != -1:
            self._last_notif_sent_id = self._notif_history[last_index][0]
            self._notif_history = self._notif_history[last_index + 1 :]
        self._send(notifications)


class TimeoutManager:
    """
    Track WebSocket activity to determine when a response has timed out,
    when a ping should be sent, and when the connection has exceeded its
    keep-alive duration.
    """
    TIMEOUT = 15
    # Timeout specifying how many seconds the connection should be kept
    # alive.
    KEEP_ALIVE_TIMEOUT = int(config['websocket_keep_alive_timeout'])
    # Proxies and NATs usually close a connection after 1 minute of inactivity.
    # Therefore, a PING frame should be sent if the connection has been idle for
    # a while. Since the selector can block for up to `TIMEOUT` seconds, the
    # worst case delay is 55 seconds (`INACTIVITY_TIMEOUT` + `TIMEOUT`), which
    # is enough to keep the connection alive.
    CONNECTION_TIMEOUT = 60
    INACTIVITY_TIMEOUT = CONNECTION_TIMEOUT - 20

    def __init__(self):
        super().__init__()
        # Maps an awaited response opcode (i.e. PONG, CLOSE) to the
        # time by which the response must be received.
        self._expiration_time_by_opcode = {}
        # Custom keep alive timeout for each TimeoutManager to avoid multiple
        # connections timing out at the same time.
        self._keep_alive_timeout = (
            self.KEEP_ALIVE_TIMEOUT + random.uniform(0, self.KEEP_ALIVE_TIMEOUT / 2)
        )
        self._keep_alive_expiration_time = time.time() + self._keep_alive_timeout
        self._next_ping_time = time.time() + self.INACTIVITY_TIMEOUT

    def acknowledge_frame_receipt(self, frame):
        self._next_ping_time = time.time() + self.INACTIVITY_TIMEOUT
        self._expiration_time_by_opcode.pop(frame.opcode, None)

    def acknowledge_frame_sent(self, frame):
        """
        Acknowledge a frame was sent. If this frame is a PING/CLOSE
        frame, start waiting for an answer.
        """
        now = time.time()
        self._next_ping_time = now + self.INACTIVITY_TIMEOUT
        if frame.opcode in (Opcode.PING, Opcode.CLOSE):
            self._expiration_time_by_opcode[
                Opcode.PONG if frame.opcode is Opcode.PING else Opcode.CLOSE
            ] = now + self.TIMEOUT

    def has_keep_alive_timed_out(self):
        return time.time() >= self._keep_alive_expiration_time

    def has_frame_response_timed_out(self):
        """
        Check if any pending PING or CLOSE frame has been waiting for an answer
        for at least `TIMEOUT` seconds.
        """
        now = time.time()
        return any(now >= expiration for expiration in self._expiration_time_by_opcode.values())

    def should_send_ping_frame(self):
        return (
            not self.has_frame_response_timed_out()
            and not self.has_keep_alive_timed_out()
            and time.time() >= self._next_ping_time
        )


# ------------------------------------------------------
# WEBSOCKET SERVING
# ------------------------------------------------------


_wsrequest_stack = LocalStack()
wsrequest = _wsrequest_stack()

class WebsocketRequest:
    def __init__(self, db, httprequest, websocket):
        self.db = db
        self.httprequest = httprequest
        self.session = None
        self.ws = websocket

    def __enter__(self):
        _wsrequest_stack.push(self)
        return self

    def __exit__(self, *args):
        _wsrequest_stack.pop()

    def serve_websocket_message(self, message):
        try:
            jsonrequest = orjson.loads(message)
            event_name = jsonrequest['event_name']  # mandatory
        except KeyError as exc:
            raise InvalidWebsocketRequest(
                f'Key {exc.args[0]!r} is missing from request'
            ) from exc
        except ValueError as exc:
            raise InvalidWebsocketRequest(
                f'Invalid JSON data, {exc.args[0]}'
            ) from exc
        data = jsonrequest.get('data')
        self.session = self._get_session()

        try:
            self.registry = Registry(self.db)
            threading.current_thread().dbname = self.registry.db_name
            self.registry.check_signaling()
        except (
            AttributeError, psycopg2.OperationalError, psycopg2.ProgrammingError
        ) as exc:
            raise InvalidDatabaseException() from exc

        with acquire_cursor(self.db) as cr:
            lang = api.Environment(cr, self.session.uid, {})['res.lang']._get_code(self.session.context.get('lang'))
            self.env = api.Environment(cr, self.session.uid, dict(self.session.context, lang=lang))
            threading.current_thread().uid = self.env.uid
            service_model.retrying(
                functools.partial(self._serve_ir_websocket, event_name, data),
                self.env,
            )

    def _serve_ir_websocket(self, event_name, data):
        """
        Delegate most of the processing to the ir.websocket model
        which is extensible by applications. Directly call the
        appropriate ir.websocket method since only two events are
        tolerated: `subscribe` and `update_presence`.
        """
        self.env['ir.websocket']._authenticate()
        if event_name == 'subscribe':
            self.env['ir.websocket']._subscribe(data)
        if event_name == 'update_presence':
            self.env['ir.websocket']._update_bus_presence(**data)

    def _get_session(self):
        session = root.session_store.get(self.ws._session.sid)
        if not session:
            raise SessionExpiredException()
        return session

    def update_env(self, user=None, context=None, su=None):
        """
        Update the environment of the current websocket request.
        """
        Request.update_env(self, user, context, su)

    def update_context(self, **overrides):
        """
        Override the environment context of the current request with the
        values of ``overrides``. To replace the entire context, please
        use :meth:`~update_env` instead.
        """
        self.update_env(context=dict(self.env.context, **overrides))

    @lazy_property
    def cookies(self):
        cookies = MultiDict(self.httprequest.cookies)
        if self.registry:
            self.registry['ir.http']._sanitize_cookies(cookies)
        return ImmutableMultiDict(cookies)


class WebsocketConnectionHandler:
    SUPPORTED_VERSIONS = {'13'}
    # Given by the RFC in order to generate Sec-WebSocket-Accept from
    # Sec-WebSocket-Key value.
    _HANDSHAKE_GUID = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
    _REQUIRED_HANDSHAKE_HEADERS = {
        'connection', 'host', 'sec-websocket-key',
        'sec-websocket-version', 'upgrade', 'origin',
    }
    # Latest version of the websocket worker. This version should be incremented
    # every time `websocket_worker.js` is modified to force the browser to fetch
    # the new worker bundle.
    _VERSION = "18.0-7"

    @classmethod
    def websocket_allowed(cls, request):
        return not modules.module.current_test

    @classmethod
    def open_connection(cls, request, version):
        """
        Open a websocket connection if the handshake is successfull.
        :return: Response indicating the server performed a connection
        upgrade.
        :raise: UpgradeRequired if there is no intersection between the
        versions the client supports and those we support.
        :raise: BadRequest if the handshake data is incorrect.
        """
        if not cls.websocket_allowed(request):
            raise ServiceUnavailable("Websocket is disabled in test mode")
        public_session = cls._handle_public_configuration(request)
        try:
            response = cls._get_handshake_response(request.httprequest.headers)
            socket = request.httprequest._HTTPRequest__environ['socket']
            session, db, httprequest = (public_session or request.session), request.db, request.httprequest
            response.call_on_close(lambda: cls._serve_forever(
                Websocket(socket, session, httprequest.cookies),
                db,
                httprequest,
                version
            ))
            # Force save the session. Session must be persisted to handle
            # WebSocket authentication.
            request.session.is_dirty = True
            return response
        except KeyError as exc:
            raise RuntimeError(
                f"Couldn't bind the websocket. Is the connection opened on the evented port ({config['gevent_port']})?"
            ) from exc
        except HTTPException as exc:
            # The HTTP stack does not log exceptions derivated from the
            # HTTPException class since they are valid responses.
            _logger.error(exc)
            raise



    @classmethod
    def _get_handshake_response(cls, headers):
        """
        :return: Response indicating the server performed a connection
        upgrade.
        :raise: BadRequest
        :raise: UpgradeRequired
        """
        cls._assert_handshake_validity(headers)
        # sha-1 is used as it is required by
        # https://datatracker.ietf.org/doc/html/rfc6455#page-7
        accept_header = hashlib.sha1(
            (headers['sec-websocket-key'] + cls._HANDSHAKE_GUID).encode()).digest()
        accept_header = base64.b64encode(accept_header)
        return Response(status=101, headers={
            'Upgrade': 'websocket',
            'Connection': 'Upgrade',
            'Sec-WebSocket-Accept': accept_header.decode(),
        })

    @classmethod
    def _handle_public_configuration(cls, request):
        if not os.getenv('ODOO_BUS_PUBLIC_SAMESITE_WS'):
            return
        headers = request.httprequest.headers
        origin_url = urlparse(headers.get('origin'))
        if origin_url.netloc != headers.get('host') or origin_url.scheme != request.httprequest.scheme:
            _logger.warning(
                'Downgrading websocket session. Host=%(host)s, Origin=%(origin)s, Scheme=%(scheme)s.',
                {
                    'host': headers.get('host'),
                    'origin': headers.get('origin'),
                    'scheme': request.httprequest.scheme,
                },
            )
            session = root.session_store.new()
            session.update(get_default_session(), db=request.session.db)
            root.session_store.save(session)
            return session
        return None

    @classmethod
    def _assert_handshake_validity(cls, headers):
        """
        :raise: UpgradeRequired if there is no intersection between
        the version the client supports and those we support.
        :raise: BadRequest in case of invalid handshake.
        """
        missing_or_empty_headers = {
            header for header in cls._REQUIRED_HANDSHAKE_HEADERS
            if header not in headers
        }
        if missing_or_empty_headers:
            raise BadRequest(
                f"""Empty or missing header(s): {', '.join(missing_or_empty_headers)}"""
            )

        if headers['upgrade'].lower() != 'websocket':
            raise BadRequest('Invalid upgrade header')
        if 'upgrade' not in headers['connection'].lower():
            raise BadRequest('Invalid connection header')
        if headers['sec-websocket-version'] not in cls.SUPPORTED_VERSIONS:
            raise UpgradeRequired()

        key = headers['sec-websocket-key']
        try:
            decoded_key = base64.b64decode(key, validate=True)
        except ValueError:
            raise BadRequest("Sec-WebSocket-Key should be b64 encoded")
        if len(decoded_key) != 16:
            raise BadRequest(
                "Sec-WebSocket-Key should be of length 16 once decoded"
            )

    @classmethod
    def _serve_forever(cls, websocket, db, httprequest, version):
        """
        Process incoming messages and dispatch them to the application.
        """
        current_thread = threading.current_thread()
        current_thread.type = 'websocket'
        if httprequest.user_agent and version != cls._VERSION:
            # Close the connection from an outdated worker. We can't use a
            # custom close code because the connection is considered successful,
            # preventing exponential reconnect backoff. This would cause old
            # workers to reconnect frequently, putting pressure on the server.
            # Clean closes don't trigger reconnections, assuming they are
            # intentional. The reason indicates to the origin worker not to
            # reconnect, preventing old workers from lingering after updates.
            # Non browsers are ignored since IOT devices do not provide the
            # worker version.
            websocket.disconnect(CloseCode.CLEAN, "OUTDATED_VERSION")
        for message in websocket.get_messages():
            if message == b'\x00':
                # Ignore internal sentinel message used to detect dead/idle connections.
                continue
            with WebsocketRequest(db, httprequest, websocket) as req:
                try:
                    req.serve_websocket_message(message)
                except SessionExpiredException:
                    websocket.disconnect(CloseCode.SESSION_EXPIRED)
                except PoolError:
                    websocket.disconnect(CloseCode.TRY_LATER)
                except Exception:
                    _logger.exception("Exception occurred during websocket request handling")


def _kick_all():
    """ Disconnect all the websocket instances. """
    for websocket in _websocket_instances:
        if websocket.state is ConnectionState.OPEN:
            websocket.disconnect(CloseCode.GOING_AWAY)


CommonServer.on_stop(_kick_all)
