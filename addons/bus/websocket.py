import base64
import functools
import hashlib
import json
import logging
import psycopg2
import queue
import socket
import struct
import selectors
import threading
import time
from collections import defaultdict, deque
from contextlib import closing, suppress
from enum import IntEnum
from itertools import count
from weakref import WeakSet

from werkzeug.local import LocalStack
from werkzeug.exceptions import BadRequest, HTTPException

from odoo import api
from odoo.http import root, Request, Response, SessionExpiredException
from odoo.modules.registry import Registry
from odoo.service import model as service_model
from odoo.service.server import CommonServer
from odoo.tools import config

_logger = logging.getLogger(__name__)


# Idea taken from the python cookbook:
# https://github.com/dabeaz/python-cookbook/blob/6e46b78e5644b3e5bf7426d900e2203b7cc630da/src/12/polling_multiple_thread_queues/pqueue.py
class PollablePriorityQueue(queue.PriorityQueue):
    """ A custom PriorityQueue than can be polled """
    # This class allow this queue to be used with select.
    def __init__(self):
        super().__init__()
        self._putsocket, self._getsocket = socket.socketpair()

    def fileno(self):
        return self._getsocket.fileno()

    def put(self, item, **kwargs):
        super().put(item, **kwargs)
        self._putsocket.send(b'x')

    def get(self, **kwargs):
        self._getsocket.recv(1)
        return super().get(**kwargs)


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
CLEAN_CLOSE_CODES = {CloseCode.CLEAN, CloseCode.GOING_AWAY, CloseCode.RESTART}
RESERVED_CLOSE_CODES = range(3000, 5000)

_XOR_TABLE = [bytes(a ^ b for a in range(256)) for b in range(256)]


class Frame:
    # This class implements the `__lt__` method in order for frames to
    # be stored in a `PriorityQueue`: ping/pong frames are prioritary.
    _frames_sent = count(0)

    def __init__(
        self,
        opcode,
        payload=b'',
        fin=True,
        rsv1=False,
        rsv2=False,
        rsv3=False
    ):
        self._send_order = next(self._frames_sent)
        self.opcode = opcode
        self.payload = payload
        self.fin = fin
        self.rsv1 = rsv1
        self.rsv2 = rsv2
        self.rsv3 = rsv3

    def __lt__(self, other):
        if not isinstance(other, Frame):
            return NotImplemented
        if (
            self.opcode in HEARTBEAT_OP and
            other.opcode in HEARTBEAT_OP or
            self.opcode in DATA_OP and other.opcode in DATA_OP
        ):
            return self._send_order < other._send_order
        return self.opcode in HEARTBEAT_OP


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


class Websocket:
    _instances = WeakSet()
    _event_callbacks = defaultdict(set)
    # Maximum size for a message in bytes, whether it is sent as one
    # frame or many fragmented ones.
    MESSAGE_MAX_SIZE = 2 ** 20
    # Proxies usually close a connection after 1 minute of inactivity.
    # Therefore, a PING frame have to be sent if no frame is either sent
    # or received within CONNECTION_TIMEOUT - 15 seconds.
    CONNECTION_TIMEOUT = 60
    INACTIVITY_TIMEOUT = CONNECTION_TIMEOUT - 15
    # How many requests can be made in excess of the given rate.
    RL_BURST = int(config['websocket_rate_limit_burst'])
    # How many seconds between each request.
    RL_DELAY = float(config['websocket_rate_limit_delay'])

    def __init__(self, socket, session):
        # Session linked to the current websocket connection.
        self._session = session
        self._socket = socket
        self._close_sent = False
        self._close_received = False
        self._outgoing_frame_queue = PollablePriorityQueue()
        self._selector = selectors.DefaultSelector()
        self._selector.register(self._socket, selectors.EVENT_READ)
        self._selector.register(self._outgoing_frame_queue, selectors.EVENT_READ)
        self._timeout_manager = TimeoutManager()
        # Used for rate limiting.
        self._incoming_frame_timestamps = deque(maxlen=type(self).RL_BURST)
        self.state = ConnectionState.OPEN
        type(self)._instances.add(self)
        self._trigger_lifecycle_event(LifecycleEvent.OPEN)

    # ------------------------------------------------------
    # PUBLIC METHODS
    # ------------------------------------------------------

    def get_messages(self):
        while self.state is not ConnectionState.CLOSED:
            try:
                readables = {
                    selector_key[0].fileobj for selector_key in
                    self._selector.select(type(self).INACTIVITY_TIMEOUT)
                }
                if self._timeout_manager.has_timed_out():
                    self.disconnect(
                        CloseCode.ABNORMAL_CLOSURE
                        if self._timeout_manager.timeout_reason is TimeoutReason.NO_RESPONSE
                        else CloseCode.KEEP_ALIVE_TIMEOUT
                    )
                    break
                if not readables:
                    self._enqueue_ping_frame()
                    continue
                if self._outgoing_frame_queue in readables:
                    self._send_next_frame()
                    if self.state is ConnectionState.CLOSED:
                        break
                if self._socket in readables:
                    message = self._process_next_message()
                    if message is not None:
                        yield message
            except Exception as exc:
                self._handle_transport_error(exc)

    def send(self, message):
        if self.state is not ConnectionState.OPEN:
            raise InvalidStateException(
                "Trying to send a frame on a closed socket"
            )
        opcode = Opcode.BINARY
        if not isinstance(message, (bytes, bytearray)):
            opcode = Opcode.TEXT
        self._outgoing_frame_queue.put(Frame(opcode, message))

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
            self._enqueue_close_frame(code, reason)
        else:
            self._terminate()

    @classmethod
    def onopen(cls, func):
        cls._event_callbacks[LifecycleEvent.OPEN].add(func)
        return func

    @classmethod
    def onclose(cls, func):
        cls._event_callbacks[LifecycleEvent.CLOSE].add(func)
        return func

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
                received_data = self._socket.recv(n - len(data))
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
        if payload_length > type(self).MESSAGE_MAX_SIZE:
            raise PayloadTooLargeException()

        mask = recv_bytes(4)
        payload = apply_mask(recv_bytes(payload_length), mask)
        frame = Frame(opcode, bytes(payload), fin, rsv1, rsv2, rsv3)
        self._timeout_manager.acknowledge_frame_receipt(frame)
        return frame

    def _send_next_frame(self):
        """ Send the next frame available in the outgoing frame queue. """
        frame = self._outgoing_frame_queue.get_nowait()
        self._send_frame(frame)
        if not isinstance(frame, CloseFrame):
            return
        self.state = ConnectionState.CLOSING
        self._close_sent = True
        if frame.code not in CLEAN_CLOSE_CODES or self._close_received:
            return self._terminate()
        # After sending a control frame indicating the connection
        # should be closed, a peer does not send any further data.
        self._selector.unregister(self._outgoing_frame_queue)

    def _process_next_message(self):
        """
        Process the next message coming throught the socket. If a
        data message can be extracted, return its decoded payload.
        As per the RFC, only control frames will be processed once
        the connection reaches the closing state.
        """
        frame = self._get_next_frame()
        if frame.opcode in CTRL_OP:
            return self._handle_control_frame(frame)
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
            if len(message_fragments) > type(self).MESSAGE_MAX_SIZE:
                raise PayloadTooLargeException()
            if frame.fin:
                return bytes(message_fragments)

    def _send_frame(self, frame):
        if frame.opcode in CTRL_OP and len(frame.payload) > 125:
            raise ProtocolError(
                "Control frames should have a payload length smaller than 126"
            )
        if isinstance(frame.payload, str):
            frame.payload = frame.payload.encode('utf-8')
        elif not isinstance(frame.payload, (bytes, bytearray)):
            frame.payload = json.dumps(frame.payload).encode('utf-8')

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
        self._socket.sendall(output)
        self._timeout_manager.acknowledge_frame_sent(frame)

    def _enqueue_close_frame(self, code, reason=None):
        """ Put a close frame in the outgoing frame queue. """
        self._outgoing_frame_queue.put(CloseFrame(code, reason))

    def _enqueue_ping_frame(self):
        """ Put a ping frame in the outgoing frame queue. """
        self._outgoing_frame_queue.put(Frame(Opcode.PING))

    def _enqueue_pong_frame(self, payload):
        """ Put a pong frame in the outgoing frame queue. """
        self._outgoing_frame_queue.put(Frame(Opcode.PONG, payload))

    def _terminate(self):
        """ Close the underlying TCP socket. """
        with suppress(OSError, TimeoutError):
            self._socket.shutdown(socket.SHUT_WR)
            # Call recv until obtaining a return value of 0 indicating
            # the other end has performed an orderly shutdown. A timeout
            # is set to ensure the connection will be closed even if
            # the other end does not close the socket properly.
            self._socket.settimeout(1)
            while self._socket.recv(4096):
                pass
        self._selector.unregister(self._socket)
        self._selector.close()
        self._socket.close()
        self.state = ConnectionState.CLOSED
        self._trigger_lifecycle_event(LifecycleEvent.CLOSE)

    def _handle_control_frame(self, frame):
        if frame.opcode is Opcode.PING:
            self._enqueue_pong_frame(frame.payload)
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
                self._enqueue_close_frame(code, reason)
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
        elif isinstance(exc, RateLimitExceededException):
            code = CloseCode.TRY_LATER
        if code is CloseCode.SERVER_ERROR:
            reason = None
            _logger.error(exc, exc_info=True)
        self.disconnect(code, reason)

    def _limit_rate(self):
        """
        This method is a simple rate limiter designed not to allow
        more than one request by `RL_DELAY` seconds. `RL_BURST` specify
        how many requests can be made in excess of the given rate at the
        begining. When requests are received too fast, raises the
        `RateLimitExceededException`.
        """
        now = time.time()
        if len(self._incoming_frame_timestamps) >= type(self).RL_BURST:
            elapsed_time = now - self._incoming_frame_timestamps[0]
            if elapsed_time < type(self).RL_DELAY * type(self).RL_BURST:
                raise RateLimitExceededException()
        self._incoming_frame_timestamps.append(now)

    @classmethod
    def _kick_all(cls):
        """ Disconnect all the websocket instances. """
        for websocket in cls._instances:
            if websocket.state is ConnectionState.OPEN:
                websocket.disconnect(CloseCode.GOING_AWAY)

    def _trigger_lifecycle_event(self, event_type):
        """
        Trigger a lifecycle event that is, call every function
        registered for this event type. Every callback is given both the
        environment and the related websocket.
        """
        registry = Registry(self._session.db)
        with closing(registry.cursor()) as cr:
            env = api.Environment(cr, self._session.uid, self._session.context)
            for callback in type(self)._event_callbacks[event_type]:
                try:
                    service_model.retrying(functools.partial(callback, env, self), env)
                except Exception:
                    _logger.warning(
                        'Error during Websocket %s callback',
                        LifecycleEvent(event_type).name,
                        exc_info=True
                    )


class TimeoutReason(IntEnum):
    KEEP_ALIVE = 0
    NO_RESPONSE = 1


class TimeoutManager:
    """
    This class handles the Websocket timeouts. If no response to a
    PING/CLOSE frame is received after `TIMEOUT` seconds or if the
    connection is opened for more than `KEEP_ALIVE_TIMEOUT` seconds, the
    connection is considered to have timed out. To determine if the
    connection has timed out, use the `has_timed_out` method.
    """
    TIMEOUT = 15
    # Timeout specifying how many seconds the connection should be kept
    # alive.
    KEEP_ALIVE_TIMEOUT = int(config['websocket_keep_alive_timeout'])

    def __init__(self):
        super().__init__()
        self._awaited_opcode = None
        # Time in which the connection was opened.
        self._opened_at = time.time()
        self.timeout_reason = None
        # Start time recorded when we started awaiting an answer to a
        # PING/CLOSE frame.
        self._waiting_start_time = None

    def acknowledge_frame_receipt(self, frame):
        if self._awaited_opcode is frame.opcode:
            self._awaited_opcode = None
            self._waiting_start_time = None

    def acknowledge_frame_sent(self, frame):
        """
        Acknowledge a frame was sent. If this frame is a PING/CLOSE
        frame, start waiting for an answer.
        """
        if self.has_timed_out():
            return
        if frame.opcode is Opcode.PING:
            self._awaited_opcode = Opcode.PONG
        elif frame.opcode is Opcode.CLOSE:
            self._awaited_opcode = Opcode.CLOSE
        if self._awaited_opcode is not None:
            self._waiting_start_time = time.time()

    def has_timed_out(self):
        """
        Determine whether the connection has timed out or not. The
        connection times out when the answer to a CLOSE/PING frame
        is not received within `TIMEOUT` seconds or if the connection
        is opened for more than `KEEP_ALIVE_TIMEOUT` seconds.
        """
        now = time.time()
        if now - self._opened_at >= type(self).KEEP_ALIVE_TIMEOUT:
            self.timeout_reason = TimeoutReason.KEEP_ALIVE
            return True
        if self._awaited_opcode and now - self._waiting_start_time >= type(self).TIMEOUT:
            self.timeout_reason = TimeoutReason.NO_RESPONSE
            return True
        return False


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
            jsonrequest = json.loads(message)
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
            self.registry.check_signaling()
        except (
            AttributeError, psycopg2.OperationalError, psycopg2.ProgrammingError
        ) as exc:
            raise InvalidDatabaseException() from exc

        with closing(self.registry.cursor()) as cr:
            self.env = api.Environment(cr, self.session.uid, self.session.context)
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
        ir_websocket = self.env['ir.websocket']
        ir_websocket._authenticate()
        if event_name == 'subscribe':
            ir_websocket._subscribe(data)
        if event_name == 'update_presence':
            ir_websocket._update_bus_presence(data)

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


class WebsocketConnectionHandler:
    SUPPORTED_VERSIONS = {'13'}
    # Given by the RFC in order to generate Sec-WebSocket-Accept from
    # Sec-WebSocket-Key value.
    _HANDSHAKE_GUID = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
    _REQUIRED_HANDSHAKE_HEADERS = {
        'connection', 'host', 'sec-websocket-key',
        'sec-websocket-version', 'upgrade',
    }

    @classmethod
    def open_connection(cls, request):
        """
        Open a websocket connection if the handshake is successfull.
        :return: Response indicating the server performed a connection
        upgrade.
        :raise: UpgradeRequired if there is no intersection between the
        versions the client supports and those we support.
        :raise: BadRequest if the handshake data is incorrect.
        """
        response = cls._get_handshake_response(request.httprequest.headers)
        response.call_on_close(functools.partial(
            cls._serve_forever,
            Websocket(request.httprequest.environ['socket'], request.session),
            request.db,
            request.httprequest
        ))
        # Force save the session. Session must be persisted to handle
        # WebSocket authentication.
        request.session.is_dirty = True
        return response

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
            'Sec-WebSocket-Accept': accept_header,
        })

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
    def _serve_forever(cls, websocket, db, httprequest):
        """
        Process incoming messages and dispatch them to the application.
        """
        current_thread = threading.current_thread()
        current_thread.type = 'websocket'
        for message in websocket.get_messages():
            with WebsocketRequest(db, httprequest, websocket) as req:
                try:
                    req.serve_websocket_message(message)
                except SessionExpiredException:
                    websocket.disconnect(CloseCode.SESSION_EXPIRED)
                except Exception:
                    _logger.exception("Exception occurred during websocket request handling")


CommonServer.on_stop(Websocket._kick_all)
