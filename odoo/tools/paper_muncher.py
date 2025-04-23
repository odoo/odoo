import io
import logging
import subprocess

from .misc import find_in_path

_logger = logging.getLogger(__name__)

REPORT_ASSET_KEY = 'http://127.0.0.1:8069/papermuncher0000.html'
MAX_BUFFER_SIZE = 1024


def can_use_papermuncher():
    from odoo.http import request

    if not request or 'use-papermuncher' not in request.session.debug:
        return False
    try:
        binary = find_in_path('paper-muncher')
        subprocess.Popen([binary, '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except Exception:  # noqa: BLE001
        return False


def run_papermuncher(
    paperformat,
    bodies: list[str],
    header: str = '',
    footer: str = '',
    landscape: bool = False,
    specific_paperformat_args: dict | None = None,
    set_viewport_size: str | None = None,
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

        # The only exception we are recovering from for now is FileNotFound, which is implemented in PM's HttPipe flow
        try:
            while True:
                request = HttpRequest(process.stdout)
                if request.method == "GET":
                    stream = get_ressource_request(request.path, body=content)
                    process.stdin.write(stream)
                    process.stdin.flush()
                elif request.method == "PUT":
                    process.stdin.write(b"HTTP/1.1 200 OK\r\n\r\n")
                    process.stdin.flush()
                    payload = process.stdout.read()
                    process.terminate()
                    return payload
                else:
                    raise RuntimeError(f"Wrong request method: {request.method!r}")  # noqa: TRY301

        except Exception as e:  # noqa: BLE001
            process.terminate()
            _logger.debug(process.stderr.read().decode("utf-8") if process.stderr else 'paper-muncher stderr is not defined.', exc_info=e)
            raise RuntimeError('Error while running paper-muncher to render the pdf.') from e


class HttpRequest:
    def __init__(self, reader: io.RawIOBase):
        self.reader = reader
        self.headers = {}
        self.method = None
        self.path = None
        self.version = None

        header_lines = self._readHeaderLines(reader)
        self.method, self.path, self.version = header_lines[0].split(' ')

        for line in header_lines[1:]:
            self._addToHeader(line)

    def _readHeaderLines(self, reader: io.RawIOBase) -> list[str]:
        lines = []
        while True:
            request_line = reader.readline().decode('utf-8')
            if len(request_line) == 0:
                raise EOFError("Input stream has ended")
            if request_line == "\r\n":
                break
            lines.append(request_line)
        return lines

    def _addToHeader(self, header_line: str) -> None:
        key, value = header_line.split(':')
        self.headers[key.strip()] = value.strip()


def get_ressource_request(path: str, body=None) -> bytes:
    from odoo.http import root, request, Request, HTTPRequest, _request_stack, _dispatchers

    status_code = 404
    content = b''
    mimetype = 'text/html'

    if path.endswith(REPORT_ASSET_KEY.rsplit('/', 1)[1]):
        status_code = 200
        content = body.encode("utf-8")
        mimetype = 'text/html'
    else:
        _logger.debug("Get ressource: %s", path)

        httprequest = request.httprequest
        environ = httprequest._HTTPRequest__environ.copy()
        path_info, _, query_string = path.partition('?')
        environ['PATH_INFO'] = path_info
        environ['QUERY_STRING'] = query_string
        environ['RAW_URI'] = path
        ressource_httprequest = HTTPRequest(environ)
        ressource_httprequest.form = {'csrf_token': httprequest.form.get('csrf_token')}
        ressource_httprequest.files = {}
        ressource_request = Request(ressource_httprequest)
        ressource_request.env = request.env()
        ressource_request.db = request.db
        ressource_request.registry = request.registry
        ressource_request.session = request.session
        _request_stack.push(ressource_request)
        try:
            response = None
            if root.get_static_file(path):
                response = ressource_request._serve_static()
            else:
                ir_http = ressource_request.env['ir.http']
                with ir_http.env.cr.savepoint():
                    rule, args = ir_http._match(path)
                    ir_http._pre_dispatch(rule, args)
                    dispatcher = _dispatchers[rule.endpoint.routing['type']](ressource_request)
                    response = dispatcher.dispatch(rule.endpoint, args)
                    ir_http._post_dispatch(response)
        except Exception as e:  # noqa: BLE001
            _logger.info('Cannot get ressource %r needed to render the pdf', path, exc_info=e)
            _logger.warning(e)
        finally:
            _request_stack.pop()

        if response:
            status_code = response.status_code
            mimetype = response.headers.get('Content-Type', 'text/html')
            content = b"".join(response.response)

    if status_code >= 300 and status_code < 400:
        _logger.warning("Redirect not implemented: %s", path)
    if status_code != 200:
        _logger.debug("File not found: %s", path)
        return b"HTTP/1.1 404 Not Found\r\n"

    return b"\r\n".join([
        b"HTTP/1.1 200 OK",
        f"Content-Length: {len(content)}".encode(),
        f"Content-Type: {mimetype}".encode(),
        b"",
        content,
    ])
