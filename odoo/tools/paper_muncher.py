import logging
import subprocess
import time
import os
import selectors
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from email.utils import format_datetime
from itertools import count
from typing import Optional, BinaryIO
from werkzeug.test import create_environ, run_wsgi_app

import odoo
from odoo.http import request, root

from .misc import find_in_path

_logger = logging.getLogger(__name__)

USER_AGENT = f'{odoo.release.product_name}/{odoo.release.version}'
DEFAULT_READ_TIMEOUT = 60 * 15  # seconds
DEFAULT_READLINE_TIMEOUT = 60  # seconds
DEFAULT_CHUNK_SIZE = 4096  # bytes


def can_use_papermuncher():
    if not request or 'papermuncher' not in request.session.debug:
        return False
    try:
        binary = find_in_path('paper-muncher')
        subprocess.run([binary, '--version'], capture_output=True, check=True)
        return True
    except (OSError, subprocess.CalledProcessError):
        _logger.debug("Cannot locate/use paper-muncher", exc_info=True)
        return False


def readline_with_timeout(
    file_object: BinaryIO,
    timeout: int = DEFAULT_READLINE_TIMEOUT,
) -> bytes:
    """
    Read a full line (ending with '\n') from file_object within timeout.
    Raises TimeoutError or EOFError if conditions are not met.
    """
    fd = file_object.fileno()
    selector = selectors.DefaultSelector()
    selector.register(fd, selectors.EVENT_READ)

    deadline = time.monotonic() + timeout

    line_buffer = bytearray()
    try:
        while remaining_time := deadline - time.monotonic() > 0:
            events = selector.select(timeout=remaining_time)
            if not events:
                raise TimeoutError(
                    "Timeout waiting for line data from subprocess")

            next_byte = os.read(fd, 1)
            if not next_byte:
                if line_buffer:
                    return bytes(line_buffer)
                raise EOFError("EOF reached while reading line")

            line_buffer += next_byte
            if next_byte == b'\n':
                break
        else:
            raise TimeoutError("Timeout while reading line from subprocess")

        return bytes(line_buffer)
    finally:
        selector.unregister(fd)


def read_all_with_timeout(
    file_object: BinaryIO,
    timeout: int = DEFAULT_READ_TIMEOUT,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> bytes:
    """
    Read all data from file_object until EOF. Timeout applies to each chunk.
    """
    fd = file_object.fileno()
    selector = selectors.DefaultSelector()
    selector.register(fd, selectors.EVENT_READ)

    data = bytearray()
    while selector.select(timeout=timeout):
        chunk = os.read(fd, chunk_size)
        if not chunk:
            break
        data.extend(chunk)
    else:
        raise TimeoutError("Timeout while reading data from subprocess")

    selector.unregister(fd)
    return bytes(data)


def consume_paper_muncher_request(stdout, timeout=DEFAULT_READ_TIMEOUT):
    while True:
        line = readline_with_timeout(stdout, timeout=timeout)
        _logger.debug("Paper Muncher request line: %s", line.rstrip())
        if line == b"\r\n":
            return


def read_paper_muncher_request(
    stdout,
    timeout=DEFAULT_READ_TIMEOUT,
) -> Optional[str]:
    first_line_bytes = readline_with_timeout(stdout, timeout=timeout)

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
        return None
    elif method != 'GET':
        raise ValueError(
            f"Unexpected HTTP method: {method} in line: {first_line}")

    consume_paper_muncher_request(stdout, timeout=timeout)

    return path


def generate_odoo_http_response(request_path: str):
    """
    Call the Odoo WSGI application for the given request path,
    and yield the full HTTP response including headers and body as
    byte chunks.

    This simulates an HTTP response from Odoo's internal webserver,
    to be sent back to Paper Muncher for asset requests.
    """
    response_iterable, http_status, http_response_headers = run_wsgi_app(
        root, generate_environ(request_path)
    )

    now = datetime.now(timezone.utc)
    http_response_status_line_and_headers = (
        f"HTTP/1.1 {http_status}\r\n"
        f"Date: {format_datetime(now, usegmt=True)}\r\n"
        f"Server: {USER_AGENT}\r\n"
        f"Content-Length: {http_response_headers['Content-Length']}\r\n"
        f"Content-Type: {http_response_headers['Content-Type']}\r\n"
        "\r\n"
    ).encode()

    yield http_response_status_line_and_headers
    yield from response_iterable


def generate_environ(path):
    """
    Generate a WSGI environment for the given path.
    This is used to simulate an HTTP request to the Odoo application.
    """
    url, _, query_string = path.partition('?')
    current_environ = request.httprequest.environ
    environ = create_environ(
        method='GET',
        path=url,
        query_string=query_string if query_string else '',
        headers={
            'Host': current_environ['HTTP_HOST'],
            'User-Agent': USER_AGENT,
            'http_cookie': current_environ['HTTP_COOKIE'],
            'remote_addr': current_environ['REMOTE_ADDR'],
        }
    )
    return environ


def run_papermuncher(
    paperformat,
    bodies: Sequence[str],
    header: str = '',
    footer: str = '',
    landscape: bool = False,
    specific_paperformat_args: Optional[Mapping] = None,
    set_viewport_size: Optional[str] = None,
) -> bytes:
    """
    Run the Paper Muncher to generate a PDF from the given HTML content.
    This function handles the communication with the Paper Muncher process,
    including sending the HTML content and receiving the generated PDF.
    """
    def get_body(html):
        return html and html.split('<body')[1].split(">", 1)[1].split("</body>")[0] or ''
    header = get_body(header)
    footer = get_body(footer)
    out = [] 
    for html in bodies:  
        open, body, close = html.partition(get_body(html))  
        out.extend((open, header, body, footer, close, "\n"))
    content = "".join(out) 

    extra_args = ['--scale', '72dpi'] #  bypass DPI scaling to correspond to WKHTMLTOPDF
    if landscape:
        extra_args += ['--orientation', 'landscape']

    if paperformat and paperformat.format:
        if paperformat.format != 'custom':
            extra_args += ['--paper', str(paperformat.format)]
        elif paperformat.page_height and paperformat.page_width:
            extra_args += ['--width', f'{paperformat.page_width}mm']
            extra_args += ['--height', f'{paperformat.page_height}mm']

    binary = find_in_path('paper-muncher')

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
            b'server': USER_AGENT.encode(),
        }

        process.stdin.write(response_headers)
        process.stdin.write(content.encode())
        process.stdin.flush()

        if process.poll() is not None:
            raise RuntimeError(
                "Paper Muncher crashed while sending HTML content")

        # Phase 2: serve asset requests
        for request_no in count(start=1):
            path = read_paper_muncher_request(process.stdout)
            if path is None:
                break

            for chunk in generate_odoo_http_response(path):
                process.stdin.write(chunk)
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
            b'server': USER_AGENT.encode(),
        }

        process.stdin.write(final_response)
        process.stdin.flush()
        process.stdin.close()

        if process.poll() is not None:
            raise RuntimeError("Paper Muncher crashed before returning PDF")

        rendered_content = read_all_with_timeout(process.stdout)

        stderr_output = read_all_with_timeout(process.stderr)
        if stderr_output:
            _logger.warning(
                "Paper Muncher error output: %s",
                stderr_output.decode('utf-8', errors='replace')
            )

        process.wait(timeout=5)
        if process.returncode != 0:
            raise RuntimeError(
                f"Paper Muncher exited with code {process.returncode}")

        return rendered_content
