class WebSocketException(Exception):
    """ Base class for all websockets exceptions """

# ------------------------------------------------------
# HANDSHAKE ERRORS
# ------------------------------------------------------

class InvalidHandshakeException(WebSocketException):
    """ Raised when upgrade to websocket protocol fails """

class MissingOrEmptyHeaderException(InvalidHandshakeException):
    """ Raised when one or several mandatory headers are missing """

    def __init__(self, missing_headers):
        super().__init__(
            '%s header(s) %s empty or missing' % (', '.join(missing_headers), 'are' if len(missing_headers) > 1 else 'is'))

class InvalidHeaderValueException(InvalidHandshakeException):
    """ Raised when an header value doesn't match expected format """

    def __init__(self, header, cause):
        super().__init__('Header %s does not match expected format. Cause: %s' % (header, cause))


class InvalidHTTPMethodException(InvalidHandshakeException):
    """ Raised when handshake request is not done with GET method """

    def __init__(self):
        super().__init__("Only GET method is valid for websocket handshakes")


class InvalidVersionException(InvalidHandshakeException):
    """ Raised when requested websocket version is not the most recent one """

    def __init__(self, actual_version, expected_version):
        super().__init__('WebSocket version should be %s, found: %s' % (expected_version, actual_version))

# ------------------------------------------------------
# FRAME ERRORS
# ------------------------------------------------------

class InvalidCloseCodeException(WebSocketException):
    def __init__(self, code):
        super().__init__('Invalid close code: %s' % code)


class ProtocolErrorException(WebSocketException):
    """ Raised when a frame format doesn't match expectations """


class NoCloseFrameReceivedException(WebSocketException):
    """ Raised when a close frame has not been received after we sent one """
    def __init__(self) -> None:
        super().__init__("Socket closed without any close frame")

class InvalidFrameException(WebSocketException):
    """
        Raised when data contained in a frame doesn't match given opcode
        eg. binary or invalid utf-8 in text frame
    """

class InvalidJSONFormatException(WebSocketException):
    """
        Raised when received JSON is missing some of the mandatory keys
        We're expecting 2 keys : channel, message
    """
    def __init__(self) -> None:
        super().__init__('Invalid JSON format. Excpecting channel and message keys.')
