from enum import IntEnum


class WebsocketException(Exception):
    """Base class for all websockets exceptions."""


class ConnectionClosed(WebsocketException):
    """
    Raised when the other end closes the socket without performing the closing
    handshake.
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
    """Raised when an operation is forbidden in the current state."""


class InvalidWebsocketRequest(WebsocketException):
    """Raised when a websocket request is invalid (format, wrong args)."""


class PayloadTooLargeException(WebsocketException):
    """Raised when a websocket message is too large."""


class ProtocolError(WebsocketException):
    """Raised when a frame format doesn't match expectations."""


class RateLimitExceededException(Exception):
    """Raised when a client exceeds the number of request in a given time."""


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
