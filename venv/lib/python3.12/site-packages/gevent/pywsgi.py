# Copyright (c) 2005-2009, eventlet contributors
# Copyright (c) 2009-2018, gevent contributors
"""
A pure-Python, gevent-friendly WSGI server implementing HTTP/1.1.

The server is provided in :class:`WSGIServer`, but most of the actual
WSGI work is handled by :class:`WSGIHandler` --- a new instance is
created for each request. The server can be customized to use
different subclasses of :class:`WSGIHandler`.

.. important::

   This server is intended primarily for development and testing, and
   secondarily for other "safe" scenarios where it will not be exposed to
   potentially malicious input. The code has not been security audited,
   and is not intended for direct exposure to the public Internet. For production
   usage on the Internet, either choose a production-strength server such as
   gunicorn, or put a reverse proxy between gevent and the Internet.

.. versionchanged:: 23.9.0

   Complies more closely with the HTTP specification for chunked transfer encoding.
   In particular, we are much stricter about trailers, and trailers that
   are invalid (too long or featuring disallowed characters) forcibly close
   the connection to the client *after* the results have been sent.

   Trailers otherwise continue to be ignored and are not available to the
   WSGI application.

"""
from __future__ import absolute_import

# FIXME: Can we refactor to make smallor?
# pylint:disable=too-many-lines

import errno
from io import BytesIO
import string
import sys
import time
import traceback
from datetime import datetime

from urllib.parse import unquote

from gevent import socket
import gevent
from gevent.server import StreamServer
from gevent.hub import GreenletExit
from gevent._compat import reraise

from functools import partial
unquote_latin1 = partial(unquote, encoding='latin-1')

_no_undoc_members = True # Don't put undocumented things into sphinx

__all__ = [
    'WSGIServer',
    'WSGIHandler',
    'LoggingLogAdapter',
    'Environ',
    'SecureEnviron',
    'WSGISecureEnviron',
]


MAX_REQUEST_LINE = 8192
# Weekday and month names for HTTP date/time formatting; always English!
_WEEKDAYNAME = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
_MONTHNAME = (None,  # Dummy so we can use 1-based month numbers
              "Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")

# The contents of the "HEX" grammar rule for HTTP, upper and lowercase A-F plus digits,
# in byte form for comparing to the network.
_HEX = string.hexdigits.encode('ascii')

# The characters allowed in "token" rules.

# token          = 1*tchar
# tchar          = "!" / "#" / "$" / "%" / "&" / "'" / "*"
#                / "+" / "-" / "." / "^" / "_" / "`" / "|" / "~"
#                / DIGIT / ALPHA
#                ; any VCHAR, except delimiters
# ALPHA          =  %x41-5A / %x61-7A   ; A-Z / a-z
_ALLOWED_TOKEN_CHARS = frozenset(
    # Remember we have to be careful because bytestrings
    # inexplicably iterate as integers, which are not equal to bytes.

    # explicit chars then DIGIT
    (c.encode('ascii') for c in "!#$%&'*+-.^_`|~0123456789")
    # Then we add ALPHA
) | {c.encode('ascii') for c in string.ascii_letters}
assert b'A' in _ALLOWED_TOKEN_CHARS


# Errors
_ERRORS = {}
_INTERNAL_ERROR_STATUS = '500 Internal Server Error'
_INTERNAL_ERROR_BODY = b'Internal Server Error'
_INTERNAL_ERROR_HEADERS = (
    ('Content-Type', 'text/plain'),
    ('Connection', 'close'),
    ('Content-Length', str(len(_INTERNAL_ERROR_BODY)))
)
_ERRORS[500] = (_INTERNAL_ERROR_STATUS, _INTERNAL_ERROR_HEADERS, _INTERNAL_ERROR_BODY)

_BAD_REQUEST_STATUS = '400 Bad Request'
_BAD_REQUEST_BODY = ''
_BAD_REQUEST_HEADERS = (
    ('Content-Type', 'text/plain'),
    ('Connection', 'close'),
    ('Content-Length', str(len(_BAD_REQUEST_BODY)))
)
_ERRORS[400] = (_BAD_REQUEST_STATUS, _BAD_REQUEST_HEADERS, _BAD_REQUEST_BODY)

_REQUEST_TOO_LONG_RESPONSE = b"HTTP/1.1 414 Request URI Too Long\r\nConnection: close\r\nContent-length: 0\r\n\r\n"
_BAD_REQUEST_RESPONSE = b"HTTP/1.1 400 Bad Request\r\nConnection: close\r\nContent-length: 0\r\n\r\n"
_CONTINUE_RESPONSE = b"HTTP/1.1 100 Continue\r\n\r\n"


def format_date_time(timestamp):
    # Return a byte-string of the date and time in HTTP format
    # .. versionchanged:: 1.1b5
    #  Return a byte string, not a native string
    year, month, day, hh, mm, ss, wd, _y, _z = time.gmtime(timestamp)
    value = "%s, %02d %3s %4d %02d:%02d:%02d GMT" % (_WEEKDAYNAME[wd], day, _MONTHNAME[month], year, hh, mm, ss)
    value = value.encode("latin-1")
    return value


class _InvalidClientInput(IOError):
    # Internal exception raised by Input indicating that the client
    # sent invalid data at the lowest level of the stream. The result
    # *should* be a HTTP 400 error.
    pass


class _InvalidClientRequest(ValueError):
    # Internal exception raised by WSGIHandler.read_request indicating
    # that the client sent an HTTP request that cannot be parsed
    # (e.g., invalid grammar). The result *should* be an HTTP 400
    # error. It must have exactly one argument, the fully formatted
    # error string.

    def __init__(self, message):
        ValueError.__init__(self, message)
        self.formatted_message = message


class Input(object):

    __slots__ = ('rfile', 'content_length', 'socket', 'position',
                 'chunked_input', 'chunk_length', '_chunked_input_error')

    def __init__(self, rfile, content_length, socket=None, chunked_input=False):
        # pylint:disable=redefined-outer-name
        self.rfile = rfile
        self.content_length = content_length
        self.socket = socket
        self.position = 0
        self.chunked_input = chunked_input
        self.chunk_length = -1
        self._chunked_input_error = False

    def _discard(self):
        if self._chunked_input_error:
            # We are in an unknown state, so we can't necessarily discard
            # the body (e.g., if the client keeps the socket open, we could hang
            # here forever).
            # In this case, we've raised an exception and the user of this object
            # is going to close the socket, so we don't have to discard
            return

        if self.socket is None and (self.position < (self.content_length or 0) or self.chunked_input):
            # ## Read and discard body
            while 1:
                d = self.read(16384)
                if not d:
                    break

    def _send_100_continue(self):
        if self.socket is not None:
            self.socket.sendall(_CONTINUE_RESPONSE)
            self.socket = None

    def _do_read(self, length=None, use_readline=False):
        if use_readline:
            reader = self.rfile.readline
        else:
            reader = self.rfile.read
        content_length = self.content_length
        if content_length is None:
            # Either Content-Length or "Transfer-Encoding: chunked" must be present in a request with a body
            # if it was chunked, then this function would have not been called
            return b''

        self._send_100_continue()
        left = content_length - self.position
        if length is None:
            length = left
        elif length > left:
            length = left
        if not length:
            return b''

        # On Python 2, self.rfile is usually socket.makefile(), which
        # uses cStringIO.StringIO. If *length* is greater than the C
        # sizeof(int) (typically 32 bits signed), parsing the argument to
        # readline raises OverflowError. StringIO.read(), OTOH, uses
        # PySize_t, typically a long (64 bits). In a bare readline()
        # case, because the header lines we're trying to read with
        # readline are typically expected to be small, we can correct
        # that failure by simply doing a smaller call to readline and
        # appending; failures in read we let propagate.
        try:
            read = reader(length)
        except OverflowError:
            if not use_readline:
                # Expecting to read more than 64 bits of data. Ouch!
                raise
            # We could loop on calls to smaller readline(), appending them
            # until we actually get a newline. For uses in this module,
            # we expect the actual length to be small, but WSGI applications
            # are allowed to pass in an arbitrary length. (This loop isn't optimal,
            # but even client applications *probably* have short lines.)
            read = b''
            while len(read) < length and not read.endswith(b'\n'):
                read += reader(MAX_REQUEST_LINE)

        self.position += len(read)
        if len(read) < length:
            if (use_readline and not read.endswith(b"\n")) or not use_readline:
                raise IOError("unexpected end of file while reading request at position %s" % (self.position,))

        return read

    def __read_chunk_length(self, rfile):
        # Read and return the next integer chunk length. If no
        # chunk length can be read, raises _InvalidClientInput.

        # Here's the production for a chunk (actually the whole body):
        # (https://www.rfc-editor.org/rfc/rfc7230#section-4.1)

        # chunked-body   = *chunk
        #                  last-chunk
        #                  trailer-part
        #                  CRLF
        #
        # chunk          = chunk-size [ chunk-ext ] CRLF
        #                  chunk-data CRLF
        # chunk-size     = 1*HEXDIG
        # last-chunk     = 1*("0") [ chunk-ext ] CRLF
        # trailer-part   = *( header-field CRLF )
        # chunk-data     = 1*OCTET ; a sequence of chunk-size octets
        #
        # chunk-ext      = *( ";" chunk-ext-name [ "=" chunk-ext-val ] )
        #
        # chunk-ext-name = token
        # chunk-ext-val  = token / quoted-string

        # To cope with malicious or broken clients that fail to send
        # valid chunk lines, the strategy is to read character by
        # character until we either reach a ; or newline. If at any
        # time we read a non-HEX digit, we bail. If we hit a ;,
        # indicating an chunk-extension, we'll read up to the next
        # MAX_REQUEST_LINE characters ("A server ought to limit the
        # total length of chunk extensions received") looking for the
        # CRLF, and if we don't find it, we bail. If we read more than
        # 16 hex characters, (the number needed to represent a 64-bit
        # chunk size), we bail (this protects us from a client that
        # sends an infinite stream of `F`, for example).

        buf = BytesIO()
        while 1:
            char = rfile.read(1)
            if not char:
                self._chunked_input_error = True
                raise _InvalidClientInput("EOF before chunk end reached")

            if char in (
                b'\r', # Beginning EOL
                b';', # Beginning extension
            ):
                break

            if char not in _HEX: # Invalid data.
                self._chunked_input_error = True
                raise _InvalidClientInput("Non-hex data", char)

            buf.write(char)

            if buf.tell() > 16: # Too many hex bytes
                self._chunked_input_error = True
                raise _InvalidClientInput("Chunk-size too large.")

        if char == b';':
            i = 0
            while i < MAX_REQUEST_LINE:
                char = rfile.read(1)
                if char == b'\r':
                    break
                i += 1
            else:
                # we read more than MAX_REQUEST_LINE without
                # hitting CR
                self._chunked_input_error = True
                raise _InvalidClientInput("Too large chunk extension")

        if char == b'\r':
            # We either got here from the main loop or from the
            # end of an extension
            self.__read_chunk_size_crlf(rfile, newline_only=True)
            result = int(buf.getvalue(), 16)
            if result == 0:
                # The only time a chunk size of zero is allowed is the final
                # chunk. It is either followed by another \r\n, or some trailers
                # which are then followed by \r\n.
                while self.__read_chunk_trailer(rfile):
                    pass
            return result

    # Trailers have the following production (they are a header-field followed by CRLF)
    # See above for the definition of "token".
    #
    # header-field   = field-name ":" OWS field-value OWS
    # field-name     = token
    # field-value    = *( field-content / obs-fold )
    # field-content  = field-vchar [ 1*( SP / HTAB ) field-vchar ]
    # field-vchar    = VCHAR / obs-text
    # obs-fold       = CRLF 1*( SP / HTAB )
    #                ; obsolete line folding
    #                ; see Section 3.2.4


    def __read_chunk_trailer(self, rfile, ):
        # With rfile positioned just after a \r\n, read a trailer line.
        # Return a true value if a non-empty trailer was read, and
        # return false if an empty trailer was read (meaning the trailers are
        # done).
        # If a single line exceeds the MAX_REQUEST_LINE, raise an exception.
        # If the field-name portion contains invalid characters, raise an exception.

        i = 0
        empty = True
        seen_field_name = False
        while i < MAX_REQUEST_LINE:
            char = rfile.read(1)
            if char == b'\r':
                # Either read the next \n or raise an error.
                self.__read_chunk_size_crlf(rfile, newline_only=True)
                break
            # Not a \r, so we are NOT an empty chunk.
            empty = False
            if char == b':' and i > 0:
                # We're ending the field-name part; stop validating characters.
                # Unless : was the first character...
                seen_field_name = True
            if not seen_field_name and char not in _ALLOWED_TOKEN_CHARS:
                raise _InvalidClientInput('Invalid token character: %r' % (char,))
            i += 1
        else:
            # We read too much
            self._chunked_input_error = True
            raise _InvalidClientInput("Too large chunk trailer")
        return not empty

    def __read_chunk_size_crlf(self, rfile, newline_only=False):
        # Also for safety, correctly verify that we get \r\n when expected.
        if not newline_only:
            char = rfile.read(1)
            if char != b'\r':
                self._chunked_input_error = True
                raise _InvalidClientInput("Line didn't end in CRLF: %r" % (char,))
        char = rfile.read(1)
        if char != b'\n':
            self._chunked_input_error = True
            raise _InvalidClientInput("Line didn't end in LF: %r" % (char,))

    def _chunked_read(self, length=None, use_readline=False):
        # pylint:disable=too-many-branches
        rfile = self.rfile
        self._send_100_continue()

        if length == 0:
            return b""

        if use_readline:
            reader = self.rfile.readline
        else:
            reader = self.rfile.read

        response = []
        while self.chunk_length != 0:
            maxreadlen = self.chunk_length - self.position
            if length is not None and length < maxreadlen:
                maxreadlen = length

            if maxreadlen > 0:
                data = reader(maxreadlen)
                if not data:
                    self.chunk_length = 0
                    self._chunked_input_error = True
                    raise IOError("unexpected end of file while parsing chunked data")

                datalen = len(data)
                response.append(data)

                self.position += datalen
                if self.chunk_length == self.position:
                    self.__read_chunk_size_crlf(rfile)

                if length is not None:
                    length -= datalen
                    if length == 0:
                        break
                if use_readline and data[-1] == b"\n"[0]:
                    break
            else:
                # We're at the beginning of a chunk, so we need to
                # determine the next size to read
                self.chunk_length = self.__read_chunk_length(rfile)
                self.position = 0
                # If chunk_length was 0, we already read any trailers and
                # validated that we have ended with \r\n\r\n.

        return b''.join(response)

    def read(self, length=None):
        if length is not None and length < 0:
            length = None
        if self.chunked_input:
            return self._chunked_read(length)
        return self._do_read(length)

    def readline(self, size=None):
        if size is not None and size < 0:
            size = None
        if self.chunked_input:
            return self._chunked_read(size, True)
        return self._do_read(size, use_readline=True)

    def readlines(self, hint=None):
        # pylint:disable=unused-argument
        return list(self)

    def __iter__(self):
        return self

    def next(self):
        line = self.readline()
        if not line:
            raise StopIteration
        return line
    __next__ = next


try:
    import mimetools
    headers_factory = mimetools.Message
except ImportError:
    # adapt Python 3 HTTP headers to old API
    from http import client # pylint:disable=import-error

    class OldMessage(client.HTTPMessage):
        def __init__(self, **kwargs):
            super(client.HTTPMessage, self).__init__(**kwargs) # pylint:disable=bad-super-call
            self.status = ''

        def getheader(self, name, default=None):
            return self.get(name, default)

        @property
        def headers(self):
            for key, value in self._headers:
                yield '%s: %s\r\n' % (key, value)

        @property
        def typeheader(self):
            return self.get('content-type')

    def headers_factory(fp, *args): # pylint:disable=unused-argument
        try:
            ret = client.parse_headers(fp, _class=OldMessage)
        except client.LineTooLong:
            ret = OldMessage()
            ret.status = 'Line too long'
        return ret


class WSGIHandler(object):
    """
    Handles HTTP requests from a socket, creates the WSGI environment, and
    interacts with the WSGI application.

    This is the default value of :attr:`WSGIServer.handler_class`.
    This class may be subclassed carefully, and that class set on a
    :class:`WSGIServer` instance through a keyword argument at
    construction time.

    Instances are constructed with the same arguments as passed to the
    server's :meth:`WSGIServer.handle` method followed by the server
    itself. The application and environment are obtained from the server.

    """
    # pylint:disable=too-many-instance-attributes

    protocol_version = 'HTTP/1.1'

    def MessageClass(self, *args):
        return headers_factory(*args)

    # Attributes reset at various times for each request; not public
    # documented. Class attributes to keep the constructor fast
    # (but not make lint tools complain)

    status = None # byte string: b'200 OK'
    _orig_status = None # native string: '200 OK'
    response_headers = None # list of tuples (b'name', b'value')
    code = None # Integer parsed from status
    provided_date = None
    provided_content_length = None
    close_connection = False
    time_start = 0 # time.time() when begin handling request
    time_finish = 0 # time.time() when done handling request
    headers_sent = False # Have we already sent headers?
    response_use_chunked = False # Write with transfer-encoding chunked
    # Was the connection upgraded? We shouldn't try to chunk writes in that
    # case.
    connection_upgraded = False
    environ = None # Dict from self.get_environ
    application = None # application callable from self.server.application
    requestline = None # native str 'GET / HTTP/1.1'
    response_length = 0 # How much data we sent
    result = None # The return value of the WSGI application
    wsgi_input = None # Instance of Input()
    content_length = 0 # From application-provided headers Incoming
    # request headers, instance of MessageClass (gunicorn uses hasattr
    # on this so the default value needs to be compatible with the
    # API)
    headers = headers_factory(BytesIO())
    request_version = None # str: 'HTTP 1.1'
    command = None # str: 'GET'
    path = None # str: '/'

    def __init__(self, sock, address, server, rfile=None):
        # Deprecation: The rfile kwarg was introduced in 1.0a1 as part
        # of a refactoring. It was never documented or used. It is
        # considered DEPRECATED and may be removed in the future. Its
        # use is not supported.

        self.socket = sock
        self.client_address = address
        self.server = server
        if rfile is None:
            self.rfile = sock.makefile('rb', -1)
        else:
            self.rfile = rfile

    def handle(self):
        """
        The main request handling method, called by the server.

        This method runs a request handling loop, calling
        :meth:`handle_one_request` until all requests on the
        connection have been handled (that is, it implements
        keep-alive).
        """
        try:
            while self.socket is not None:
                self.time_start = time.time()
                self.time_finish = 0

                result = self.handle_one_request()
                if result is None:
                    break
                if result is True:
                    continue

                self.status, response_body = result # pylint:disable=unpacking-non-sequence
                self.socket.sendall(response_body)
                if self.time_finish == 0:
                    self.time_finish = time.time()
                self.log_request()
                break
        finally:
            if self.socket is not None:
                _sock = getattr(self.socket, '_sock', None) # Python 3
                try:
                    # read out request data to prevent error: [Errno 104] Connection reset by peer
                    if _sock:
                        try:
                            # socket.recv would hang
                            _sock.recv(16384)
                        finally:
                            _sock.close()
                    self.socket.close()
                except socket.error:
                    pass
            self.__dict__.pop('socket', None)
            self.__dict__.pop('rfile', None)
            self.__dict__.pop('wsgi_input', None)

    def _check_http_version(self):
        version_str = self.request_version
        if not version_str.startswith("HTTP/"):
            return False
        version = tuple(int(x) for x in version_str[5:].split("."))  # "HTTP/"
        if version[1] < 0 or version < (0, 9) or version >= (2, 0):
            return False
        return True

    def read_request(self, raw_requestline):
        """
        Parse the incoming request.

        Parses various headers into ``self.headers`` using
        :attr:`MessageClass`. Other attributes that are set upon a successful
        return of this method include ``self.content_length`` and ``self.close_connection``.

        :param str raw_requestline: A native :class:`str` representing
           the request line. A processed version of this will be stored
           into ``self.requestline``.

        :raises ValueError: If the request is invalid. This error will
           not be logged as a traceback (because it's a client issue, not a server problem).
        :return: A boolean value indicating whether the request was successfully parsed.
           This method should either return a true value or have raised a ValueError
           with details about the parsing error.

        .. versionchanged:: 1.1b6
           Raise the previously documented :exc:`ValueError` in more cases instead of returning a
           false value; this allows subclasses more opportunity to customize behaviour.
        """
        # pylint:disable=too-many-branches
        self.requestline = raw_requestline.rstrip()
        words = self.requestline.split()
        if len(words) == 3:
            self.command, self.path, self.request_version = words
            if not self._check_http_version():
                raise _InvalidClientRequest('Invalid http version: %r' % (raw_requestline,))
        elif len(words) == 2:
            self.command, self.path = words
            if self.command != "GET":
                raise _InvalidClientRequest('Expected GET method; Got command=%r; path=%r; raw=%r' % (
                    self.command, self.path, raw_requestline,))
            self.request_version = "HTTP/0.9"
            # QQQ I'm pretty sure we can drop support for HTTP/0.9
        else:
            raise _InvalidClientRequest('Invalid HTTP method: %r' % (raw_requestline,))

        self.headers = self.MessageClass(self.rfile, 0)

        if self.headers.status:
            raise _InvalidClientRequest('Invalid headers status: %r' % (self.headers.status,))

        if self.headers.get("transfer-encoding", "").lower() == "chunked":
            try:
                del self.headers["content-length"]
            except KeyError:
                pass

        content_length = self.headers.get("content-length")
        if content_length is not None:
            content_length = int(content_length)
            if content_length < 0:
                raise _InvalidClientRequest('Invalid Content-Length: %r' % (content_length,))

            if content_length and self.command in ('HEAD', ):
                raise _InvalidClientRequest('Unexpected Content-Length')

        self.content_length = content_length

        if self.request_version == "HTTP/1.1":
            conntype = self.headers.get("Connection", "").lower()
            self.close_connection = (conntype == 'close') # pylint:disable=superfluous-parens
        elif self.request_version == 'HTTP/1.0':
            conntype = self.headers.get("Connection", "close").lower()
            self.close_connection = (conntype != 'keep-alive') # pylint:disable=superfluous-parens
        else:
            # XXX: HTTP 0.9. We should drop support
            self.close_connection = True

        return True

    _print_unexpected_exc = staticmethod(traceback.print_exc)

    def log_error(self, msg, *args):
        if not args:
            # Already fully formatted, no need to do it again; msg
            # might contain % chars that would lead to a formatting
            # error.
            message = msg
        else:
            try:
                message = msg % args
            except Exception: # pylint:disable=broad-except
                self._print_unexpected_exc()
                message = '%r %r' % (msg, args)
        try:
            message = '%s: %s' % (self.socket, message)
        except Exception: # pylint:disable=broad-except
            pass

        try:
            self.server.error_log.write(message + '\n')
        except Exception: # pylint:disable=broad-except
            self._print_unexpected_exc()

    def read_requestline(self):
        """
        Read and return the HTTP request line.

        Under both Python 2 and 3, this should return the native
        ``str`` type; under Python 3, this probably means the bytes read
        from the network need to be decoded (using the ISO-8859-1 charset, aka
        latin-1).
        """
        line = self.rfile.readline(MAX_REQUEST_LINE)
        line = line.decode('latin-1')
        return line

    def handle_one_request(self):
        """
        Handles one HTTP request using ``self.socket`` and ``self.rfile``.

        Each invocation of this method will do several things, including (but not limited to):

        - Read the request line using :meth:`read_requestline`;
        - Read the rest of the request, including headers, with :meth:`read_request`;
        - Construct a new WSGI environment in ``self.environ`` using :meth:`get_environ`;
        - Store the application in ``self.application``, retrieving it from the server;
        - Handle the remainder of the request, including invoking the application,
          with :meth:`handle_one_response`

        There are several possible return values to indicate the state
        of the client connection:

        - ``None``
            The client connection is already closed or should
            be closed because the WSGI application or client set the
            ``Connection: close`` header. The request handling
            loop should terminate and perform cleanup steps.
        - (status, body)
            An HTTP status and body tuple. The request was in error,
            as detailed by the status and body. The request handling
            loop should terminate, close the connection, and perform
            cleanup steps. Note that the ``body`` is the complete contents
            to send to the client, including all headers and the initial
            status line.
        - ``True``
            The literal ``True`` value. The request was successfully handled
            and the response sent to the client by :meth:`handle_one_response`.
            The connection remains open to process more requests and the connection
            handling loop should call this method again. This is the typical return
            value.

        .. seealso:: :meth:`handle`

        .. versionchanged:: 1.1b6
           Funnel exceptions having to do with invalid HTTP requests through
           :meth:`_handle_client_error` to allow subclasses to customize. Note that
           this is experimental and may change in the future.
        """
        # pylint:disable=too-many-return-statements
        if self.rfile.closed:
            return

        try:
            self.requestline = self.read_requestline()
            # Account for old subclasses that haven't done this
            if isinstance(self.requestline, bytes):
                self.requestline = self.requestline.decode('latin-1')
        except socket.error:
            # "Connection reset by peer" or other socket errors aren't interesting here
            return

        if not self.requestline:
            return

        self.response_length = 0

        if len(self.requestline) >= MAX_REQUEST_LINE:
            return ('414', _REQUEST_TOO_LONG_RESPONSE)

        try:
            # for compatibility with older versions of pywsgi, we pass self.requestline as an argument there
            # NOTE: read_request is supposed to raise ValueError on invalid input; allow old
            # subclasses that return a False value instead.
            # NOTE: This can mutate the value of self.headers, so self.get_environ() must not be
            # called until AFTER this call is done.
            if not self.read_request(self.requestline):
                return ('400', _BAD_REQUEST_RESPONSE)
        except Exception as ex: # pylint:disable=broad-except
            # Notice we don't use self.handle_error because it reports
            # a 500 error to the client, and this is almost certainly
            # a client error.
            # Provide a hook for subclasses.
            return self._handle_client_error(ex)

        self.environ = self.get_environ()
        self.application = self.server.application

        self.handle_one_response()

        if self.close_connection:
            return

        if self.rfile.closed:
            return

        return True  # read more requests

    def _connection_upgrade_requested(self):
        if self.headers.get('Connection', '').lower() == 'upgrade':
            return True
        if self.headers.get('Upgrade', '').lower() == 'websocket':
            return True
        return False

    def finalize_headers(self):
        if self.provided_date is None:
            self.response_headers.append((b'Date', format_date_time(time.time())))

        self.connection_upgraded = self.code == 101

        if self.code not in (304, 204):
            # the reply will include message-body; make sure we have either Content-Length or chunked
            if self.provided_content_length is None:
                if hasattr(self.result, '__len__'):
                    total_len = sum(len(chunk) for chunk in self.result)
                    total_len_str = str(total_len)
                    total_len_str = total_len_str.encode("latin-1")
                    self.response_headers.append((b'Content-Length', total_len_str))
                else:
                    self.response_use_chunked = (
                        not self.connection_upgraded
                        and self.request_version != 'HTTP/1.0'
                    )
                    if self.response_use_chunked:
                        self.response_headers.append((b'Transfer-Encoding', b'chunked'))

    def _sendall(self, data):
        try:
            self.socket.sendall(data)
        except socket.error as ex:
            self.status = 'socket error: %s' % ex
            if self.code > 0:
                self.code = -self.code
            raise
        self.response_length += len(data)

    def _write(self, data,
               _bytearray=bytearray):
        if not data:
            # The application/middleware are allowed to yield
            # empty bytestrings.
            return

        if self.response_use_chunked:
            # Write the chunked encoding header
            header_str = b'%x\r\n' % len(data)
            towrite = _bytearray(header_str)

            # data
            towrite += data
            # trailer
            towrite += b'\r\n'
            self._sendall(towrite)
        else:
            self._sendall(data)

    ApplicationError = AssertionError

    def write(self, data):
        # The write() callable we return from start_response.
        # https://www.python.org/dev/peps/pep-3333/#the-write-callable
        # Supposed to do pretty much the same thing as yielding values
        # from the application's return.
        if self.code in (304, 204) and data:
            raise self.ApplicationError('The %s response must have no body' % self.code)

        if self.headers_sent:
            self._write(data)
        else:
            if not self.status:
                raise self.ApplicationError("The application did not call start_response()")
            self._write_with_headers(data)

    def _write_with_headers(self, data):
        self.headers_sent = True
        self.finalize_headers()

        # self.response_headers and self.status are already in latin-1, as encoded by self.start_response
        towrite = bytearray(b'HTTP/1.1 ')
        towrite += self.status
        towrite += b'\r\n'
        for header, value in self.response_headers:
            towrite += header
            towrite += b': '
            towrite += value
            towrite += b"\r\n"

        towrite += b'\r\n'
        self._sendall(towrite)
        # No need to copy the data into towrite; we may make an extra syscall
        # but the copy time could be substantial too, and it reduces the chances
        # of sendall being able to send everything in one go
        self._write(data)

    def start_response(self, status, headers, exc_info=None):
        """
         .. versionchanged:: 1.2a1
            Avoid HTTP header injection by raising a :exc:`ValueError`
            if *status* or any *header* name or value contains a carriage
            return or newline.
         .. versionchanged:: 1.1b5
            Pro-actively handle checking the encoding of the status line
            and headers during this method. On Python 2, avoid some
            extra encodings.
        """
        # pylint:disable=too-many-branches,too-many-statements
        if exc_info:
            try:
                if self.headers_sent:
                    # Re-raise original exception if headers sent
                    reraise(*exc_info)
            finally:
                # Avoid dangling circular ref
                exc_info = None

        # Pep 3333, "The start_response callable":
        # https://www.python.org/dev/peps/pep-3333/#the-start-response-callable
        # "Servers should check for errors in the headers at the time
        # start_response is called, so that an error can be raised
        # while the application is still running." Here, we check the encoding.
        # This aids debugging: headers especially are generated programmatically
        # and an encoding error in a loop or list comprehension yields an opaque
        # UnicodeError without any clue which header was wrong.
        # Note that this results in copying the header list at this point, not modifying it,
        # although we are allowed to do so if needed. This slightly increases memory usage.
        # We also check for HTTP Response Splitting vulnerabilities
        response_headers = []
        header = None
        value = None
        try:
            for header, value in headers:
                if not isinstance(header, str):
                    raise UnicodeError("The header must be a native string", header, value)
                if not isinstance(value, str):
                    raise UnicodeError("The value must be a native string", header, value)
                if '\r' in header or '\n' in header:
                    raise ValueError('carriage return or newline in header name', header)
                if '\r' in value or '\n' in value:
                    raise ValueError('carriage return or newline in header value', value)
                # Either we're on Python 2, in which case bytes is correct, or
                # we're on Python 3 and the user screwed up (because it should be a native
                # string). In either case, make sure that this is latin-1 compatible. Under
                # Python 2, bytes.encode() will take a round-trip through the system encoding,
                # which may be ascii, which is not really what we want. However, the latin-1 encoding
                # can encode everything except control characters and the block from 0x7F to 0x9F, so
                # explicitly round-tripping bytes through the encoding is unlikely to be of much
                # benefit, so we go for speed (the WSGI spec specifically calls out allowing the range
                # from 0x00 to 0xFF, although the HTTP spec forbids the control characters).
                # Note: Some Python 2 implementations, like Jython, may allow non-octet (above 255) values
                # in their str implementation; this is mentioned in the WSGI spec, but we don't
                # run on any platform like that so we can assume that a str value is pure bytes.
                response_headers.append((header.encode("latin-1"),
                                         value.encode("latin-1")))
        except UnicodeEncodeError:
            # If we get here, we're guaranteed to have a header and value
            raise UnicodeError("Non-latin1 header", repr(header), repr(value))

        # Same as above
        if not isinstance(status, str):
            raise UnicodeError("The status string must be a native string")
        if '\r' in status or '\n' in status:
            raise ValueError("carriage return or newline in status", status)
        # don't assign to anything until the validation is complete, including parsing the
        # code
        code = int(status.split(' ', 1)[0])

        self.status = status.encode("latin-1")
        self._orig_status = status # Preserve the native string for logging
        self.response_headers = response_headers
        self.code = code

        provided_connection = None # Did the wsgi app give us a Connection header?
        self.provided_date = None
        self.provided_content_length = None

        for header, value in headers:
            header = header.lower()
            if header == 'connection':
                provided_connection = value
            elif header == 'date':
                self.provided_date = value
            elif header == 'content-length':
                self.provided_content_length = value

        if self.request_version == 'HTTP/1.0' and provided_connection is None:
            conntype = b'close' if self.close_connection else b'keep-alive'
            response_headers.append((b'Connection', conntype))
        elif provided_connection == 'close':
            self.close_connection = True

        if self.code in (304, 204):
            if self.provided_content_length is not None and self.provided_content_length != '0':
                msg = 'Invalid Content-Length for %s response: %r (must be absent or zero)' % (self.code, self.provided_content_length)
                msg = msg.encode('latin-1')
                raise self.ApplicationError(msg)

        return self.write

    def log_request(self):
        self.server.log.write(self.format_request() + '\n')

    def format_request(self):
        now = datetime.now().replace(microsecond=0)
        length = self.response_length or '-'
        if self.time_finish:
            delta = '%.6f' % (self.time_finish - self.time_start)
        else:
            delta = '-'
        client_address = self.client_address[0] if isinstance(self.client_address, tuple) else self.client_address
        return '%s - - [%s] "%s" %s %s %s' % (
            client_address or '-',
            now,
            self.requestline or '',
            # Use the native string version of the status, saved so we don't have to
            # decode. But fallback to the encoded 'status' in case of subclasses
            # (Is that really necessary? At least there's no overhead.)
            (self._orig_status or self.status or '000').split()[0],
            length,
            delta)

    def process_result(self):
        for data in self.result:
            if data:
                self.write(data)
        if self.status and not self.headers_sent:
            # In other words, the application returned an empty
            # result iterable (and did not use the write callable)
            # Trigger the flush of the headers.
            self.write(b'')
        if self.response_use_chunked:
            self._sendall(b'0\r\n\r\n')


    def run_application(self):
        assert self.result is None
        try:
            self.result = self.application(self.environ, self.start_response)
            self.process_result()
        finally:
            close = getattr(self.result, 'close', None)
            try:
                if close is not None:
                    close()
            finally:
                # Discard the result. If it's a generator this can
                # free a lot of hidden resources (if we failed to iterate
                # all the way through it---the frames are automatically
                # cleaned up when StopIteration is raised); but other cases
                # could still free up resources sooner than otherwise.
                close = None
                self.result = None

    #: These errors are silently ignored by :meth:`handle_one_response` to avoid producing
    #: excess log entries on normal operating conditions. They indicate
    #: a remote client has disconnected and there is little or nothing
    #: this process can be expected to do about it. You may change this
    #: value in a subclass.
    #:
    #: The default value includes :data:`errno.EPIPE` and :data:`errno.ECONNRESET`.
    #: On Windows this also includes :data:`errno.WSAECONNABORTED`.
    #:
    #: This is a provisional API, subject to change. See :pr:`377`, :pr:`999`
    #: and :issue:`136`.
    #:
    #: .. versionadded:: 1.3
    ignored_socket_errors = (errno.EPIPE, errno.ECONNRESET)
    try:
        ignored_socket_errors += (errno.WSAECONNABORTED,)
    except AttributeError:
        pass # Not windows

    def handle_one_response(self):
        """
        Invoke the application to produce one response.

        This is called by :meth:`handle_one_request` after all the
        state for the request has been established. It is responsible
        for error handling.
        """
        self.time_start = time.time()
        self.status = None
        self.headers_sent = False

        self.result = None
        self.response_use_chunked = False
        self.connection_upgraded = False
        self.response_length = 0

        try:
            try:
                self.run_application()
            finally:
                try:
                    self.wsgi_input._discard()
                except _InvalidClientInput:
                    # This one is deliberately raised to the outer
                    # scope, because, with the incoming stream in some bad state,
                    # we can't be sure we can synchronize and properly parse the next
                    # request.
                    raise
                except socket.error:
                    # Don't let socket exceptions during discarding
                    # input override any exception that may have been
                    # raised by the application, such as our own _InvalidClientInput.
                    # In the general case, these aren't even worth logging (see the comment
                    # just below)
                    pass
        except _InvalidClientInput as ex:
            # DO log this one because:
            # - Some of the data may have been read and acted on by the
            #   application;
            # - The response may or may not have been sent;
            # - It's likely that the client is bad, or malicious, and
            #   users might wish to take steps to block the client.
            self._handle_client_error(ex)
            self.close_connection = True
            self._send_error_response_if_possible(400)
        except socket.error as ex:
            if ex.args[0] in self.ignored_socket_errors:
                # See description of self.ignored_socket_errors.
                self.close_connection = True
            else:
                self.handle_error(*sys.exc_info())
        except: # pylint:disable=bare-except
            self.handle_error(*sys.exc_info())
        finally:
            self.time_finish = time.time()
            self.log_request()

    def _send_error_response_if_possible(self, error_code):
        if self.response_length:
            self.close_connection = True
        else:
            status, headers, body = _ERRORS[error_code]
            try:
                self.start_response(status, headers[:])
                self.write(body)
            except socket.error:
                self.close_connection = True

    def _log_error(self, t, v, tb):
        # TODO: Shouldn't we dump this to wsgi.errors? If we did that now, it would
        # wind up getting logged twice
        if not issubclass(t, GreenletExit):
            context = self.environ
            if not isinstance(context, self.server.secure_environ_class):
                context = self.server.secure_environ_class(context)
            self.server.loop.handle_error(context, t, v, tb)

    def handle_error(self, t, v, tb):
        # Called for internal, unexpected errors, NOT invalid client input
        self._log_error(t, v, tb)
        t = v = tb = None
        self._send_error_response_if_possible(500)

    def _handle_client_error(self, ex):
        # Called for invalid client input
        # Returns the appropriate error response.
        if not isinstance(ex, (ValueError, _InvalidClientInput)):
            # XXX: Why not self._log_error to send it through the loop's
            # handle_error method?
            # _InvalidClientRequest is a ValueError; _InvalidClientInput is an IOError.
            traceback.print_exc()
        if isinstance(ex, _InvalidClientRequest):
            # No formatting needed, that's already been handled. In fact, because the
            # formatted message contains user input, it might have a % in it, and attempting
            # to format that with no arguments would be an error.
            # However, the error messages do not include the requesting IP
            # necessarily, so we do add that.
            self.log_error('(from %s) %s', self.client_address, ex.formatted_message)
        else:
            self.log_error('Invalid request (from %s): %s',
                           self.client_address,
                           str(ex) or ex.__class__.__name__)
        return ('400', _BAD_REQUEST_RESPONSE)

    def _headers(self):
        key = None
        value = None
        IGNORED_KEYS = (None, 'CONTENT_TYPE', 'CONTENT_LENGTH')
        for header in self.headers.headers:
            if key is not None and header[:1] in " \t":
                value += header
                continue

            if key not in IGNORED_KEYS:
                yield 'HTTP_' + key, value.strip()

            key, value = header.split(':', 1)
            if '_' in key:
                # strip incoming bad veaders
                key = None
            else:
                key = key.replace('-', '_').upper()

        if key not in IGNORED_KEYS:
            yield 'HTTP_' + key, value.strip()

    def get_environ(self):
        """
        Construct and return a new WSGI environment dictionary for a specific request.

        This should begin with asking the server for the base environment
        using :meth:`WSGIServer.get_environ`, and then proceed to add the
        request specific values.

        By the time this method is invoked the request line and request shall have
        been parsed and ``self.headers`` shall be populated.
        """
        env = self.server.get_environ()
        env['REQUEST_METHOD'] = self.command
        # SCRIPT_NAME is explicitly implementation defined. Using an
        # empty value for SCRIPT_NAME is both explicitly allowed by
        # both the CGI standard and WSGI PEPs, and also the thing that
        # makes the most sense from a generic server perspective (we
        # have no hierarchy or understanding of URLs or files, just a
        # single application to call. The empty string represents the
        # application root, which is what we have). Different WSGI
        # implementations handle this very differently, so portable
        # applications that rely on SCRIPT_NAME will have to use a
        # WSGI middleware to set it to a defined value, or otherwise
        # rely on server-specific mechanisms (e.g, on waitress, use
        # ``--url-prefix``, in gunicorn set the ``SCRIPT_NAME`` header
        # or process environment variable, in gevent subclass
        # WSGIHandler.)
        #
        # See https://github.com/gevent/gevent/issues/1667 for discussion.
        env['SCRIPT_NAME'] = ''

        path, query = self.path.split('?', 1) if '?' in self.path else (self.path, '')
        # Note that self.path contains the original str object; if it contains
        # encoded escapes, it will NOT match PATH_INFO.
        env['PATH_INFO'] = unquote_latin1(path)
        env['QUERY_STRING'] = query

        if self.headers.typeheader is not None:
            env['CONTENT_TYPE'] = self.headers.typeheader

        length = self.headers.getheader('content-length')
        if length:
            env['CONTENT_LENGTH'] = length
        env['SERVER_PROTOCOL'] = self.request_version

        client_address = self.client_address
        if isinstance(client_address, tuple):
            env['REMOTE_ADDR'] = str(client_address[0])
            env['REMOTE_PORT'] = str(client_address[1])

        for key, value in self._headers():
            if key in env:
                if 'COOKIE' in key:
                    env[key] += '; ' + value
                else:
                    env[key] += ',' + value
            else:
                env[key] = value

        sock = self.socket if env.get('HTTP_EXPECT') == '100-continue' else None

        chunked = env.get('HTTP_TRANSFER_ENCODING', '').lower() == 'chunked'
        # Input refuses to read if the data isn't chunked, and there is no content_length
        # provided. For 'Upgrade: Websocket' requests, neither of those things is true.
        handling_reads = not self._connection_upgrade_requested()

        self.wsgi_input = Input(self.rfile, self.content_length, socket=sock, chunked_input=chunked)

        env['wsgi.input'] = self.wsgi_input if handling_reads else self.rfile
        # This is a non-standard flag indicating that our input stream is
        # self-terminated (returns EOF when consumed).
        # See https://github.com/gevent/gevent/issues/1308
        env['wsgi.input_terminated'] = handling_reads
        return env


class _NoopLog(object):
    # Does nothing; implements just enough file-like methods
    # to pass the WSGI validator

    def write(self, *args, **kwargs):
        # pylint:disable=unused-argument
        return

    def flush(self):
        pass

    def writelines(self, *args, **kwargs):
        pass


class LoggingLogAdapter(object):
    """
    An adapter for :class:`logging.Logger` instances
    to let them be used with :class:`WSGIServer`.

    .. warning:: Unless the entire process is monkey-patched at a very
        early part of the lifecycle (before logging is configured),
        loggers are likely to not be gevent-cooperative. For example,
        the socket and syslog handlers use the socket module in a way
        that can block, and most handlers acquire threading locks.

    .. warning:: It *may* be possible for the logging functions to be
       called in the :class:`gevent.Hub` greenlet. Code running in the
       hub greenlet cannot use any gevent blocking functions without triggering
       a ``LoopExit``.

    .. versionadded:: 1.1a3

    .. versionchanged:: 1.1b6
       Attributes not present on this object are proxied to the underlying
       logger instance. This permits using custom :class:`~logging.Logger`
       subclasses (or indeed, even duck-typed objects).

    .. versionchanged:: 1.1
       Strip trailing newline characters on the message passed to :meth:`write`
       because log handlers will usually add one themselves.
    """

    # gevent avoids importing and using logging because importing it and
    # creating loggers creates native locks unless monkey-patched.

    __slots__ = ('_logger', '_level')

    def __init__(self, logger, level=20):
        """
        Write information to the *logger* at the given *level* (default to INFO).
        """
        self._logger = logger
        self._level = level

    def write(self, msg):
        if msg and msg.endswith('\n'):
            msg = msg[:-1]
        self._logger.log(self._level, msg)

    def flush(self):
        "No-op; required to be a file-like object"

    def writelines(self, lines):
        for line in lines:
            self.write(line)

    def __getattr__(self, name):
        return getattr(self._logger, name)

    def __setattr__(self, name, value):
        if name not in LoggingLogAdapter.__slots__:
            setattr(self._logger, name, value)
        else:
            object.__setattr__(self, name, value)

    def __delattr__(self, name):
        delattr(self._logger, name)

####
## Environ classes.
# These subclass dict. They could subclass collections.UserDict on
# 3.3+ and proxy to the underlying real dict to avoid a copy if we
# have to print them (on 2.7 it's slightly more complicated to be an
# instance of collections.MutableMapping; UserDict.UserDict isn't.)
# Then we could have either the WSGIHandler.get_environ or the
# WSGIServer.get_environ return one of these proxies, and
# WSGIHandler.run_application would know to access the `environ.data`
# attribute to be able to pass the *real* dict to the application
# (because PEP3333 requires no subclasses, only actual dict objects;
# wsgiref.validator and webob.Request both enforce this). This has the
# advantage of not being fragile if anybody else tries to print/log
# self.environ (and not requiring a copy). However, if there are any
# subclasses of Handler or Server, this could break if they don't know
# to return this type.
####

class Environ(dict):
    """
    A base class that can be used for WSGI environment objects.

    Provisional API.

    .. versionadded:: 1.2a1
    """

    __slots__ = () # add no ivars or weakref ability

    def copy(self):
        return self.__class__(self)

    if not hasattr(dict, 'iteritems'):
        # Python 3
        def iteritems(self):
            return self.items()

    def __reduce_ex__(self, proto):
        return (dict, (), None, None, iter(self.iteritems()))

class SecureEnviron(Environ):
    """
    An environment that does not print its keys and values
    by default.

    Provisional API.

    This is intended to keep potentially sensitive information like
    HTTP authorization and cookies from being inadvertently printed
    or logged.

    For debugging, each instance can have its *secure_repr* attribute
    set to ``False``, which will cause it to print like a normal dict.

    When *secure_repr* is ``True`` (the default), then the value of
    the *whitelist_keys* attribute is consulted; if this value is
    true-ish, it should be a container (something that responds to
    ``in``) of key names (typically a list or set). Keys and values in
    this dictionary that are in *whitelist_keys* will then be printed,
    while all other values will be masked. These values may be
    customized on the class by setting the *default_secure_repr* and
    *default_whitelist_keys*, respectively::

        >>> environ = SecureEnviron(key='value')
        >>> environ # doctest: +ELLIPSIS
        <pywsgi.SecureEnviron dict (keys: 1) at ...

    If we whitelist the key, it gets printed::

        >>> environ.whitelist_keys = {'key'}
        >>> environ
        {'key': 'value'}

    A non-whitelisted key (*only*, to avoid doctest issues) is masked::

        >>> environ['secure'] = 'secret'; del environ['key']
        >>> environ
        {'secure': '<MASKED>'}

    We can turn it off entirely for the instance::

        >>> environ.secure_repr = False
        >>> environ
        {'secure': 'secret'}

    We can also customize it at the class level (here we use a new
    class to be explicit and to avoid polluting the true default
    values; we would set this class to be the ``environ_class`` of the
    server)::

        >>> class MyEnviron(SecureEnviron):
        ...    default_whitelist_keys = ('key',)
        ...
        >>> environ = MyEnviron({'key': 'value'})
        >>> environ
        {'key': 'value'}

    .. versionadded:: 1.2a1
    """

    default_secure_repr = True
    default_whitelist_keys = ()
    default_print_masked_keys = True

    # Allow instances to override the class values,
    # but inherit from the class if not present. Keeps instances
    # small since we can't combine __slots__ with class attributes
    # of the same name.
    __slots__ = ('secure_repr', 'whitelist_keys', 'print_masked_keys')

    def __getattr__(self, name):
        if name in SecureEnviron.__slots__:
            return getattr(type(self), 'default_' + name)
        raise AttributeError(name)

    def __repr__(self):
        if self.secure_repr:
            whitelist = self.whitelist_keys
            print_masked = self.print_masked_keys
            if whitelist:
                safe = {k: self[k] if k in whitelist else "<MASKED>"
                        for k in self
                        if k in whitelist or print_masked}
                safe_repr = repr(safe)
                if not print_masked and len(safe) != len(self):
                    safe_repr = safe_repr[:-1] + ", (hidden keys: %d)}" % (len(self) - len(safe))
                return safe_repr
            return "<pywsgi.SecureEnviron dict (keys: %d) at %s>" % (len(self), id(self))
        return Environ.__repr__(self)
    __str__ = __repr__


class WSGISecureEnviron(SecureEnviron):
    """
    Specializes the default list of whitelisted keys to a few
    common WSGI variables.

    Example::

       >>> environ = WSGISecureEnviron(REMOTE_ADDR='::1', HTTP_AUTHORIZATION='secret')
       >>> environ
       {'REMOTE_ADDR': '::1', (hidden keys: 1)}
       >>> import pprint
       >>> pprint.pprint(environ)
       {'REMOTE_ADDR': '::1', (hidden keys: 1)}
       >>> print(pprint.pformat(environ))
       {'REMOTE_ADDR': '::1', (hidden keys: 1)}
    """
    default_whitelist_keys = ('REMOTE_ADDR', 'REMOTE_PORT', 'HTTP_HOST')
    default_print_masked_keys = False


class WSGIServer(StreamServer):
    """
    A WSGI server based on :class:`StreamServer` that supports HTTPS.


    :keyword log: If given, an object with a ``write`` method to which
        request (access) logs will be written. If not given, defaults
        to :obj:`sys.stderr`. You may pass ``None`` to disable request
        logging. You may use a wrapper, around e.g., :mod:`logging`,
        to support objects that don't implement a ``write`` method.
        (If you pass a :class:`~logging.Logger` instance, or in
        general something that provides a ``log`` method but not a
        ``write`` method, such a wrapper will automatically be created
        and it will be logged to at the :data:`~logging.INFO` level.)

    :keyword error_log: If given, a file-like object with ``write``,
        ``writelines`` and ``flush`` methods to which error logs will
        be written. If not given, defaults to :obj:`sys.stderr`. You
        may pass ``None`` to disable error logging (not recommended).
        You may use a wrapper, around e.g., :mod:`logging`, to support
        objects that don't implement the proper methods. This
        parameter will become the value for ``wsgi.errors`` in the
        WSGI environment (if not already set). (As with *log*,
        wrappers for :class:`~logging.Logger` instances and the like
        will be created automatically and logged to at the :data:`~logging.ERROR`
        level.)

    .. seealso::

        :class:`LoggingLogAdapter`
            See important warnings before attempting to use :mod:`logging`.

    .. versionchanged:: 1.1a3
        Added the ``error_log`` parameter, and set ``wsgi.errors`` in the WSGI
        environment to this value.
    .. versionchanged:: 1.1a3
        Add support for passing :class:`logging.Logger` objects to the ``log`` and
        ``error_log`` arguments.
    .. versionchanged:: 20.6.0
        Passing a ``handle`` kwarg to the constructor is now officially deprecated.
    """

    #: A callable taking three arguments: (socket, address, server) and returning
    #: an object with a ``handle()`` method. The callable is called once for
    #: each incoming socket request, as is its handle method. The handle method should not
    #: return until all use of the socket is complete.
    #:
    #: This class uses the :class:`WSGIHandler` object as the default value. You may
    #: subclass this class and set a different default value, or you may pass
    #: a value to use in the ``handler_class`` keyword constructor argument.
    handler_class = WSGIHandler

    #: The object to which request logs will be written.
    #: It must never be None. Initialized from the ``log`` constructor
    #: parameter.
    log = None

    #: The object to which error logs will be written.
    #: It must never be None. Initialized from the ``error_log`` constructor
    #: parameter.
    error_log = None

    #: The class of environ objects passed to the handlers.
    #: Must be a dict subclass. For compliance with :pep:`3333`
    #: and libraries like WebOb, this is simply :class:`dict`
    #: but this can be customized in a subclass or per-instance
    #: (probably to :class:`WSGISecureEnviron`).
    #:
    #: .. versionadded:: 1.2a1
    environ_class = dict

    # Undocumented internal detail: the class that WSGIHandler._log_error
    # will cast to before passing to the loop.
    secure_environ_class = WSGISecureEnviron

    base_env = {'GATEWAY_INTERFACE': 'CGI/1.1',
                'SERVER_SOFTWARE': 'gevent/%d.%d Python/%d.%d' % (gevent.version_info[:2] + sys.version_info[:2]),
                'SCRIPT_NAME': '',
                'wsgi.version': (1, 0),
                'wsgi.multithread': False, # XXX: Aren't we really, though?
                'wsgi.multiprocess': False,
                'wsgi.run_once': False}

    def __init__(self, listener, application=None, backlog=None, spawn='default',
                 log='default', error_log='default',
                 handler_class=None,
                 environ=None, **ssl_args):
        if 'handle' in ssl_args:
            # The ultimate base class (BaseServer) uses 'handle' for
            # the thing we call 'application'. We never deliberately
            # bass a `handle` argument to the base class, but one
            # could sneak in through ``**ssl_args``, even though that
            # is not the intent, while application is None. That
            # causes our own ``def handle`` method to be replaced,
            # probably leading to bad results. Passing a 'handle'
            # instead of an 'application' can really confuse things.
            import warnings
            warnings.warn("Passing 'handle' kwarg to WSGIServer is deprecated. "
                          "Did you mean application?", DeprecationWarning, stacklevel=2)

        StreamServer.__init__(self, listener, backlog=backlog, spawn=spawn, **ssl_args)

        if application is not None:
            self.application = application
        if handler_class is not None:
            self.handler_class = handler_class

        # Note that we can't initialize these as class variables:
        # sys.stderr might get monkey patched at runtime.
        def _make_log(l, level=20):
            if l == 'default':
                return sys.stderr
            if l is None:
                return _NoopLog()
            if not hasattr(l, 'write') and hasattr(l, 'log'):
                return LoggingLogAdapter(l, level)
            return l
        self.log = _make_log(log)
        self.error_log = _make_log(error_log, 40) # logging.ERROR

        self.set_environ(environ)
        self.set_max_accept()

    def set_environ(self, environ=None):
        if environ is not None:
            self.environ = environ
        environ_update = getattr(self, 'environ', None)

        self.environ = self.environ_class(self.base_env)
        if self.ssl_enabled:
            self.environ['wsgi.url_scheme'] = 'https'
        else:
            self.environ['wsgi.url_scheme'] = 'http'
        if environ_update is not None:
            self.environ.update(environ_update)
        if self.environ.get('wsgi.errors') is None:
            self.environ['wsgi.errors'] = self.error_log

    def set_max_accept(self):
        if self.environ.get('wsgi.multiprocess'):
            self.max_accept = 1

    def get_environ(self):
        return self.environ_class(self.environ)

    def init_socket(self):
        StreamServer.init_socket(self)
        self.update_environ()

    def update_environ(self):
        """
        Called before the first request is handled to fill in WSGI environment values.

        This includes getting the correct server name and port.
        """
        address = self.address
        if isinstance(address, tuple):
            if 'SERVER_NAME' not in self.environ:
                try:
                    name = socket.getfqdn(address[0])
                except socket.error:
                    name = str(address[0])
                if not isinstance(name, str):
                    name = name.decode('ascii')
                self.environ['SERVER_NAME'] = name
            self.environ.setdefault('SERVER_PORT', str(address[1]))
        else:
            self.environ.setdefault('SERVER_NAME', '')
            self.environ.setdefault('SERVER_PORT', '')

    def handle(self, sock, address):
        """
        Create an instance of :attr:`handler_class` to handle the request.

        This method blocks until the handler returns.
        """
        # pylint:disable=method-hidden
        handler = self.handler_class(sock, address, self)
        handler.handle()

def _main():
    # Provisional main handler, for quick tests, not production
    # usage.
    from gevent import monkey; monkey.patch_all()

    import argparse
    import importlib

    parser = argparse.ArgumentParser()
    parser.add_argument("app", help="dotted name of WSGI app callable [module:callable]")
    parser.add_argument("-b", "--bind",
                        help="The socket to bind",
                        default=":8080")

    args = parser.parse_args()

    module_name, app_name = args.app.split(':')
    module = importlib.import_module(module_name)
    app = getattr(module, app_name)
    bind = args.bind

    server = WSGIServer(bind, app)
    server.serve_forever()

if __name__ == '__main__':
    _main()
