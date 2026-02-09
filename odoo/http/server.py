import io
import logging
import pprint
import sys
import threading
import time
from contextlib import suppress
from functools import partial
from http import HTTPStatus
from wsgiref.handlers import format_date_time
from wsgiref.simple_server import sys_version

import h11
from urllib3.util import parse_url
from werkzeug.exceptions import default_exceptions as werkzeug_exceptions
from werkzeug.middleware.proxy_fix import ProxyFix

import odoo
import odoo.release
from odoo.tools import config, real_time

from .log import http_log
from .router import root

_logger = logging.getLogger(__name__)

RECV_SIZE = 8192
MAX_BUFFER_SIZE = 16384

SERVER_AGENT = ' '.join((
    f'odoo/{odoo.release.series}',
    h11.PRODUCT_ID,
    sys_version,
)).encode()

_NO_BODY_STATUS = {
    HTTPStatus.CONTINUE,
    HTTPStatus.SWITCHING_PROTOCOLS,
    HTTPStatus.PROCESSING,
    HTTPStatus.EARLY_HINTS,
    HTTPStatus.NO_CONTENT,
    HTTPStatus.RESET_CONTENT,
    HTTPStatus.NOT_MODIFIED,
}


def find_header(
    headers: list[tuple[bytes, bytes]],
    name: bytes,
    default: bytes | None = None,
) -> bytes | None:
    return next((value for header, value in headers if header == name), default)


class HTTPSocket:
    def __init__(self, client_sock, client_addr, *, prelude=b''):
        self.sock = client_sock
        self.addr = client_addr
        self.ip = client_addr[0]

        self.conn = h11.Connection(h11.SERVER, max_incomplete_event_size=MAX_BUFFER_SIZE)
        if prelude:
            self.conn.receive_data(prelude)

        self._request_line = None
        self.upgrade = None

    def _make_environ(self, h11request):
        # h11 made sure the target, http_version, header names and
        # content-length only contain valid ascii characters. It didn't
        # verified any other header value as HTTP (RFC9110) states they
        # can be "opaque" data. Decoding them as latin-1 gives the
        # correct string for US-ASCII and ISO-8859-1 which are the two
        # commonly used charset for header values. Using latin-1 doesn't
        # break RFC2047/RFC5987/RFC8187-encoding (base64 or %-encoding)
        # and just leaves the string unparsed. HTTP headers that use
        # other (non-standard) charsets are passed to the application as
        # latin-1 string and must be re-encoded by the application. This
        # is in line with the WSGI spec.

        *_, path_info, query_string, _ = parse_url(h11request.target.decode('ascii'))
        environ = {
            'REQUEST_METHOD': h11request.method.decode('ascii'),
            'SCRIPT_NAME': '',
            'PATH_INFO': path_info,
            'QUERY_STRING': query_string or '',
            'REMOTE_ADDR': self.addr[0],
            'REMOTE_PORT': self.addr[1],
            'SERVER_NAME': config['http_interface'],
            'SERVER_PORT': config['http_port'],
            'SERVER_PROTOCOL': 'HTTP/' + h11request.http_version.decode('ascii'),
            'SERVER_SOFTWARE': SERVER_AGENT,
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

        environ.update({
            'HTTP_' + header.upper().replace(b'-', b'_').decode('ascii'): value.decode('latin-1')
            for header, value in h11request.headers
        })
        if content_type := environ.pop('HTTP_CONTENT_TYPE', ''):
            environ['CONTENT_TYPE'] = content_type
        if content_length := environ.pop('HTTP_CONTENT_LENGTH', ''):
            environ['CONTENT_LENGTH'] = content_length

        if config['proxy_mode'] and environ.get('HTTP_X_FORWARDED_HOST'):
            pf = ProxyFix(lambda environ, start_response: (), x_for=1, x_proto=1, x_host=1)
            pf(environ, lambda status, headers: None)  # it updates environ
            self.ip = environ['REMOTE_ADDR']

        return environ

    def process_request(self):
        t0 = real_time()
        current_thread = threading.current_thread()
        current_thread.query_count = 0
        current_thread.query_time = 0
        current_thread.perf_t0 = t0
        current_thread.cursor_mode = None

        # Receive the HTTP request
        try:
            h11request = self.conn.next_event()
            while h11request is h11.NEED_DATA:
                self.conn.receive_data(self.sock.recv(RECV_SIZE))
                h11request = self.conn.next_event()
            if type(h11request) is h11.ConnectionClosed:
                return
            assert type(h11request) is h11.Request, h11request
        except h11.RemoteProtocolError as exc:
            # There is an error in the HTTP request. Fail with a 4xx and
            # close the socket. Do not bother with a reason or a body.
            with suppress(BrokenPipeError):
                self.sock.sendall(self.conn.send(h11.Response(
                    status_code=exc.status_code_hint,
                    headers=[
                        (b'date', format_date_time(time.time()).encode()),
                        (b'server', SERVER_AGENT),
                        (b'connection', b'close'),
                        (b'content-length', b'0'),
                    ],
                )))
                http_log(_logger, logging.INFO, '', extra={
                    'remote_addr': self.ip,
                    'http_request_line': '"- - HTTP/?"',
                    'http_response_status': exc.status_code_hint,
                    'http_response_body': 0,
                    'query_count': 0,
                    'query_time': 0,
                    'remaining_time': real_time() - t0 - current_thread.query_time,
                }, exc_info=_logger.isEnabledFor(logging.DEBUG))
                assert not self.conn.send(h11.EndOfMessage())
                assert self.conn.our_state is h11.MUST_CLOSE, self.conn.our_state
            return

        # Craft the WSGI environ
        wsgi_environ = self._make_environ(h11request)
        self._request_line = (b'"%s %s HTTP/%s"' % (
            h11request.method,
            h11request.target,
            h11request.http_version,
        )).decode()

        if self.conn.client_is_waiting_for_100_continue:
            # The request has header "Expect: 100-continue". Send a
            # 100 Continue response now as we are just before forwarding
            # the request to the WSGI application.
            # Maybe we should instead let the WSGI application send this
            # 100-Continue info response, and we would only does it
            # ourselves if it calls start_response() and that the
            # 100-Continue response wasn't sent yet.
            self.sock.sendall(self.conn.send(h11.InformationalResponse(
                status_code=HTTPStatus.CONTINUE,
                headers=[
                    (b'date', format_date_time(time.time()).encode()),
                    (b'server', SERVER_AGENT),
                ],
            )))
            http_log(_logger, logging.DEBUG, '[100] ', extra={
                'remote_addr': self.ip,
                'http_request_line': self._request_line,
                'http_response_status': 100,
                'http_response_body': 0,
                'query_count': 0,
                'query_time': 0,
                'remaining_time': real_time() - t0,
            })

        # Pass the request into the WSGI application. It'll call our
        # start_response() with the http response line and headers, then
        # return an iterable object containing the body.
        http_log(_logger, logging.DEBUG, '[REQ] ', extra={
            'remote_addr': self.ip,
            'http_request_line': self._request_line,
            'query_count': 0,
            'query_time': 0,
            'remaining_time': real_time() - t0,
        })
        wsgi_response = root(wsgi_environ, self.start_response)

        if self.conn.our_state is h11.SWITCHED_PROTOCOL:
            # The WSGI applicated called start_response() with
            # > HTTP/1.1 101 Switching Protocols
            # > Connection: upgrade
            # > Upgrade: websocket
            # HTTP-wise there is nothing left to do.
            if hasattr(wsgi_response, 'close'):
                wsgi_response.close()  # werkzeug call_on_close()
            http_log(_logger, logging.DEBUG, '[END] ', extra={
                'remote_addr': self.ip,
                'http_request_line': self._request_line,
            })
            return

        # Iter over the iterable object the WSGI application gave us. It
        # contains the body that we are yet to send on the network.
        bytes_sent = 0
        response_iter = iter(wsgi_response)
        try:
            while True:
                try:
                    chunk = next(response_iter)
                except StopIteration:
                    # There are no more data to send. Close the response
                    # and http stream.
                    if hasattr(wsgi_response, 'close'):
                        wsgi_response.close()  # werkzeug call_on_close()
                    if data := self.conn.send(h11.EndOfMessage()):
                        self.sock.sendall(data)
                    break
                else:
                    # There are some data, send them.
                    if data := self.conn.send(h11.Data(chunk)):
                        self.sock.sendall(data)
                    bytes_sent += len(chunk)
        except Exception as exc:  # noqa: BLE001
            # A fatal error occured while sending the body, mark the
            # connection failed and close it.
            self.conn.send_failed()
            http_log(_logger, logging.ERROR, '[END] ', extra={
                'remote_addr': self.ip,
                'http_request_line': self._request_line,
                'http_response_body': bytes_sent,
                'query_count': current_thread.query_count,
                'query_time': current_thread.query_time,
                'remaining_time': real_time() - t0 - current_thread.query_time,
                'cursor_mode': current_thread.cursor_mode,
            }, exc_info=exc)
        else:
            http_log(_logger, logging.DEBUG, '[END] ', extra={
                'remote_addr': self.ip,
                'http_request_line': self._request_line,
                'http_response_body': bytes_sent,
                'query_count': current_thread.query_count,
                'query_time': current_thread.query_time,
                'remaining_time': real_time() - t0 - current_thread.query_time,
                'cursor_mode': current_thread.cursor_mode,
            })

    def start_response(
        self,
        status: str,
        response_headers: list[tuple[str, str]],
        exc_info=None,
    ):
        if _logger.isEnabledFor(logging.DEBUG):
            _logger.debug("%s\n%s", status, pprint.pformat(response_headers))
        status_code, _, reason = status.partition(' ')
        status_code = HTTPStatus(int(status_code))

        # Do the wsgi-encoding dance back, see _make_environ()
        response_headers: list[tuple[bytes, bytes]] = [
            (header.encode('ascii').lower(), value.encode('latin-1'))
            for header, value in response_headers
        ]
        find_header_ = partial(find_header, response_headers)

        # Add the mandatory HTTP headers
        if (cnx := find_header_(b'connection')) is not None:
            if cnx.lower() == b'upgrade':
                self.upgrade = find_header(response_headers, b'upgrade')
                if self.upgrade is None:
                    e = "the Upgrade header is mandatory with Connection: upgrade"
                    raise ValueError(e)
            elif cnx.lower() != b'close':
                e = f"invalid Connection header: {cnx}"
                raise ValueError(e)
        else:
            response_headers.append((b'connection', b'close'))
        if find_header_(b'server') is None:
            response_headers.append((b'server', SERVER_AGENT))
        if find_header_(b'date') is None:
            date = format_date_time(time.time()).encode()
            response_headers.insert(0, (b'date', date))

        # Send and log the response
        h11_response_cls = (
            h11.InformationalResponse
            if status_code.is_informational else
            h11.Response
        )
        h11_response = h11_response_cls(
            status_code=status_code,
            reason=reason,
            headers=response_headers,
        )
        self.sock.sendall(self.conn.send(h11_response))

        current_thread = threading.current_thread()
        http_log(_logger, logging.INFO, '', extra={
            'remote_addr': self.ip,
            'http_request_line': self._request_line,
            'http_response_status': status_code,
            'http_response_body': (
                    cl if (cl := find_header_(b'content-length')) is not None
                else 0 if status_code in _NO_BODY_STATUS
                else 'stream'),
            'query_count': current_thread.query_count,
            'query_time': current_thread.query_time,
            'remaining_time': real_time() - current_thread.perf_t0 - current_thread.query_time,
            'cursor_mode': current_thread.cursor_mode,
        })


class HTTPBodyReader(io.RawIOBase):
    def __init__(self, sock, conn):
        self._sock = sock
        self._conn = conn
        self._buffered = bytearray()
        self._eof_received = False

    def readable(self) -> bool:
        return True

    # The read() and readinto() look similar but are different enough to
    # warrant their own dedicated methods. Deal with it and keep them in
    # sync!

    def read(self, size: int = -1):
        # /!\ Keep me sync with readinto() /!\

        if self._eof_received:
            return b''

        if self._buffered:
            # TODO: Py3.15: return self._buffered.take_bytes(size)
            data = bytes(self._buffered[:size if size != -1 else None])
            del self._buffered[:size if size != -1 else None]
            return data

        try:
            event = self._conn.next_event()
            while event is h11.NEED_DATA:
                self._conn.receive_data(self._sock.recv(max(size, RECV_SIZE)))
                event = self._conn.next_event()
        except h11.RemoteProtocolError as exc:
            raise werkzeug_exceptions[exc.status_code_hint] from exc

        if type(event) is h11.EndOfMessage:
            self._eof_received = True
            return b''

        assert type(event) is h11.Data, event
        self._buffered[:] = event.data[size if size != -1 else None:]
        return event.data[:size if size != -1 else None]

    def readinto(self, buff):
        # /!\ Keep me sync with read() /!\

        if self._eof_received:
            return 0

        if self._buffered:
            size = min(len(buff), len(self._buffered))
            # TODO: Py3.15: buff[:size] = self._buffered.take_bytes(size)
            buff[:size] = self._buffered[:size]
            del self._buffered[:size]
            return size

        try:
            event = self._conn.next_event()
            while event is h11.NEED_DATA:
                self._conn.receive_data(self._sock.recv(max(len(buff), RECV_SIZE)))
                event = self._conn.next_event()
        except h11.RemoteProtocolError as exc:
            raise werkzeug_exceptions[exc.status_code_hint] from exc

        if type(event) is h11.EndOfMessage:
            self._eof_received = True
            return 0

        assert type(event) is h11.Data, event
        size = min(len(buff), len(event.data))
        buff[:size] = event.data[:size]
        self._buffered[:] = event.data[size:]
        return size
