import io
import logging
import sys
import time
import typing
from contextlib import suppress
from http import HTTPStatus
from urllib.parse import unquote
from wsgiref.handlers import format_date_time
from wsgiref.simple_server import sys_version

import h11
from werkzeug.exceptions import RequestTimeout
from werkzeug.exceptions import default_exceptions as werkzeug_exceptions
from werkzeug.middleware.proxy_fix import ProxyFix

import odoo
import odoo.release
from odoo.tools import config

from .router import root
from .server_log import _logger, http_log, reset_thread_info

if typing.TYPE_CHECKING:
    from collections.abc import Buffer

# Buffer size for recv() calls.
# 16kiB to match nginx's default client_body_buffer_size.
RECV_SIZE = 16384

# h11 bufferizes what has been recv()-ed inside its connection object.
# It has not buffer size limit: receive_data() never raise an exception.
# Instead, when calling next_event(), it does the following:
#
#   event = _extract_next_receive_event()
#   if event is NEED_DATA:
#       if len(_receive_buffer) > MAX_INCOMPLETE_EVENT_SIZE:
#           raise RemoteProtocolError(...)
#   return event
#
# As we always do the following pattern:
#
#   while conn.next_event() is h11.NEED_DATA:
#       conn.receive_data(sock.recv(RECV_SIZE))
#
# The buffer can grow bigger than MAX_INCOMPLETE_EVENT_SIZE, but in our
# case it never grows bigger than MAX_INCOMPLETE_EVENT_SIZE + RECV_SIZE.
MAX_INCOMPLETE_EVENT_SIZE = 16384

# No need to conceal the server agent as Odoo MUST run behind a web
# server (apache/nginx/...), which is gonna replace it with its own.
SERVER_SOFTWARE = ' '.join((
    f'odoo/{odoo.release.series}',
    h11.PRODUCT_ID,
    sys_version,
))
SERVER_AGENT = SERVER_SOFTWARE.encode()


def _verify_target(target: bytes):
    # RFC9112 says in #3.2:
    # 1. Clients MUST use origin-form when talking to origin servers.
    # 2. Proxies MUST convert absolute-form to origin-from + Host.
    # 3. Servers MUST convert absolute-form to origin-from + Host
    # We ignore this third point as Odoo MUST be deployed behind a
    # proxy and both the clients and proxies MUST NOT send
    # absolute-form request targets. If we receive an absolute-form
    # it likely is a rogue client.
    if not target.startswith(b'/') and target != b'*':
        e = "target is not origin-form"
        raise h11.RemoteProtocolError(e)


def _verify_headers(headers):
    # RFC9112 says in #field.transfer-encoding:
    # Transfert-Encoding and Content-Length can be both present in the
    # headers, in which case Transfert-Encoding takes precedent over
    # Content-Length, but it can make it vulnerable to request smuggling
    # or splitting. "A server MAY reject a request that contains both
    # Content-Length and Transfer-Encoding".
    if (
        any(h == b'transfert-encoding' for h, _ in headers) and
        any(h == b'content-length' for h, _ in headers)
    ):
        e = "can't use both Content-Length and Transfert-Encoding"
        raise h11.RemoteProtocolError(e)


class HTTPSocket:
    __slots__ = (
        'addr',
        'conn',
        'h11request',
        'h11response',
        'ip',
        'sock',
    )

    def __init__(self, client_sock, client_addr, *, prelude=b''):
        self.sock = client_sock
        self.addr = client_addr
        self.ip = client_addr[0]  # until we find the X-Forwarded-For header

        self.conn = h11.Connection(
            h11.SERVER,
            max_incomplete_event_size=MAX_INCOMPLETE_EVENT_SIZE,
        )
        if prelude:
            self.conn.receive_data(prelude)

        self.h11request = None
        self.h11response = None

    def _log(self, level, msg, *args, req=None, res=None, **kwargs):
        kwargs.setdefault('extra', {}).setdefault('remote_addr', self.ip)
        http_log(
            level,
            msg,
            *args,
            req=req or self.h11request,
            res=res or self.h11response,
            **kwargs,
        )

    def _make_environ(self):
        # h11 made sure the target, http_version, header names and
        # content-length only contain valid ascii characters. It didn't
        # verify any other header value as HTTP (RFC9110) states they
        # can be "opaque" data. Decoding them as latin-1 gives the
        # correct string for US-ASCII and ISO-8859-1 which are the two
        # commonly used charset for header values. Using latin-1 doesn't
        # break RFC2047/RFC5987/RFC8187-encoding (base64 or %-encoding)
        # and just leaves the string unparsed. HTTP headers that use
        # other (non-standard) charsets are passed to the application as
        # latin-1 string and must be re-encoded by the application. This
        # is in line with the WSGI spec.
        assert self.h11request
        request_uri = self.h11request.target.decode('ascii')
        path_quoted, _, query = request_uri.partition('?')

        environ = {
            'REQUEST_METHOD': self.h11request.method.decode('ascii'),
            'SCRIPT_NAME': '',
            'PATH_INFO': unquote(path_quoted, 'latin-1'),
            'QUERY_STRING': query,
            'REQUEST_URI': request_uri,
            'RAW_URI': request_uri,
            'REMOTE_ADDR': self.addr[0],
            'REMOTE_PORT': self.addr[1],
            'SERVER_NAME': config['http_interface'],
            'SERVER_PORT': config['http_port'],
            'SERVER_PROTOCOL': 'HTTP/' + self.h11request.http_version.decode('ascii'),
            'SERVER_SOFTWARE': SERVER_SOFTWARE,
            'wsgi.version': (1, 0),
            'wsgi.url_scheme': 'http',
            'wsgi.input': HTTPBodyReader(self.sock, self.conn),
            'wsgi.errors': sys.stderr,
            'wsgi.multithread': not config['workers'] and not odoo.evented,
            'wsgi.multiprocess': config['workers'] and not odoo.evented,
            'wsgi.run_once': False,
        }
        if environ['wsgi.multithread']:
            # cannot use websocket in multiworker and gevent uses
            # another http library than this one
            environ['socket'] = self.sock
            environ['odoo.trailing_data'] = lambda: self.conn.trailing_data

        # do like gunicorn: ignore headers with _ and merge those with
        # an identic name
        headers = {}
        for header, value in self.h11request.headers:
            if b'_' in header:
                continue
            header = 'HTTP_' + header.upper().replace(b'-', b'_').decode('ascii')
            if header in headers:
                headers[header] += ',' + value.decode('latin-1')
            else:
                headers[header] = value.decode('latin-1')
        if content_type := headers.pop('HTTP_CONTENT_TYPE', ''):
            environ['CONTENT_TYPE'] = content_type
        if content_length := headers.pop('HTTP_CONTENT_LENGTH', ''):
            environ['CONTENT_LENGTH'] = content_length
        environ.update(headers)

        if config['proxy_mode'] and environ.get('HTTP_X_FORWARDED_HOST'):
            pf = ProxyFix(lambda e, sr: (), x_for=1, x_proto=1, x_host=1)
            pf(environ, lambda status, headers: None)  # it updates environ
            self.ip = environ['REMOTE_ADDR']

        return environ

    def process_request(self):
        reset_thread_info()

        # Receive the HTTP request
        try:
            event = self.conn.next_event()
            while event is h11.NEED_DATA:
                try:
                    self.conn.receive_data(self.sock.recv(RECV_SIZE))
                except ConnectionError:
                    return
                except TimeoutError as exc:
                    e = "Timed out"
                    raise h11.RemoteProtocolError(e, HTTPStatus.REQUEST_TIMEOUT) from exc
                event = self.conn.next_event()
            if type(event) is h11.ConnectionClosed:
                return
            assert type(event) is h11.Request, event
            self.h11request = event
            _verify_target(event.target)
            _verify_headers(event.headers)
        except h11.RemoteProtocolError as exc:
            # There is an error in the HTTP request. Fail with a 4xx and
            # close the socket. Do not bother with a reason or a body.
            self.h11response = h11.Response(
                status_code=exc.error_status_hint,
                headers=[
                    (b'date', format_date_time(time.time()).encode()),
                    (b'server', SERVER_AGENT),
                    (b'connection', b'close'),
                    (b'content-length', b'0'),
                ],
            )
            with suppress(ConnectionError):
                self.sock.sendall(self.conn.send(self.h11response))
            self._log(logging.INFO, '', exc_info=_logger.isEnabledFor(logging.DEBUG))
            eof = self.conn.send(h11.EndOfMessage())
            assert eof == b'', eof
            assert self.conn.our_state is h11.MUST_CLOSE, self.conn.our_state
            return
        else:
            # We got our request.
            self._log(logging.DEBUG, '[REQ] ')  # request line + headers

        # If the request has header "Expect: 100-continue". Send a 100
        # Continue response now: we're just before forwarding the
        # request to the WSGI application, and we've read all headers.
        if self.conn.client_is_waiting_for_100_continue:
            res_continue = h11.InformationalResponse(
                status_code=HTTPStatus.CONTINUE,
                headers=[
                    (b'date', format_date_time(time.time()).encode()),
                    (b'server', SERVER_AGENT),
                ],
            )
            self.sock.sendall(self.conn.send(res_continue))
            self._log(logging.DEBUG, '[100] ', res=res_continue)

        # Pass the request into the WSGI application. It'll call our
        # start_response() with the http response line and headers, then
        # return an iterable object containing the body.
        wsgi_environ = self._make_environ()
        wsgi_response = root(wsgi_environ, self.start_response)
        assert self.h11response

        if self.conn.our_state is h11.SWITCHED_PROTOCOL:
            # The WSGI application called start_response() with
            # > HTTP/1.1 101 Switching Protocols
            # > Connection: upgrade
            # > Upgrade: websocket
            # HTTP-wise there is nothing left to do.
            if hasattr(wsgi_response, 'close'):
                wsgi_response.close()  # werkzeug call_on_close()
            self._log(logging.INFO, '')
            return

        # Iter over the iterable object the WSGI application gave us. It
        # contains the body that we are yet to send on the network.
        bytes_sent = 0
        exc_info = None
        try:
            for chunk in wsgi_response:
                if data := self.conn.send(h11.Data(chunk)):
                    self.sock.sendall(data)
                bytes_sent += len(chunk)
            if data := self.conn.send(h11.EndOfMessage()):
                self.sock.sendall(data)
        except ConnectionError:
            # The client is no longer connected. Ignore the exception.
            self.conn.send_failed()
        except Exception as exc:  # noqa: BLE001
            # A fatal error occured while sending the body, mark the
            # connection failed and close it.
            self.conn.send_failed()
            exc_info = exc
        finally:
            if hasattr(wsgi_response, 'close'):
                wsgi_response.close()  # werkzeug call_on_close()

        self._log(  # response body
            logging.ERROR if exc_info else logging.INFO,
            '',
            exc_info=exc_info,
            extra={
                'http_response_body': bytes_sent,
                'http_headers': (),  # already printed at [RES]
            },
        )

    def start_response(
        self,
        status: str,
        response_headers: list[tuple[str, str]],
        exc_info=None,
    ):
        status_code, _, reason = status.partition(' ')
        status_code = HTTPStatus(int(status_code))

        # Do the wsgi-encoding dance back, see _make_environ()
        response_headers: list[tuple[bytes, bytes]] = [
            (header.encode('ascii').lower(), value.encode('latin-1'))
            for header, value in response_headers
        ]
        get_header = dict(response_headers).get

        # Add the mandatory HTTP headers
        if (cnx := get_header(b'connection')) is not None:
            if cnx.lower() == b'upgrade':
                if not get_header(b'upgrade'):
                    e = "the Upgrade header is mandatory with Connection: upgrade"
                    raise ValueError(e)
            elif cnx.lower() != b'close':
                e = f"invalid Connection header: {cnx}"
                raise ValueError(e)
        else:
            response_headers.append((b'connection', b'close'))
        if get_header(b'server') is None:
            response_headers.append((b'server', SERVER_AGENT))
        if get_header(b'date') is None:
            date = format_date_time(time.time()).encode()
            response_headers.insert(0, (b'date', date))

        # Send and log the response
        h11response_cls = (
            h11.InformationalResponse
            if status_code.is_informational else
            h11.Response
        )
        self.h11response = h11response_cls(
            status_code=status_code,
            reason=reason,
            headers=response_headers,
        )
        self.sock.sendall(self.conn.send(self.h11response))
        self._log(logging.DEBUG, '[RES] ')  # response line + headers


class HTTPBodyReader(io.RawIOBase):
    def __init__(self, sock, conn):
        self._sock = sock
        self._conn = conn
        self._buffered: Buffer | None = b''

    def readable(self) -> bool:
        return True

    def read(self, size: int = -1):
        if size == -1:
            buff = memoryview(bytearray(RECV_SIZE))
            result = bytearray()
            while count := self.readinto(buff):
                result.extend(buff[:count])
            return bytes(result)

        if self._buffered:
            result, self._buffered = self._buffered[:size], self._buffered[size:]
            return bytes(result)

        buff = memoryview(bytearray(size))
        count = self.readinto(buff)
        return bytes(buff[:count])

    def readinto(self, buff):
        if self._buffered is None:  # eof
            return 0

        if self._buffered:
            size = min(len(buff), len(self._buffered))
            buff[:size], self._buffered = self._buffered[:size], self._buffered[size:]
            return size

        try:
            event = self._conn.next_event()
            while event is h11.NEED_DATA:
                try:
                    self._conn.receive_data(self._sock.recv(max(len(buff), RECV_SIZE)))
                except ConnectionError as exc:
                    exc.loglevel = logging.WARNING
                    raise
                except TimeoutError as exc:
                    raise RequestTimeout from exc
                event = self._conn.next_event()
        except h11.RemoteProtocolError as exc:
            raise werkzeug_exceptions[exc.error_status_hint] from exc

        if type(event) is h11.EndOfMessage:
            self._buffered = None  # eof
            return 0

        assert type(event) is h11.Data, event
        size = min(len(buff), len(event.data))
        data = memoryview(event.data)
        buff[:size] = data[:size]
        self._buffered = data[size:]
        return size
