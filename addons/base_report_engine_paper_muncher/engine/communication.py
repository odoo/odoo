# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import os
import selectors
import threading
import re
import time
from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime, timezone
from email.utils import format_datetime
from typing import BinaryIO, Optional, IO
from wsgiref.types import WSGIEnvironment
from lxml import etree, html
from PyPDF2 import PdfMerger

from werkzeug.test import create_environ, run_wsgi_app

import odoo
from odoo.http import request
from odoo.http.router import root

_logger = logging.getLogger(__name__)

SERVER_SOFTWARE = f'{odoo.release.product_name}/{odoo.release.version}'
DEFAULT_READ_TIMEOUT = 60  # seconds
DEFAULT_READLINE_TIMEOUT = 60 * 15  # seconds (15 minutes is for the put request)
DEFAULT_WRITE_TIMEOUT = 30  # seconds
DEFAULT_CHUNK_SIZE = 4096  # bytes
HTML_BODY_PATTERN = re.compile(
    r'(?s)(.*?)(<body[^>]*>)(.*?)(</body>)(.*)', re.IGNORECASE)

def remaining_time(deadline: float) -> float:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError("Timeout exceeded")
    return remaining


def readline_with_timeout(
        file_object: IO[bytes],
        timeout: int = DEFAULT_READLINE_TIMEOUT,
) -> bytes:
    """Read a full line ending with '\\n' from a file-like object within a timeout.

    :param IO[bytes] file_object: File-like object to read from (must be in binary mode).
    :param int timeout: Max seconds to wait for line data.
    :return: A line of bytes ending in '\\n'.
    :rtype: bytes
    :raises TimeoutError: If timeout is reached before a line is read.
    :raises EOFError: If EOF is reached before a line is read.
    """
    fd = file_object.fileno()
    deadline = time.monotonic() + timeout
    line_buffer = bytearray()

    with selectors.DefaultSelector() as selector:
        selector.register(fd, selectors.EVENT_READ)

        while selector.select(timeout=remaining_time(deadline)):
            next_byte = os.read(fd, 1)
            if not next_byte:
                raise EOFError("EOF reached while reading line")

            line_buffer += next_byte
            if next_byte == b'\n':
                break
        else:
            raise TimeoutError("Timeout while reading line from subprocess")
    _logger.debug(
        "Elapsed time reading line: %.3f seconds",
        time.monotonic() - (deadline - timeout)
    )
    return bytes(line_buffer)


def read_all_with_timeout(
        file_object: BinaryIO,
        timeout: int = DEFAULT_READ_TIMEOUT,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> bytes:
    """Read all data from a file-like object until EOF, with a timeout per chunk.

    :param BinaryIO file_object: File-like object to read from.
    :param int timeout: Timeout in seconds for the entire read operation.
    :param int chunk_size: Number of bytes to read per chunk.
    :return: All bytes read until EOF.
    :rtype: bytes
    :raises TimeoutError: If no data is read within the timeout period.
    """
    fd = file_object.fileno()
    data = bytearray()
    deadline = time.monotonic() + timeout

    with selectors.DefaultSelector() as selector:
        selector.register(fd, selectors.EVENT_READ)
        while selector.select(timeout=remaining_time(deadline)):
            chunk = os.read(fd, chunk_size)
            if not chunk:
                break
            data.extend(chunk)
        else:
            raise TimeoutError("Timeout while reading data")
    _logger.debug(
        "Elapsed time reading: %.3f seconds",
        time.monotonic() - (deadline - timeout)
    )
    return bytes(data)


def write_with_timeout(
        file_object: BinaryIO,
        data: bytes,
        timeout: int = DEFAULT_WRITE_TIMEOUT
) -> None:
    """Write all data to a file-like object within a timeout, using selectors.

    :param BinaryIO file_object: File-like object to write to.
    :param bytes data: Bytes to write.
    :param int timeout: Max seconds to wait for write readiness.
    :raises TimeoutError: If writing cannot complete within timeout.
    """
    fd = file_object.fileno()
    total_written = 0
    deadline = time.monotonic() + timeout

    with selectors.DefaultSelector() as selector:
        selector.register(fd, selectors.EVENT_WRITE)

        while total_written < len(data):
            events = selector.select(timeout=remaining_time(deadline))
            if not events:
                raise TimeoutError("Timeout exceeded while writing to subprocess")

            written = os.write(fd, data[total_written:])
            if written == 0:
                raise RuntimeError("Write returned zero bytes")
            total_written += written
    _logger.debug(
        "Elapsed time writing: %.3f seconds",
        time.monotonic() - (deadline - timeout)
    )


def consume_paper_muncher_request(
        stdout: IO[bytes],
        timeout: int = DEFAULT_READLINE_TIMEOUT
) -> None:
    """Read and discard all header lines from a Paper Muncher request.

    :param IO[bytes] stdout: File-like stdout stream from Paper Muncher.
    :param int timeout: Timeout in seconds for each line read.
    :return: None
    :rtype: None
    """
    deadline = time.monotonic() + timeout
    while line := readline_with_timeout(stdout, timeout=int(remaining_time(deadline))):
        _logger.debug("Paper Muncher request line: %s", line.rstrip())
        if line == b"\r\n":
            return
        if not line:
            raise EOFError("EOF reached while reading request headers")


def read_paper_muncher_request(
        stdout: BinaryIO,
        timeout: int = DEFAULT_READLINE_TIMEOUT,
) -> Optional[str]:
    """Read the HTTP-like request line from Paper Muncher and return the path.

    :param BinaryIO stdout: File-like stdout stream from Paper Muncher.
    :param int timeout: Timeout in seconds for each line read.
    :return: The requested asset path, or ``None`` if the method is PUT.
    :rtype: str or None
    :raises EOFError: If no request line is found.
    :raises ValueError: If the request format is invalid or the method is unsupported.
    """
    deadline = time.monotonic() + timeout
    first_line_bytes = readline_with_timeout(stdout, timeout=int(remaining_time(deadline)))

    if not first_line_bytes:
        raise EOFError("EOF reached while reading first line from subprocess")

    first_line = first_line_bytes.decode('utf-8').rstrip('\r\n')

    _logger.debug("First Paper Muncher request line: %s", first_line)

    parts = first_line.split(' ')
    if len(parts) != 3:
        raise ValueError(
            f"Invalid HTTP request line from Paper Muncher: {first_line}")

    method, path, _ = parts
    if method == 'PUT':
        path = None
    elif method != 'GET':
        raise ValueError(
            f"Unexpected HTTP method: {method} in line: {first_line}")

    consume_paper_muncher_request(stdout, timeout=int(remaining_time(deadline)))

    return path


@contextmanager
def preserve_thread_data():
    """Context manager to preserve and restore thread-local data used by Odoo.
    """
    current_thread = threading.current_thread()
    attrs_to_preserve = [
        'query_count',
        'query_time',
        'perf_t0',
        'cursor_mode',
        'dbname',
        'uid',
    ]

    saved = {}
    missing = set()

    for attr in attrs_to_preserve:
        if hasattr(current_thread, attr):
            saved[attr] = getattr(current_thread, attr)
        else:
            missing.add(attr)

    try:
        yield
    finally:
        for attr, value in saved.items():
            setattr(current_thread, attr, value)
        for attr in missing:
            if hasattr(current_thread, attr):
                delattr(current_thread, attr)


def generate_environ(path: str) -> WSGIEnvironment:
    """Generate a WSGI environment for the given path.
    This is used to simulate an HTTP request to the Odoo application.

    :param str path: The HTTP request path.
    :return: The WSGI environment dictionary.
    :rtype: WSGIEnvironment
    """
    url, _, query_string = path.partition('?')
    current_environ = request.httprequest.environ
    environ = create_environ(
        method='GET',
        path=url,
        query_string=query_string,
        headers={
            'Host': current_environ['HTTP_HOST'],
            'User-Agent': SERVER_SOFTWARE,
            'http_cookie': current_environ['HTTP_COOKIE'],
            'remote_addr': current_environ['REMOTE_ADDR'],
        }
    )
    return environ

def generate_odoo_http_response(
        request_path: str
) -> Generator[bytes, None, None]:
    """Simulate an internal HTTP GET request to the Odoo WSGI app and yield
    the HTTP response headers and body as bytes.

    :param str request_path: Path to query within the Odoo app.
    :yields: Chunks of the full HTTP response to the simulated request.
    :rtype: Generator[bytes, None, None]
    """
    with preserve_thread_data():
        response_iterable, http_status, http_response_headers = run_wsgi_app(
            root, generate_environ(request_path)
        )

    if "X-Sendfile" in http_response_headers:
        with open(http_response_headers["X-Sendfile"], 'rb') as file:
            http_response_status_line_and_headers = (
                f"HTTP/1.1 {http_status}\r\n"
                f"Date: {format_datetime(datetime.now(timezone.utc), usegmt=True)}\r\n"
                f"Server: {SERVER_SOFTWARE}\r\n"
                f"Content-Length: {os.path.getsize(http_response_headers['X-Sendfile'])}\r\n"
                f"Content-Type: {http_response_headers['Content-Type']}\r\n"
                "\r\n"
            ).encode()
            yield http_response_status_line_and_headers
            yield from file
    else:
        now = datetime.now(timezone.utc)
        http_response_status_line_and_headers = (
            f"HTTP/1.1 {http_status}\r\n"
            f"Date: {format_datetime(now, usegmt=True)}\r\n"
            f"Server: {SERVER_SOFTWARE}\r\n"
            f"Content-Length: {http_response_headers['Content-Length']}\r\n"
            f"Content-Type: {http_response_headers['Content-Type']}\r\n"
            "\r\n"
        ).encode()

        yield http_response_status_line_and_headers
        yield from response_iterable


def partition_on_body(html: str) -> tuple[str, str, str]:
    """Extract the content of the <body> tag from HTML as a tuple of
    (before_body, body_content, after_body)

    :param str html: Full HTML document.
    :return: Tuple of (open_body, body_content, close_body)
    :rtype: tuple[str, str, str]
    """
    if not html:
        return "", "", ""

    match = HTML_BODY_PATTERN.fullmatch(html)
    if not match:
        return html, "", ""

    pre, open_tag, body_content, close_tag, post = match.groups()
    return pre + open_tag, body_content, close_tag + post


def make_multi_docs_html(bodies, header='', footer=''):
    """Combine multi header and footer with their respective bodies.

    :param bodies: List of HTML body strings.
    :param header: HTML header fragment.
    :param footer: HTML footer fragment.
    :return: Combined HTML document.
    :rtype: list[str]
    """

    footers_encapsulated = partition_on_body(footer)[1]
    footers_tree = html.fromstring(footers_encapsulated)
    footers = []
    for footer in footers_tree.findall('./div'):
        # encapsulate each footer in a div with the same classes as the englobing divs
        footers.append(etree.tostring(footer, encoding='unicode'))

    headers_encapsulated = partition_on_body(header)[1]
    headers_tree = html.fromstring(headers_encapsulated)
    headers = []
    for header in headers_tree.findall('./div'):
        # encapsulate each header in a div with the same classes as the englobing divs
        headers.append(etree.tostring(header, encoding='unicode'))

    is_same_length_h = (len(headers) == len(bodies))
    is_same_length_f = (len(footers) == len(bodies))

    documents = []
    for i, body in enumerate(bodies):
        open_body, body, close_body = partition_on_body(body)
        header_fragment = headers[i] if is_same_length_h else (headers[0] if headers else '')
        footer_fragment = footers[i] if is_same_length_f else (footers[0] if footers else '')
        documents.append("".join((
            open_body,
            header_fragment,
            body,
            footer_fragment,
            close_body,
            "\n",
        )))

    return documents