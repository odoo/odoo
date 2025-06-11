"""
The :mod:`odoo.tools.paper_muncher` module provides utilities for
interacting with Paper Muncher, a subprocess used to render
HTML content into PDF format.

It includes functions to read and write data to the subprocess,
handle HTTP-like requests, and generate responses using the
Odoo WSGI application.
"""
import logging
import os
import re
import selectors
import subprocess
import threading
import time
from collections.abc import Generator, Mapping, Sequence
from contextlib import contextmanager
from datetime import datetime, timezone
from email.utils import format_datetime
from itertools import count
from typing import BinaryIO, Optional
from wsgiref.types import WSGIEnvironment

from werkzeug.test import create_environ, run_wsgi_app

import odoo
from odoo.http import request, root

from .misc import find_in_path

_logger = logging.getLogger(__name__)

SERVER_SOFTWARE = f'{odoo.release.product_name}/{odoo.release.version}'
DEFAULT_READ_TIMEOUT = 60  # seconds
DEFAULT_READLINE_TIMEOUT = 60 * 15  # seconds (15 minutes is for the put request)
DEFAULT_WRITE_TIMEOUT = 30  # seconds
DEFAULT_CHUNK_SIZE = 4096  # bytes
HTML_BODY_PATTERN = re.compile(
    r'(?s)(.*?)(<body[^>]*>)(.*?)(</body>)(.*)', re.IGNORECASE)
FALLBACK_BINARY = '/opt/paper-muncher/bin/paper-muncher'


def get_paper_muncher_binary() -> Optional[str]:
    """Find and validate the Paper Muncher binary."""
    try:
        binary = find_in_path('paper-muncher')
    except OSError:
        _logger.debug("Cannot locate in path paper-muncher", exc_info=True)
        binary = FALLBACK_BINARY

    try:
        subprocess.run(
            [binary, '--version'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
    except subprocess.CalledProcessError:
        _logger.debug("Cannot use paper-muncher", exc_info=True)
        return None

    return binary


def can_use_paper_muncher() -> bool:
    """Check if Paper Muncher binary is available and usable.

    :return: True if Paper Muncher is in debug session and available, False otherwise.
    :rtype: bool
    """
    if not request or 'paper-muncher' not in request.session.debug:
        return False
    return bool(get_paper_muncher_binary())


def remaining_time(deadline: float) -> float:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError("Timeout exceeded")
    return remaining


def readline_with_timeout(
    file_object: BinaryIO,
    timeout: int = DEFAULT_READLINE_TIMEOUT,
) -> bytes:
    """Read a full line ending with '\\n' from a file-like object within a timeout.

    :param BinaryIO file_object: File-like object to read from (must be in binary mode).
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
    stdout: BinaryIO,
    timeout: int = DEFAULT_READLINE_TIMEOUT
) -> None:
    """Read and discard all header lines from a Paper Muncher request.

    :param BinaryIO stdout: File-like stdout stream from Paper Muncher.
    :param int timeout: Timeout in seconds for each line read.
    :return: None
    :rtype: None
    """
    deadline = time.monotonic() + timeout
    while line := readline_with_timeout(stdout, timeout=remaining_time(deadline)):
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
    first_line_bytes = readline_with_timeout(stdout, timeout=remaining_time(deadline))

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

    consume_paper_muncher_request(stdout, timeout=remaining_time(deadline))

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


def run_paper_muncher(
    paperformat,
    bodies: Sequence[str],
    header: str = '',
    footer: str = '',
    landscape: bool = False,
    specific_paperformat_args: Optional[Mapping] = None,
    set_viewport_size: Optional[str] = None,
) -> bytes:
    """Render a PDF from HTML content using Paper Muncher subprocess.

    :param paperformat: Odoo report paperformat object (may have format, width/height).
    :param Sequence[str] bodies: List of HTML body strings.
    :param str header: HTML header fragment.
    :param str footer: HTML footer fragment.
    :param bool landscape: Whether to use landscape layout.
    :param Optional[Mapping] specific_paperformat_args: Optional override arguments.
    :param Optional[str] set_viewport_size: Optional viewport string (currently unused).
    :return: PDF bytes returned by Paper Muncher.
    :rtype: bytes
    :raises RuntimeError: If Paper Muncher fails during any phase.
    """
    header = partition_on_body(header)[1]
    footer = partition_on_body(footer)[1]
    out = []
    for html in bodies:
        open_body, body, close_body = partition_on_body(html)
        out.extend((open_body, header, body, footer, close_body, "\n"))
    content = "".join(out)

    extra_args = ['--scale', '72dpi']  # bypass DPI scaling to correspond to WKHTMLTOPDF
    if landscape:
        extra_args += ['--orientation', 'landscape']

    if paperformat and paperformat.format:
        if paperformat.format != 'custom':
            extra_args += ['--paper', str(paperformat.format)]
        elif paperformat.page_height and paperformat.page_width:
            extra_args += ['--width', f'{paperformat.page_width}mm']
            extra_args += ['--height', f'{paperformat.page_height}mm']

    if not (binary := get_paper_muncher_binary()):
        raise RuntimeError(
            "Paper Muncher binary not found or not usable. "
            "Ensure it is installed and available in the system PATH."
        )

    with subprocess.Popen(
        [binary, "print", "pipe:", '-o', "pipe:"] + extra_args,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ) as process:
        # Phase 1: send HTML content headers and body
        try:
            consume_paper_muncher_request(process.stdout)
        except EOFError as early_eof:
            raise RuntimeError(
                "Paper Muncher terminated prematurely (phase 1)"
            ) from early_eof

        if process.poll() is not None:
            raise RuntimeError(
                "Paper Muncher crashed before receiving content")

        now = datetime.now(timezone.utc)
        response_headers = (
            b"HTTP/1.1 200 OK\r\n"
            b"Content-Length: %(length)d\r\n"
            b"Content-Type: text/html\r\n"
            b"Date: %(date)s\r\n"
            b"Server: %(server)s\r\n"
            b"\r\n"
        ) % {
            b'length': len(content.encode()),
            b'date':  format_datetime(now, usegmt=True).encode(),
            b'server': SERVER_SOFTWARE.encode(),
        }

        write_with_timeout(process.stdin, response_headers)
        write_with_timeout(process.stdin, content.encode())
        process.stdin.flush()

        if process.poll() is not None:
            raise RuntimeError(
                "Paper Muncher crashed while sending HTML content")

        # Phase 2: serve asset requests until the pdf is ready
        for request_no in count(start=1):
            try:
                path = read_paper_muncher_request(process.stdout)
            except (EOFError, TimeoutError):
                process.kill()
                process.wait()
                raise

            if path is None:
                break

            for chunk in generate_odoo_http_response(path):
                write_with_timeout(process.stdin, chunk)
            process.stdin.flush()

            if process.poll() is not None:
                raise RuntimeError(
                    "Paper Muncher crashed while serving asset"
                    f" {request_no}: {path}"
                )

        # Phase 3: send final OK and read PDF bytes
        now = datetime.now(timezone.utc)
        final_response = (
            b"HTTP/1.1 200 OK\r\n"
            b"Date: %(date)s\r\n"
            b"Server: %(server)s\r\n"
            b"\r\n"
        ) % {
            b'date': format_datetime(now, usegmt=True).encode(),
            b'server': SERVER_SOFTWARE.encode(),
        }

        write_with_timeout(process.stdin, final_response)
        process.stdin.flush()
        process.stdin.close()

        if process.poll() is not None:
            raise RuntimeError("Paper Muncher crashed before returning PDF")

        try:
            rendered_content = read_all_with_timeout(process.stdout)
            stderr_output = read_all_with_timeout(process.stderr)
        except (EOFError, TimeoutError):
            process.kill()
            process.wait()
            raise

        if stderr_output:
            _logger.warning(
                "Paper Muncher error output: %s",
                stderr_output.decode('utf-8', errors='replace'),
            )

        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            _logger.warning(
                "Paper Muncher did not terminate in time,"
                "forcefully killed it"
            )

        if process.returncode != 0:
            _logger.warning(
                "Paper Muncher exited with code %d",
                process.returncode,
            )

        if not rendered_content.startswith(b'%PDF-'):
            raise RuntimeError(
                "Paper Muncher did not return valid PDF content"
            )

        return rendered_content
