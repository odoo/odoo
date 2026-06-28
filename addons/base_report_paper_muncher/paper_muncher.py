# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime as dt
import logging
import os
import os.path
import re
import selectors
import subprocess as sp
import sys
import threading
import time
from collections.abc import Sequence
from email.utils import format_datetime
from functools import cache
from io import DEFAULT_BUFFER_SIZE, BytesIO
from typing import Literal, NamedTuple
from urllib.parse import unquote

import h11

from odoo.http.router import root
from odoo.http.server import SERVER_AGENT, SERVER_SOFTWARE
from odoo.http.server_log import http_log, run_in_isolated_context, reset_thread_info
from odoo.tools.misc import find_in_path

__all__ = ['PaperMuncherInfo', 'PaperMuncherServer', 'paper_muncher']

_logger = logging.getLogger(__name__)
_logger_pipe = _logger.getChild('pipe')
_logger_process = _logger.getChild('process')

FALLBACK_BIN_PATH = '/opt/paper-muncher/bin/paper-muncher'
WRITE_TIMEOUT = 15  # seconds
SERVE_TIMEOUT = 15 * 60  # 15 minutes
CHUNK_SIZE = 8192  # 8kiB, buffer size of paper-muncher
MAX_INCOMPLETE_EVENT_SIZE = 8192  # 8kiB
GET_DOCUMENT_RE = re.compile(br"^/paper-muncher/(\.|[0-9]+)\.(?:html|xhtml|xml)$")


class PaperMuncherServer:
    __slots__ = (
        '_args',
        '_conn',
        '_deadline',
        '_documents',
        '_os_env',
        '_pdf',
        '_process',
        '_request',
        '_request_body',
        '_selector',
        '_wsgi_environ',
    )

    def __init__(self, args, os_env=None, wsgi_environ=None):
        self._args = args
        self._os_env = os_env
        self._wsgi_environ = wsgi_environ or {}
        self._process = None

    def __enter__(self):
        if self._process:
            e = "process started already"
            raise RuntimeError(e)

        self._process = sp.Popen(
            self._args,
            stdin=sp.PIPE,
            stdout=sp.PIPE,
            stderr=(
                sys.stderr
                if logging.NOTSET < _logger_process.level <= logging.DEBUG else
                sp.DEVNULL
            ),
            env=self._os_env,
        )

        self._conn = h11.Connection(
            h11.SERVER,
            max_incomplete_event_size=MAX_INCOMPLETE_EVENT_SIZE,
        )
        return self

    def __exit__(self, *_):
        if self._process and not self._process.poll():
            try:
                self._process.terminate()
                self._process.wait(1)
            except sp.TimeoutExpired:
                self._process.kill()
        self._process = None

    def serve(self, documents: Sequence[str], *, timeout: int = SERVE_TIMEOUT):
        """Serve Paper Muncher requests until the rendered PDF is returned."""
        if not self._process:
            e = "this function cannot be called outside of the context manager"
            raise RuntimeError(e)

        # HTTP worker threads have query_count set by HTTPSocket.process_request();
        # other callers (e.g. tests) do not, so initialise once before the loop.
        if not hasattr(threading.current_thread(), 'query_count'):
            reset_thread_info()

        _logger.info("Starting request loop, %d documents available", len(documents))
        self._deadline = time.monotonic() + timeout
        self._documents = documents
        self._selector = selectors.DefaultSelector()
        with self._selector:
            self._selector.register(self._process.stdout, selectors.EVENT_READ, data='stdout')

            while (
                self._process.poll() is None  # paper-muncher is alive
                and self._selector.get_map()  # stdout still registered
            ):
                events = self._selector.select(timeout=_remaining_time(self._deadline))
                if events:
                    chunk = os.read(self._process.stdout.fileno(), CHUNK_SIZE)
                    if logging.NOTSET < _logger_pipe.level <= logging.DEBUG:
                        _logger_pipe.debug("read %d bytes:\n%s", len(chunk), chunk)
                    else:
                        _logger.debug("read %d bytes", len(chunk))
                    self._conn.receive_data(chunk)
                    self._process_data()

        if exit_code := self._process.poll():
            raise sp.CalledProcessError(exit_code, self._args)

        return self._pdf

    def _process_data(self):
        while True:
            # h11's state machine guarantees that the events always
            # occur in the following order:
            # (Request => Data* => EndOfMessage)* => ConnectionClosed
            event = self._conn.next_event()
            _logger.debug("h11 current-state=%s event=%s", self._conn.states, type(event).__name__)
            match event:
                case h11.NEED_DATA:
                    break  # go back polling for more data
                case h11.Request():
                    http_log(logging.DEBUG, '[REQ] ', req=event, res=None)
                    self._request = event
                    self._request_body = bytearray()
                case h11.Data():
                    self._request_body += event.data
                case h11.EndOfMessage():
                    try:
                        self._process_request()
                    except Exception as exc:
                        exc.add_note("upon processing %s" % self._request)
                        raise
                    if self._conn.our_state is h11.MUST_CLOSE:
                        self._selector.unregister(self._process.stdout)
                        break
                    self._conn.start_next_cycle()
                case h11.ConnectionClosed():
                    self._selector.unregister(self._process.stdout)
                    break
                case _:
                    e = f"unexpected {event=} in states={self._conn.states}"
                    raise TypeError(e)

    def _process_request(self):
        if self._request.method == b'GET' and (match := GET_DOCUMENT_RE.match(self._request.target)):
            response, bytes_sent = self._handle_get_document(match[1])
        elif self._request.method == b'PUT' and self._request.target == b'/paper-muncher/output.pdf':
            response, bytes_sent = self._handle_put(self._request_body)
            _logger.info("Got a PDF of %s bytes", len(self._request_body))
        else:
            response, bytes_sent = run_in_isolated_context(
                self._handle_fallback,
                self._request,
                self._request_body,
            )
        http_log(logging.INFO, "", req=self._request, res=response, extra={
            'http_response_body': bytes_sent,
            'http_headers': (),  # already printed at [RES]
        })

    def _handle_get_document(self, document_index: str):
        """Serve one ``GET`` document request from the worker."""
        index = int(document_index) if document_index != b'.' else 0
        content = self._documents[index].encode()

        response = h11.Response(
            status_code=200,
            headers=[
                (b'Date', format_datetime(dt.datetime.now(dt.UTC), usegmt=True)),
                (b'Content-Length', str(len(content))),
                (b'Content-Type', 'text/html; charset=utf-8'),
                (b'Server', SERVER_SOFTWARE),
            ],
        )
        self._send(response)
        self._send(h11.Data(data=content))
        self._send(h11.EndOfMessage())
        return response, len(content)

    def _handle_put(self, body: bytes):
        # The PUT is a signal that the PDF is ready; acknowledge it so paper-muncher
        # starts streaming the PDF as raw bytes on stdout right after the exchange.
        assert body.startswith(b'%PDF-'), body
        self._pdf = body
        response = h11.Response(
            status_code=200,
            headers=[
                (b'Date', format_datetime(dt.datetime.now(dt.UTC), usegmt=True)),
                (b'Server', SERVER_SOFTWARE),
                (b'Content-Length', '0'),
                (b'Connection', 'close'),
            ],
        )
        self._send(response)
        self._send(h11.EndOfMessage())
        self._process.stdin.close()
        return response, 0

    def _handle_fallback(self, request: h11.Request, body: bytes):
        # Heavily inspired from odoo.http.server.HTTPSocket._make_environ
        assert request.target.startswith(b'/'), request.target
        request_uri = request.target.decode('ascii')
        path_quoted, _, query = request_uri.partition('?')
        environ = {
            'REQUEST_METHOD': request.method.decode('ascii'),
            'SCRIPT_NAME': '',
            'PATH_INFO': unquote(path_quoted, 'latin-1'),
            'QUERY_STRING': query,
            'REQUEST_URI': request_uri,
            'RAW_URI': request_uri,
            # PEP-3333 "WSGI"
            # > missing variables should be left out of the environ dict
            # 'REMOTE_ADDR': ...,
            # 'REMOTE_PORT': ...,
            # 'SERVER_NAME': ...,
            # 'SERVER_PORT': ...,
            'SERVER_PROTOCOL': 'HTTP/1.0',
            'SERVER_SOFTWARE': SERVER_SOFTWARE,
            'wsgi.version': (1, 0),
            'wsgi.url_scheme': 'http',
            'wsgi.input': BytesIO(body),
            'wsgi.errors': sys.stderr,
            'wsgi.multithread': False,
            'wsgi.multiprocess': False,
            'wsgi.run_once': False,
        }
        # can use a dict: paper-muncher sends no duplicated header name
        headers = {
            'HTTP_' + header.upper().replace(b'-', b'_').decode('ascii'):
                value.decode('latin-1')
            for header, value in request.headers
        }
        if content_type := headers.pop('HTTP_CONTENT_TYPE', ''):
            environ['CONTENT_TYPE'] = content_type
        if content_length := headers.pop('HTTP_CONTENT_LENGTH', ''):
            environ['CONTENT_LENGTH'] = content_length
        environ.update(headers)
        environ.update(self._wsgi_environ)

        response = None
        x_sendfile = None
        def start_response(status, headers, exc_info=None):  # noqa: E306
            nonlocal response, x_sendfile
            status_code = int(status.partition(' ')[0])
            headers = [(_normalize_header(h), v) for h, v in headers]

            def find_header(header):
                return next((v for h, v in headers if h == header), None)
            if find_header(b'Connection'):
                e = "the WSGI app cannot set the Connection header"
                raise ValueError(e)
            if find_header(b'Upgrade'):
                e = "paper-muncher does not support websocket"
                raise ValueError(e)
            if not find_header(b'Date'):
                headers.insert(0, (b'Date', format_datetime(dt.datetime.now(dt.UTC), usegmt=True)))
            if not find_header(b'Server'):
                headers.append((b'Server', SERVER_AGENT))
            x_sendfile = find_header(b'X-Sendfile')
            if x_sendfile:
                index = next((i for i, (h, v) in enumerate(headers) if h == b'Content-Length'))
                headers[index] = (b'Content-Length', str(os.path.getsize(x_sendfile)))

            response = h11.Response(status_code=status_code, headers=headers)
            http_log(logging.DEBUG, '[RES] ', req=self._request, res=response)

        response_body = root(environ, start_response)  # call Odoo as public user
        bytes_sent = 0
        deadline = time.monotonic() + WRITE_TIMEOUT
        self._send(response, deadline=deadline)

        try:  # noqa: PLW0717
            if x_sendfile:
                response_chunks = list(response_body)
                assert not any(response_chunks), response_chunks
                with open(x_sendfile, 'rb') as f:
                    while chunk := f.read(DEFAULT_BUFFER_SIZE):
                        self._send(h11.Data(data=chunk), deadline=deadline)
                        bytes_sent += len(chunk)
            else:
                for chunk in response_body:
                    self._send(h11.Data(data=chunk), deadline=deadline)
                    bytes_sent += len(chunk)
            if hasattr(response_body, 'close'):
                response_body.close()
            self._send(h11.EndOfMessage(), deadline=deadline)
        except Exception:
            self._conn.send_failed()
            raise

        return response, bytes_sent

    def _send(self, event, *, deadline=None) -> None:
        data = self._conn.send(event)
        memview = memoryview(data)
        bytes_written = 0

        if deadline is None:
            deadline = time.monotonic() + WRITE_TIMEOUT

        with selectors.DefaultSelector() as selector:  # TODO: maybe reuse _selector
            selector.register(self._process.stdin.fileno(), selectors.EVENT_WRITE)
            while bytes_written < len(data):
                events = selector.select(timeout=_remaining_time(deadline))
                if not events:
                    e = "Timeout exceeded while writing to subprocess"
                    raise TimeoutError(e)
                bytes_written += os.write(self._process.stdin.fileno(), memview[bytes_written:])
            self._process.stdin.flush()

        if logging.NOTSET < _logger_pipe.level <= logging.DEBUG:
            _logger_pipe.debug("wrote %d bytes:\n%s", bytes_written, data)
        else:
            _logger.debug("wrote %d bytes", bytes_written)


def _remaining_time(deadline: float) -> float:
    """Return remaining seconds until a monotonic deadline.

    :param deadline: Absolute timestamp from :func:`time.monotonic`.
    :raises TimeoutError: When the deadline has been reached.
    """
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError
    return max(1, remaining)


def _normalize_header(header: str) -> bytes:
    # FIXME: paper-muncher uses case-sensitive headers
    return header.replace('-', ' ').title().replace(' ', '-').encode('ascii')


class PaperMuncherInfo(NamedTuple):
    state: Literal['ok', 'install']
    bin: str
    version: str


@cache
def paper_muncher() -> PaperMuncherInfo:
    bin_path = ''
    version = ''
    try:  # noqa: PLW0717
        try:
            bin_path = find_in_path('paper-muncher')
        except OSError as exc:
            if not os.path.isfile(FALLBACK_BIN_PATH):
                e = "paper-muncher binary not found in PATH"
                raise RuntimeError(e) from exc
            bin_path = FALLBACK_BIN_PATH

        result = sp.run([bin_path, '--version'], stdout=sp.PIPE, stderr=sp.DEVNULL, check=True)
        version = result.stdout.decode('utf-8', errors='replace').strip()
    except (RuntimeError, OSError, sp.SubprocessError):
        _logger.info("You need paper-muncher to print a pdf version of the reports.",
                     exc_info=_logger.isEnabledFor(logging.DEBUG))
        return PaperMuncherInfo(state='install', bin=bin_path, version=version)

    _logger.info("Will use the paper-muncher binary at %s", bin_path)
    return PaperMuncherInfo(state='ok', bin=bin_path, version=version)
