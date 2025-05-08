import logging
import subprocess
import textwrap
import time
from wsgiref.handlers import format_date_time

from werkzeug.test import create_environ, run_wsgi_app

import odoo.http
import odoo.release

from .misc import find_in_path

_logger = logging.getLogger(__name__)

REPORT_ASSET_KEY = 'http://127.0.0.1:8069/papermuncher0000.html'


def can_use_papermuncher():
    from odoo.http import request  # noqa: PLC0415

    if not request or 'use-papermuncher' not in request.session.debug:
        return False
    try:
        binary = find_in_path('paper-muncher')
        subprocess.Popen([binary, '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except Exception as e:  # noqa: BLE001
        _logger.warning(e)
        return False


def run_papermuncher(
    paperformat,
    bodies: list[str],
    header: str = '',
    footer: str = '',
    landscape: bool = False,
    specific_paperformat_args: dict | None = None,
    set_viewport_size: str | None = None,

    env=...,
) -> bytes:

    # TODO: use header and footer (+ placeholder for pager)
    def get_body(html):
        return html and html.split('<body')[1].split(">", 1)[1].split("</body>")[0] or ''
    header = get_body(header)
    footer = get_body(footer)
    content = ''
    for html in bodies:
        open, body, close = html.partition(get_body(html))
        content += f'{open}{header}{body}{footer}{close}\n'

    extraArgs = ['--orientation', 'landscape'] if landscape else []

    if paperformat:
        if paperformat.format and paperformat.format != 'custom':
            extraArgs += ['--paper', str(paperformat.format)]
        if paperformat.page_height and paperformat.page_width and paperformat.format == 'custom':
            extraArgs += ['--width', str(paperformat.page_width) + 'mm']
            extraArgs += ['--height', str(paperformat.page_height) + 'mm']

    with subprocess.Popen(
        [find_in_path('paper-muncher'), '--sandbox', "print", REPORT_ASSET_KEY, '-o', 'http://stdout'] + extraArgs,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ) as process:
        process.stdout.readline().rstrip()
        process.stdin.write(textwrap.dedent(f"""\
            HTTP/1.1 200 OK\r
            Date: {format_date_time(time.time())}\r
            Server: {odoo.release.product_name}/{odoo.release.major_version}\r
            Content-Length: {len(content)}\r
            Content-Type: text/html\r
            \r
        """.encode()))
        process.stdin.write(content.encode())

        while (line := process.stdout.readline().rstrip()):
            match line.partition(b' '):
                case (b'GET', b' ', path):
                    for line in get(path):
                        process.stdin.write(line)
                case (b'PUT', b'', b''):
                    break
                case _:
                    e = f"unknown paper-muncher command on stdout: {line}"
                    raise ValueError(e)

        return process.stdout


def get(path):
    # The environ must be created so the http stack uses the same user
    # and database. Maybe we shall create a dedicated session for that
    # purpose on disk, or reuse the original request's session (but we
    # MUST ensure the db and user are right).
    app_iter, status, headers = run_wsgi_app(odoo.http.root, create_environ(
        ...
    ))

    # https://httpwg.org/specs/rfc9112.html#message.body.length
    # the 8th case is troublesome, as we are not in a situation where we
    # can "close the socket". Either we decide to not support it, either
    # we rewrite the response on-the-fly (maybe using
    # Transfert-Encoding: chunked)
    assert headers.get('Connection', '').casefold() != 'close'  # this is incomplete

    yield magic(status)
    yield magic(headers)
    yield from app_iter
