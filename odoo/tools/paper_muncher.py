import logging
import subprocess
import time
from collections.abc import Mapping, Sequence
from typing import Optional
from wsgiref.handlers import format_date_time
from werkzeug.test import create_environ, run_wsgi_app

import odoo
from odoo.http import request, root, Session

from .misc import find_in_path

_logger = logging.getLogger(__name__)
USER_AGENT = f'{odoo.release.product_name}/{odoo.release.version}'

def can_use_papermuncher():
    if not request or 'use-papermuncher' not in request.session.debug:
        return False
    try:
        binary = find_in_path('paper-muncher')
        subprocess.run([binary, '--version'], capture_output=True, check=True)
        return True
    except (OSError, subprocess.CalledProcessError) as e:  # noqa: BLE001
        _logger.debug("cannot locate/use paper-muncher", exc_info=True)
        return False


def run_papermuncher(
    paperformat,
    bodies:Sequence[str],
    header: str = '',
    footer: str = '',
    landscape: bool = False,
    specific_paperformat_args: Optional[Mapping] = None,
    set_viewport_size: str | None = None,
) -> bytes:

    # TODO: use header and footer (+ placeholder for pager)
    def get_body(html):
        return html and html.split('<body')[1].split(">", 1)[1].split("</body>")[0] or ''
    header = get_body(header)
    footer = get_body(footer)
    out = []  
    for html in bodies:  
        open, body, close = html.partition(get_body(html))  
        out.extend((open, header, body, footer, close, "\n"))  
    content = "".join(out) 


    extra_args = ['--scale', '72dpi']  # wkhtml default is 72dpi
    if landscape:
        extra_args += ['--orientation', 'landscape'] 
    if paperformat and paperformat.format:
        if paperformat.format != 'custom':
            extra_args += ['--paper', str(paperformat.format)]
        elif paperformat.page_height and paperformat.page_width:  
            extra_args += ['--width', f'{paperformat.page_width}mm']  
            extra_args += ['--height', f'{paperformat.page_height}mm'] 

    with subprocess.Popen(
        [find_in_path('paper-muncher'), "print", "pipe:", '-o', "pipe:"] + extra_args,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ) as process:
        # phase 1: send the html
        consume_pm_request(process.stdout)  # throw the first request away
        if process.poll() is not None:
            raise RuntimeError("Paper Muncher crashed before receiving content")
        response_headers = (
            b"HTTP/1.1 200 OK\r\n"
            b"Content-Length: %(length)d\r\n"
            b"Content-Type: text/html\r\n"
            b"Date: %(date)s\r\n"
            b"Server: %(server)s\r\n"
            b"\r\n"
        ) % {
            b'length': len(content.encode()),
            b'date': format_date_time(time.time()).encode(),
            b'server': USER_AGENT.encode(),
        }
        process.stdin.write(response_headers)
        process.stdin.write(content.encode())
        if process.poll() is not None:
            raise RuntimeError("Paper Muncher crashed while sending HTML content")

        # phase 2: send the assets
        while (path := read_pm_request(process.stdout)) is not None:
            for chunk in bluently_request(path):
                process.stdin.write(chunk)
            process.stdin.flush()
            if process.poll() is not None:
                raise RuntimeError(f"Paper Muncher crashed while serving asset: {path}")

        # phase 3: fetch the pdf
        process.stdin.write((
            b"HTTP/1.1 200 OK\r\n"
            b"Date: %(date)s\r\n"
            b"Server: %(server)s\r\n"
            b"\r\n"
        ) % {
            b'date': format_date_time(time.time()).encode(),
            b'server': USER_AGENT.encode(),
        })
        process.stdin.flush()
        if process.poll() is not None:
            raise RuntimeError("Paper Muncher crashed before returning PDF")
        rendered_content = bytearray()  
        while chunk := process.stdout.read():  
            rendered_content += chunk  
        if stderr := process.stderr.read():
            _logger.warning("paper muncher error: %s", stderr.decode('utf-8'))
        process.wait(timeout=30)
        if process.returncode != 0:
            raise RuntimeError(f"Paper Muncher exited with code {process.returncode}")  
        return rendered_content


def consume_pm_request(stdout):
    while (request_line := stdout.readline()) != b"\r\n":
        _logger.debug(b"paper muncher request line: %s", request_line)
        if not request_line:
            raise EOFError("Input stream has ended")


def read_pm_request(stdout):
    first_line = stdout.readline().decode('utf-8')
    if not first_line:
        raise EOFError("Input stream has ended")
    _logger.debug(b"fist paper muncher request line: %s", first_line)
    method, path, _ = first_line.split(' ')
    if method == 'PUT':
        return
    elif method != 'GET':
        raise ValueError(
            "Invalid request method: %(method)s in line %(line)s",
            method=method, line=first_line,
        )

    # consume the headers
    consume_pm_request(stdout)

    return path


def bluently_request(path):
    app_iter, status, headers = run_wsgi_app(root, generate_environ(path))
    head = (
        f"HTTP/1.1 {status}\r\n"
        f"Date: {format_date_time(time.time())}\r\n"
        f"Server: {USER_AGENT}\r\n"
        f"Content-Length: {headers['Content-Length']}\r\n"
        f"Content-Type: {headers['Content-Type']}\r\n"
        "\r\n"
    ).encode()
    yield head
    yield from app_iter


def generate_environ(path):
    url, _, query_string = path.partition('?')
    current_environ = request.httprequest.environ
    environ = create_environ(
        method='GET',
        path=url,
        *{'query_string': query_string} if query_string else {},
        headers={
            'Host': current_environ['HTTP_HOST'],
            'User-Agent': USER_AGENT,
            'http_cookie': current_environ['HTTP_COOKIE'],
            'remote_addr': current_environ['REMOTE_ADDR'],
        }
    )
    return environ
