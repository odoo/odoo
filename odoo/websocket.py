import base64
import hashlib
import json
import logging
import socket
import struct
import time
from dataclasses import dataclass
from enum import Enum, IntEnum
from itertools import cycle
from queue import Empty, Queue
from threading import Event, Thread, Timer, current_thread

import gevent.monkey
from werkzeug.exceptions import NotFound

from . import api
from .websocket_exceptions import (InvalidCloseCodeException,
                                  InvalidFrameException,
                                  InvalidHeaderValueException,
                                  InvalidJSONFormatException,
                                  InvalidVersionException,
                                  MissingOrEmptyHeaderException,
                                  ProtocolErrorException, WebSocketException)

gevent.monkey.patch_all()
_logger = logging.getLogger(__name__)


# ------------------------------------------------------
# HTTP OPENING HANDSHAKE
# ------------------------------------------------------

class WSConnectionServer:
    def __init__(self, request, websocket_version):
        self._websocket_version = websocket_version
        self._request = request.httprequest
        self._headers = {key.lower(): value for key, value in self._request.headers}
        self._required_headers = ["connection", "upgrade", "host", "sec-websocket-key", "sec-websocket-version"]
        self._PROTOCOL_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
        self._key = ""

    def connect(self):
        """
            Handles verification of the handshake as well as constructing the answer.
            :raise InvalidHandshakeException: if some of the mandatory headers are missing or incorrect
            :return bytes: response to send through the socket
        """
        self._ensure_handshake_validity()
        headers = self._get_handshake_headers()
        response = "HTTP/1.1 101 SWITCHING PROTOCOLS"
        response = "%s\r\n%s\r\n" % (response, ''.join('%s: %s\r\n' % (k, v) for k, v in headers.items()))
        return bytes(response, 'utf-8')

    def _ensure_handshake_validity(self):
        """
            Validates handshake as described in section 4.2.1. Upgrade as well as Connection headers have
            already been checked by `WebSocket.is_websocket_request` method.
            :raise InvalidHandshakeException: custom exceptions (subclassing InvalidHandshakeException) according to what went wrong
        """
        missing_or_empty_headers = [header for header in self._required_headers if
                                    header not in self._headers.keys() or not self._headers[header]]
        if missing_or_empty_headers:
            raise MissingOrEmptyHeaderException(missing_or_empty_headers)
        if self._headers['upgrade'].lower() != 'websocket' or 'upgrade' not in self._headers['connection'].lower():
            raise InvalidHeaderValueException('Upgrade, Connection', 'should be websocket and upgrade, respectively')

        self._key = self._headers["sec-websocket-key"]
        try:
            decoded_key = base64.b64decode(self._key)
        except ValueError:
            raise InvalidHeaderValueException("Sec-WebSocket-Key", "should be b64 encoded")
        if len(decoded_key) != 16:
            raise InvalidHeaderValueException("Sec-WebSocket-Key", "should be of length 16 once decoded")

        try:
            version = int(self._headers["sec-websocket-version"])
        except ValueError:
            raise InvalidHeaderValueException("Sec-WebSocket-Version", self._headers["sec-websocket-version"])
        if version != self._websocket_version:
            raise InvalidVersionException(version, self._websocket_version)

    def _compute_accept_header(self):
        """ Compute Sec-WebSocket-Accept header """
        digest = hashlib.sha1((self._key + self._PROTOCOL_GUID).encode()).digest()
        result = base64.b64encode(digest).decode('utf-8')
        return result

    def _get_handshake_headers(self):
        return {
            "Upgrade": "websocket",
            "Connection": "Upgrade",
            "Sec-WebSocket-Accept": self._compute_accept_header(),
        }


# ------------------------------------------------------
# WEBSOCKETS
# ------------------------------------------------------

class State(Enum):
    CONNECTING, OPEN, CLOSING, CLOSED = range(4)


class PongState(Enum):
    WAITING, OK = range(2)


class WebSocket:
    def __init__(self, request, dispatch):
        self.state = State.CLOSED
        self.pong_state = PongState.OK
        self._request = request
        self._version = 13
        self._socket = current_thread()._args[0]
        self._reader = FrameReader(self._socket, self._handle_control_frame, self._handle_exception)
        self._notification_reader = NotificationReader(request.db, [], dispatch)
        # TODO do this in websocket_dispatch
        current_thread().type = 'websocket'

    # ------------------------------------------------------
    # PUBLIC METHODS
    # ------------------------------------------------------

    def connect(self):
        """
            :raise: WebSocketException: if request doesn't match expectations in order for `http.py`
            to send a response and for the thread to end
            A 426 response with a Sec-WebSocket-Version header indicating which version is supported
            by the server should be sent in case of `InvalidVersionException`.
            A 400 response should be sent overwise.
        """
        self.state = State.CONNECTING
        try:
            response = WSConnectionServer(self._request, self._version).connect()
            self.state = State.OPEN
            self._reader.start()
            self._notification_reader.start()
            self._socket.sendall(response)
            Thread(target=self._heartbeat).start()
        except WebSocketException as exc:
            self.state = State.CLOSED
            raise exc

    def disconnect(self):
        self._write_close(1000)

    def read(self):
        """
            Get oldest frame and returns it's data, parsed. If no frame are yet to be read, wait until one is available.
            Stops when WebSocket is closed.
            :rtype: `bytes` or `str` or `dict`
        """
        while True:
            try:
                yield self._reader.read(timeout=1)
            except Empty:
                if self.state is State.CLOSED:
                    break
            except Exception as exc:
                self._handle_exception(exc)

    def read_notifications(self):
        """ Get bus notifications from `NotificationReader` """
        while True:
            try:
                yield self._notification_reader.read(timeout=1)
            except Empty:
                if self.state is State.CLOSED:
                    break

    def write(self, data):
        """
            :param data: data to send
            :type data: `bytes` or `str` or `dict`
        """
        opcode = Opcode.BINARY
        if not isinstance(data, bytes):
            opcode = json.dumps(data)
            opcode = Opcode.TEXT
        self._write_frame(Frame(opcode, data))

    def subscribe(self, channels):
        """ Subscribe to a list of channels, overwriting the current list """
        self._notification_reader.channels = channels

    # ------------------------------------------------------
    # PRIVATE METHODS
    # ------------------------------------------------------

    def _write_frame(self, frame):
        try:
            if not isinstance(frame, Frame):
                raise TypeError("_write_frame method is expecting Frame object to be given as parameter")
            if self.state is not State.OPEN and frame.opcode in DATA_OPCODES:
                raise RuntimeError("Can't send data frame if state is not open. Current state: %s" % self.state)
            self._socket.sendall(frame.serialize())
        except Exception as exc:
            self._handle_exception(exc)

    def _write_close(self, code, reason=None):
        """ If after 5 seconds socket is still not closed it means we have not received a close frame in response. Let's fail the connection. """
        try:
            self.state = State.CLOSING
            self._write_frame(Frame(Opcode.CLOSE, Close(code, reason).serialize()))
            Timer(5, lambda: self._fail(1006, 'No close frame received') if self.state is not State.CLOSED else None).start()
        except Exception as exc:
            self._handle_exception(exc)

    def _heartbeat(self):
        """
            Sends a ping frame every 50s since client closes connection after 1mn inactivity.
            If after 10 seconds a pong frame has not been received, then the other end is probably not listening anymore: let's close the connection.
            This method will be launch after a successfull `connect` in a seperate greenlet.
        """
        while self.state is State.OPEN:
            self.pong_status = PongState.WAITING
            self._write_frame(Frame(Opcode.PING))
            Timer(10, lambda: self._fail(1006, 'No pong frame received') if self.pong_state is not PongState.OK else None).start()
            time.sleep(50)

    def _fail(self, code, reason):
        """
            Fails a WebSocket connection. As for RFC6455 7.1.7, we MUST stop processing frames immediately after fail.
            In case of 1011 code, let's log the reason and set is as `None` in order to hide implementation details to the client.
        """
        _logger.warning('%s %s%s', code, CLOSE_CODES.get(code), '' if not reason else f': {reason}')
        if code == 1011:
            reason = None
        if code != 1006:
            self._write_close(code, reason)
        self._close_socket()

    def _close_socket(self):
        try:
            self._socket.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        self._socket.close()
        self._reader.stop()
        self._notification_reader.stop()
        self.state = State.CLOSED

    def _handle_control_frame(self, frame):
        try:
            if frame.opcode is Opcode.CLOSE:
                if self.state is State.OPEN:
                    close = Close.deserialize(frame.data)
                    self._write_close(close.code, close.reason)
                self._close_socket()
            elif frame.opcode is Opcode.PING:
                self._write_frame(Frame(Opcode.PONG, frame.data))
            elif frame.opcode is Opcode.PONG:
                self.pong_state = PongState.OK
        except Exception as exc:
            self._handle_exception(exc)

    def _handle_exception(self, exc):
        """ Find out which fail code we should send according to given exception and call `self._fail` """
        if self.state is State.OPEN:
            code, reason = 1011, str(exc)
            if isinstance(exc, (EOFError, ConnectionResetError, OSError)):
                if not isinstance(exc, OSError) or exc.errno == 107:
                    code = 1006
            elif isinstance(exc, (ProtocolErrorException, InvalidCloseCodeException, InvalidJSONFormatException)):
                code = 1002
            elif isinstance(exc, InvalidFrameException):
                code = 1007
            elif isinstance(exc, NotFound):
                code, reason = 1003, 'Given channel matches no route'
            self._fail(code, reason)

# ------------------------------------------------------
# READERS
# ------------------------------------------------------

class FrameReader(Thread):
    """
        Process incoming websocket data frames and make them available via `self.read` method,
        Relay control frames to `self.frame_handler` in order to handle them as soon as possible.
    """
    def __init__(self, socket, frame_handler, exc_handler):
        Thread.__init__(self)
        self._socket = socket
        self._exit = False
        self._exc_handler = exc_handler
        self._frame_handler = frame_handler
        self._frames = Queue()

    def read(self, timeout):
        """
            Read frames from `self.frames` queue in a FIFO fashion and parse it's data.
            :rtype: `bytes` or `str` or `dict
        """
        frame = self._frames.get(timeout=timeout)
        data = frame.data
        if frame.opcode is Opcode.TEXT:
            try:
                data = data.decode("utf-8")
                data = json.loads(data)
                if not all(key in data for key in ('channel', 'message')):
                    raise InvalidJSONFormatException()
            except UnicodeDecodeError as exc:
                raise InvalidFrameException(exc)
            except json.JSONDecodeError:
                pass
        return data

    def run(self):
        """
            Receive and deserialize frames as they come and add them to `self.frames` queue.
            Concatenate payload from fragmented frames until a full frame is received.
        """
        concatenated_data = []
        initial_frame = None
        try:
            while not self._exit:
                frame = Frame.deserialize(self._read_bytes)
                if frame.opcode is Opcode.CONTINUE and not concatenated_data:
                    raise ProtocolErrorException('Unexpected continuation frame')
                if frame.opcode in CTRL_OPCODES:
                    self._frame_handler(frame)
                    continue
                if frame.opcode in DATA_OPCODES:
                    if concatenated_data:
                        raise ProtocolErrorException('Expected continuation frame. Received: %s' % frame.opcode)
                    initial_frame = frame
                concatenated_data.append(frame.data)
                if frame.fin and not self._exit:
                    initial_frame.data = b''.join(concatenated_data)
                    self._frames.put(initial_frame)
                    concatenated_data = []
                    initial_frame = None
        except Exception as exc:
            self._exc_handler(exc)

    def _read_bytes(self, required_bytes):
        """
            Used during deserialization to pull required bytes from the socket.
            This solves the two following issues:
                - socket.recv is expecting a fixed number of bytes.
                - TCP does not guarantee that 2 frames won't be received by one recv().
            :type require_bytes: int
        """
        data = []
        actual_bytes = 0
        while actual_bytes < required_bytes and not self._exit:
            byte = self._socket.recv(required_bytes - actual_bytes)
            if not byte:
                raise EOFError()
            data.append(byte)
            actual_bytes += len(byte)
        return b''.join(data)

    def stop(self):
        self._exit = True

class NotificationReader(Thread):
    """ Listen to bus notification according to channels the user has subscribed to.
        Stay idle until `self._channels` is not empty.
    """
    def __init__(self, db, channels, dispatch):
        super().__init__()
        self._dispatch = dispatch
        self._db = db
        self._channels = channels
        self._notifications = Queue()
        self._active_event = Event()
        self._exit = False

    @property
    def channels(self):
        return self._channels

    @channels.setter
    def channels(self, channels):
        # After json_dump/load, channels will not be tuple anymore. Let's morph tuple channels into lists
        # In order to ease notification's channel membership test against self._channels.
        self._channels = [list(chan) if isinstance(chan, tuple) else chan for chan in channels]
        if channels:
            self._active_event.set()
        else:
            self._active_event.clear()

    def run(self):
        with api.Environment.manage():
            last = 0
            while not self._exit:
                self._active_event.wait()
                notifs = self._dispatch.poll(self._db, self._channels, last, timeout=1)
                if notifs and not self._exit:
                    last = notifs[-1]['id']
                    # Channels might have change between poll and notifications retrieving, let's ensure
                    # We still want to get those notifications before pushing it in the queue.
                    notifs = [notif for notif in notifs if notif['channel'] in self.channels]
                    if notifs:
                        self._notifications.put(notifs)

    def read(self, timeout):
        self._active_event.wait()
        return self._notifications.get(timeout=timeout)

    def stop(self):
        self._exit = True
        self._active_event.set()


# ------------------------------------------------------
# FRAMES
# ------------------------------------------------------

class Opcode(IntEnum):
    CONTINUE = 0x00
    TEXT = 0x01
    BINARY = 0x02
    CLOSE = 0x08
    PING = 0x09
    PONG = 0x0A


DATA_OPCODES = {Opcode.TEXT, Opcode.BINARY}
CTRL_OPCODES = {Opcode.CLOSE, Opcode.PING, Opcode.PONG}
CLOSE_CODES = {
    1000: "Normal Closure",
    1001: "Going Away",
    1002: "Protocol Error",
    1003: "Incorrect data",
    1007: "Inconsistent Data",
    1008: "Message Violating Policy",
    1009: "Message Too Big",
    1010: "Extension Negotiation Failed",
    1011: "Unexpected Server Error",
    1012: "Restart",
    1013: "Try Later",
    1014: "Bad Gateway",
}


@dataclass
class Frame:
    """ This class represents a WebSocket Frame and provides utility to serialize/deserialize it """
    opcode: Opcode
    data: bytes = b''
    fin: bool = True
    rsv1: bool = False
    rsv2: bool = False
    rsv3: bool = False

    @classmethod
    def deserialize(cls, read_bytes):
        """
            see: https://datatracker.ietf.org/doc/html/rfc6455#5.2
            :raise ProtocolErrorException: is the frame format doesn't match the expectations
        """
        try:
            data = read_bytes(2)
            first_head, second_head = struct.unpack("!BB", data)
            fin = cls.is_bit_set(first_head, 0)
            rsv1 = cls.is_bit_set(first_head, 1)
            rsv2 = cls.is_bit_set(first_head, 2)
            rsv3 = cls.is_bit_set(first_head, 3)
            opcode = Opcode(first_head & 0b00001111)
            payload_length = second_head & 0b01111111

            if rsv1 or rsv2 or rsv3:
                raise ProtocolErrorException('Reserved bits must be unset')
            if not cls.is_bit_set(second_head, 0):
                raise ProtocolErrorException('Frame must be masked')
            if opcode in CTRL_OPCODES:
                if not fin:
                    raise ProtocolErrorException('Control frames cannot be fragmented')
                if payload_length > 125:
                    raise ProtocolErrorException('Control frames must have a payload length smaller than 126')

            if payload_length == 126:
                data = read_bytes(2)
                payload_length = struct.unpack("!H", data)[0]
            elif payload_length == 127:
                data = read_bytes(8)
                payload_length = struct.unpack("!Q", data)[0]
            masks = read_bytes(4)
            data = [byte ^ mask for byte, mask in zip(read_bytes(payload_length), cycle(masks))]
            return Frame(opcode, bytes(data), fin, rsv1, rsv2, rsv3)
        except (ValueError, struct.error) as exc:
            msg = exc if isinstance(exc, ValueError) else 'Malformed frame, not enough bytes'
            raise ProtocolErrorException(msg)

    def serialize(self):
        """
            During serialization we need either:
                - 7 bits to encode payload length if it's between 0-125
                - 2 bytes to encode payload length if it's between 126-65535
                - 8 bytes for longer payloads
            :raise: TypeError if `self.data` is neither of type `str` nor `bytes` nor `dict`
        """
        self.process_data()
        output = []
        first_head = (
            (0b10000000 if self.fin else 0)
            | (0b01000000 if self.rsv1 else 0)
            | (0b00100000 if self.rsv2 else 0)
            | (0b00010000 if self.rsv3 else 0)
            | self.opcode
        )
        second_head = 0
        payload_length = len(self.data)
        if payload_length < 126:
            output.append(struct.pack('!BB', first_head, second_head | payload_length))
        elif payload_length < 65536:
            output.append(struct.pack('!BBH', first_head, second_head | 126, payload_length))
        else:
            output.append(struct.pack('!BBQ', first_head, second_head | 127, payload_length))
        output.append(self.data)
        return b''.join(output)

    def process_data(self):
        """
            Transform frame data's to bytes in order to send it through socket.
            :raise TypeError: if `self.data` is neither of type `str` nor `bytes` nor `dict`
            :raise UnicodeEncodeError: if `self.data` is a string that contains invalid UTF-8 chars
            :raise ValueError: if `self.data` length is bigger than 125 and it's a control frame
        """
        if len(self.data) > 125 and self.opcode in CTRL_OPCODES:
            raise ValueError('Control frame must have a payload length smaller than 126')
        if isinstance(self.data, str):
            self.data = self.data.encode('utf-8')
        elif not isinstance(self.data, bytes):
            self.data = json.dumps(self.data).encode('utf-8')

    @classmethod
    def is_bit_set(cls, byte, n):
        """ Check whether `n`th bit (starting from the left) of `byte` is set or not """
        return True if byte & (1 << (7 - n)) else False


class Close:
    """  Class helping with close frames' data serialization/deserialization """

    def __init__(self, code, reason=None):
        self.code = code
        self.reason = reason

    @classmethod
    def deserialize(cls, buffer):
        try:
            if len(buffer) >= 2:
                code = struct.unpack('!H', buffer[:2])[0]
                reason = buffer[2:].decode('utf-8')
                close = Close(code, reason)
            elif not buffer:
                close = Close(1000)
            else:
                raise ProtocolErrorException('Malformed closing frame')
            close._ensure_validity()
            return close
        except UnicodeDecodeError as exc:
            raise InvalidFrameException(str(exc))

    def serialize(self):
        self._ensure_validity()
        self.reason = self.reason if self.reason is not None else CLOSE_CODES.get(self.code, '')
        output = struct.pack('!H', self.code) + self.reason.encode('utf-8')
        return output

    def _ensure_validity(self):
        is_valid_close_code = self.code in CLOSE_CODES.keys() or 3000 <= self.code <= 4999
        if not is_valid_close_code:
            raise InvalidCloseCodeException(self.code)
