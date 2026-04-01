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
import subprocess

from werkzeug.test import create_environ, run_wsgi_app

import odoo
from odoo.http import request
from odoo.http.router import root

_logger = logging.getLogger(__name__)

SERVER_SOFTWARE = f'{odoo.release.product_name}/{odoo.release.version}'
DEFAULT_READ_TIMEOUT = 15  # seconds
DEFAULT_READLINE_TIMEOUT = 1 * 15 # seconds (15 minutes is for the put request)
DEFAULT_WRITE_TIMEOUT = 15  # seconds
DEFAULT_CHUNK_SIZE = 4096  # bytes
LOG_PAPER_MUNCHER = False
HTML_BODY_PATTERN = re.compile(
    r'(?s)(.*?)(<body[^>]*>)(.*?)(</body>)(.*)', re.IGNORECASE)

def remaining_time(deadline: float) -> float:
    """Return remaining seconds until a monotonic deadline.

    Args:
        deadline: Absolute timestamp from :func:`time.monotonic`.

    Raises:
        TimeoutError: If the deadline has been reached.
    """
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError("Timeout exceeded")
    return remaining

def read_all_with_timeout(
        file_object: IO[bytes],
        timeout: int = DEFAULT_READ_TIMEOUT,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> bytes:
    """Read from a binary stream until EOF with a global timeout.

    The timeout applies to the whole operation (single deadline), not per chunk.

    Args:
        file_object: Binary stream (must implement :meth:`fileno`).
        timeout: Maximum number of seconds.
        chunk_size: Maximum bytes per read.

    Raises:
        TimeoutError: If the deadline is reached before EOF.
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
    """Write all bytes to a binary stream with a global timeout.

    Args:
        file_object: Binary stream (must implement :meth:`fileno`).
        data: Bytes to write.
        timeout: Maximum number of seconds.

    Raises:
        TimeoutError: If the deadline is reached before completion.
        RuntimeError: If 0 bytes are written while data remains.
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

@contextmanager
def preserve_thread_data():
    """Preserve and restore a subset of Odoo thread-local attributes."""
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
    """Build a WSGI environ for an internal Odoo GET request."""
    url, _, query_string = path.partition('?')
    current_environ = request.httprequest.environ
    # By security, we forge a request with public user environment.
    # For protected documents, Odoo should provide a URL with an access token.
    environ = create_environ(
        method='GET',
        path=url,
        query_string=query_string,
        headers={
            'Host': current_environ['HTTP_HOST'],
            'User-Agent': SERVER_SOFTWARE,
            'remote_addr': current_environ['REMOTE_ADDR'],
        }
    )
    return environ

def generate_odoo_http_response(
        request_path: str
) -> Generator[bytes, None, None]:
    """Yield a raw HTTP response (headers then body) for an internal Odoo GET.

    If the response provides ``X-Sendfile``, the file is streamed from disk.
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
    """Split HTML into ``(prefix_with_<body>, body_inner_html, suffix_from_</body>)``.

    If no ``<body>`` can be identified, returns ``(html, "", "")``.
    """
    if not html:
        return "", "", ""

    match = HTML_BODY_PATTERN.fullmatch(html)
    if not match:
        return html, "", ""

    pre, open_tag, body_content, close_tag, post = match.groups()
    return pre + open_tag, body_content, close_tag + post


def make_multi_docs_html(bodies, header='', footer=''):
    """Inject per-page header/footer fragments into each body HTML document."""

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


def consume_headers(buffer: bytearray) -> tuple[Optional[str], Optional[dict[str, str]]]:
    """Parse and remove an HTTP-like header block from a byte buffer.

    Returns ``(None, None)`` if the full header block has not been received yet.
    """
    # Look for the end of the HTTP headers (double CRLF or double LF)
    headers_end = buffer.find(b'\r\n\r\n')
    sep_len = 4
    if headers_end == -1:
        headers_end = buffer.find(b'\n\n')
        sep_len = 2
        if headers_end == -1:
            return None, None

    headers_data = buffer[:headers_end]
    lines = headers_data.split(b'\n')
    
    # Strip \r and decode as text
    decoded_lines = [line.strip(b'\r').decode('utf-8', errors='replace') for line in lines]
    
    request_line = decoded_lines[0] if decoded_lines else ""
    headers = {}
    
    for line in decoded_lines[1:]:
        if not line:
            continue
        parts = line.split(':', 1)
        if len(parts) == 2:
            headers[parts[0].strip().lower()] = parts[1].strip()

    # Remove the headers and the separator from the buffer
    del buffer[:headers_end + sep_len]
    
    return request_line, headers


def _serve_requests(process, documents):
    """Serve Paper Muncher requests until the rendered PDF is returned."""
    _logger.info("_serve_requests: Starting request loop, %d documents available", len(documents))
    documents_served = set()

    # We use a selector to monitor both stdout (requests) and stderr (logs)
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ, data='stdout')
    selector.register(process.stderr, selectors.EVENT_READ, data='stderr')

    # Line buffers for partial reads
    stdout_buffer = bytearray()
    stderr_buffer = bytearray()

    request_number = 0
    try:
        while True:
            # Check if process died
            if process.poll() is not None:
                break

            # Wait for data on either pipe (timeout helps check process status)
            events = selector.select(timeout=1.0)

            for key, mask in events:
                if key.data == 'stderr':
                    # DRAIN STDERR: Read logs so the worker doesn't block
                    # Using a large read to clear the buffer quickly


                    log_data = os.read(process.stderr.fileno(), 65536)
                    if not log_data:
                        selector.unregister(process.stderr)
                    else:
                        if not LOG_PAPER_MUNCHER:
                            continue

                        stderr_buffer.extend(log_data)
                        while b'\n' in stderr_buffer:
                            line_end = stderr_buffer.find(b'\n') + 1
                            line = stderr_buffer[:line_end].decode('utf-8', errors='replace').rstrip('\r\n')
                            del stderr_buffer[:line_end]
                            if line:
                                _logger.warning("Worker Log: %s", line)

                elif key.data == 'stdout':
                    # PROCESS REQUESTS: Read chunk from stdout
                    chunk = os.read(process.stdout.fileno(), DEFAULT_CHUNK_SIZE)
                    if not chunk: # EOF
                        return

                    stdout_buffer.extend(chunk)

                    while True:
                        request_line, headers = consume_headers(stdout_buffer)
                        if request_line is None:
                            break

                        request_number += 1

                        if request_line.startswith('GET'):
                            documents_served = _handle_single_request(process, request_line, documents, documents_served, request_number)

                        elif request_line.startswith('PUT'):
                            all_docs_served = len(documents_served) >= len(documents)
                            if all_docs_served:
                                return _finalize_and_read(process, stdout_buffer)
                            raise RuntimeError("Paper Muncher returned before we sent everything")


    finally:
        selector.close()


def _finalize_and_read(process, current_buffer):
    """Send the final response, then read stdout/stderr and validate the PDF."""
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

    try:
        _safe_write(process, final_response)
        process.stdin.flush()
        process.stdin.close()
    except TimeoutError:
        raise

    if process.poll() is not None:
        raise RuntimeError("Paper Muncher crashed before returning PDF")

    try:
        rendered_content = bytes(current_buffer + read_all_with_timeout(process.stdout))
        stderr_output = read_all_with_timeout(process.stderr)
    except (EOFError, TimeoutError):
        try:
            process.kill()
        except Exception:
            pass
        try:
            process.wait()
        except Exception:
            pass
        raise

    if stderr_output:
        _logger.warning(
            "Paper Muncher error output: %s",
            stderr_output.decode('utf-8', errors='replace'),
        )

    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            process.kill()
        except Exception:
            pass
        try:
            process.wait()
        except Exception:
            pass
        _logger.warning(
            "Paper Muncher did not terminate in time, forcefully killed it"
        )

    if process.returncode != 0:
        _logger.warning("Paper Muncher exited with code %d", process.returncode)

    if not rendered_content.startswith(b'%PDF-'):
        raise RuntimeError("Paper Muncher did not return valid PDF content")

    return rendered_content


def _handle_single_request(process, request_line, documents, documents_served, request_number):
    """Serve one ``GET`` request (document or asset) from the worker."""
    parts = request_line.split(' ')
    if len(parts) < 2:
        return

    method, path = parts[0], parts[1]

    if method != 'GET':
        raise ValueError(
            f"Unexpected HTTP method: {method} in line: {request_line}")


    _logger.info("Request #%d: path=%r (documents_count=%d)", request_number, path, len(documents))

    is_document = path.endswith(('.html','.xhtml','.xml')) or path == "."
    if is_document:
        index = int(path.split('.')[0]) if path != "." else 0
        _logger.info("Request #%d: Document request for index=%d", request_number, index)
        content = documents[index]
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
                               b'date': format_datetime(now, usegmt=True).encode(),
                               b'server': SERVER_SOFTWARE.encode(),
                           }
        _safe_write(process, response_headers)
        _safe_write(process, content.encode())
        process.stdin.flush()
        documents_served.add(index)
    else:
        # Asset logic
        for chunk in generate_odoo_http_response(path):
            _safe_write(process, chunk)

    process.stdin.flush()
    _logger.info("Request #%d: Asset %s sent successfully", request_number, path)
    return documents_served


def _safe_write(process, data: bytes) -> None:
    """Write to the worker stdin, killing the process if the write times out."""
    try:
        write_with_timeout(process.stdin, data)
    except TimeoutError:
        try:
            process.kill()
        except Exception:
            pass
        try:
            process.wait()
        except Exception:
            pass
        raise
