
from contextlib import nullcontext
import io
from pathlib import Path
import subprocess
import logging
from odoo import SUPERUSER_ID, _, http, api
from odoo.exceptions import UserError
from odoo.addons.base.models.assetsbundle import ANY_UNIQUE

_logger = logging.getLogger(__name__)

class Loader:
    def handleRequest(self, url: str):
        raise NotImplementedError()


class OdooLoader(Loader):

    def __init__(self, env, document, doc_name):
        self.env = env
        self.document = document
        self.doc_name = doc_name

    # COPIED FROM CONTROLLER, TODO
    def _get_assets(self, filename=None, unique=ANY_UNIQUE, assets_params=None):
        assets_params = assets_params or {}
        assert isinstance(assets_params, dict)
        debug_assets = unique == 'debug'
        if unique in ('any', '%'):
            unique = ANY_UNIQUE
        attachment = None
        if unique != 'debug':
            url = self.env['ir.asset']._get_asset_bundle_url(filename, unique, assets_params)
            assert not '%' in url
            domain = [
                ('public', '=', True),
                ('url', '!=', False),
                ('url', '=like', url),
                ('res_model', '=', 'ir.ui.view'),
                ('res_id', '=', 0),
                ('create_uid', '=', SUPERUSER_ID),
            ]
            attachment = self.env['ir.attachment'].sudo().search(domain, limit=1)
        if not attachment:
            # try to generate one
            if self.env.cr.readonly:
                self.env.cr.rollback()  # reset state to detect newly generated assets
                cursor_manager = self.env.registry.cursor(readonly=False)
            else:
                # if we don't have a replica, the cursor is not readonly, use the same one to avoid a rollback
                cursor_manager = nullcontext(self.env.cr)
            with cursor_manager as rw_cr:
                rw_env = api.Environment(rw_cr, self.env.user.id, {})
                try:
                    if filename.endswith('.map'):
                        _logger.error(".map should have been generated through debug assets, (version %s most likely outdated)", unique)
                        raise UserError("a")
                    bundle_name, rtl, asset_type, autoprefix = rw_env['ir.asset']._parse_bundle_name(filename, debug_assets)
                    css = asset_type == 'css'
                    js = asset_type == 'js'
                    bundle = rw_env['ir.qweb']._get_asset_bundle(
                        bundle_name,
                        css=css,
                        js=js,
                        debug_assets=debug_assets,
                        rtl=rtl,
                        autoprefix=autoprefix,
                        assets_params=assets_params,
                    )
                    # check if the version matches. If not, redirect to the last version
                    if not debug_assets and unique != ANY_UNIQUE and unique != bundle.get_version(asset_type):
                        return UserError("b")
                    if css and bundle.stylesheets:
                        attachment = self.env['ir.attachment'].sudo().browse(bundle.css().id)
                    elif js and bundle.javascripts:
                        attachment = self.env['ir.attachment'].sudo().browse(bundle.js().id)
                except ValueError as e:
                    _logger.warning("Parsing asset bundle %s has failed: %s", filename, e)
                    import traceback
                    print("".join(traceback.format_tb(e.__traceback__)))
                    raise FileNotFoundError()
        if not attachment:
            raise FileNotFoundError()

        return self.env['ir.binary']._get_stream_from(attachment, 'raw', filename)

    def handleRequest(self, url: str):
        # FIXME: we dont need to reload the document which is already in `body`, but this check should be more elegant
        url_nodes = url.split("/")
        if url_nodes[-1] == self.doc_name:
            return self.document.encode("utf-8")

        # Assets path: /web/assets/<string:unique>/<string:filename>'
        if len(url_nodes) == 5 and url.startswith("/web/assets/"):
            assetBinary = self._get_assets(url_nodes[-1], url_nodes[-2])
            return assetBinary.read()

        raise FileNotFoundError()


MAX_BUFFER_SIZE = 1024
class HttpMessage():

    def __init__(self):
        self.headers = {}

    def _readHeaderLines(self, reader: io.TextIOWrapper) -> list[str]:
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

    def readHeader(self, reader: io.TextIOWrapper) -> None:
        raise NotImplementedError()

    def _readSingleChunk(self, reader: io.TextIOWrapper) -> bytes:
        def read_chunk_content(rem_size):
            chunk = b""

            while rem_size > 0:
                bs = min(MAX_BUFFER_SIZE, rem_size)
                byte = reader.read(bs)
                chunk += byte

                rem_size -= bs
            return chunk

        size = int(reader.readline()[:-2])
        chunk = read_chunk_content(size)

        reader.read(2)

        return chunk

    def readChunkedBody(self, reader: io.TextIOWrapper) -> bytes:
        encoded_body = b""
        while True:
            chunk = self._readSingleChunk(reader)

            if chunk is None:
                return None

            if len(chunk) == 0:
                break

            encoded_body += chunk

        return encoded_body

class HttpRequest(HttpMessage):

    def __init__(self, method=None, path=None, version=None):
        super().__init__()
        self.method = method
        self.path = path
        self.version = version

    def readHeader(self, reader: io.TextIOWrapper) -> None:
        header_lines = self._readHeaderLines(reader)
        self.method, self.path, self.version = header_lines[0].split(' ')

        for line in header_lines[1:]:
            self._addToHeader(line)


RESPONSE_MESSAGES = {
    200: 'OK',
    404: 'Not Found'
}

class HttpResponse(HttpMessage):

    def __init__(self, code: int, version="1.1"):
        super().__init__()
        self.version = version
        self.code = code
        self.body = None

    def addHeader(self, key: str, value: str) -> None:
        self.headers[key] = value

    def addBody(self, body: bytes) -> None:
        if not isinstance(body, bytes):
            raise ValueError("Body must be in bytes")
        self.body = body
        self.addHeader("Content-Length", len(body))

    def __bytes__(self) -> bytes:
        def firstLine():
            return f"HTTP/{self.version} {self.code} {RESPONSE_MESSAGES.get(self.code, 'Hello')}".encode()

        def headers():
            return (f"{key}: {value}".encode() for key, value in self.headers.items())

        return b"\r\n".join([firstLine(), *headers(), b"", self.body])


def _run(
    args: list[str],
    loader=Loader(),
) -> bytes:

    def sendResponse(stdin: io.TextIOWrapper, response: HttpResponse):
        stdin.write(bytes(response))
        stdin.flush()

    with subprocess.Popen(
        args,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ) as proc:
        stdout = proc.stdout
        if stdout is None:
            raise ValueError("stdout is None")

        stderr = proc.stderr
        if stderr is None:
            raise ValueError("stderr is None")

        stdin = proc.stdin
        if stdin is None:
            raise ValueError("stdin is None")

        # The only exception we are recovering from for now is FileNotFound, which is implemented in PM's HttPipe flow
        try:
            while True:
                request = HttpRequest()
                request.readHeader(stdout)

                if request.method == "GET":
                    try:
                        asset = loader.handleRequest(request.path)
                        response = HttpResponse(200)
                    except FileNotFoundError:
                        response = HttpResponse(404)
                    response.addBody(asset)

                    sendResponse(stdin, response)
                elif request.method == "POST":
                    payload = request.readChunkedBody(stdout)
                    proc.terminate()
                    return payload, stderr.read().decode('utf-8'), None
                else:
                    raise ValueError("Invalid request")
        except Exception as e:
            proc.terminate()
            return None, stderr.read().decode('utf-8'), e


def printPM(
    loader: Loader,
    bin: str,
    *args: str,
    **kwargs: str,
):
    extraArgs = list(args)
    for key, value in kwargs.items():
        extraArgs.append(f"--{key}")
        extraArgs.append(str(value))

    return _run(
        [bin, "print"] + extraArgs,
        loader,
    )
