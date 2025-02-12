from contextlib import nullcontext
import select
import sys
import logging
from pathlib import Path
import subprocess
from tempfile import TemporaryFile
from odoo import api, models, fields
from odoo.addons.base.models.assetsbundle import ANY_UNIQUE
from odoo.tools.misc import find_in_path
from odoo.exceptions import UserError
from odoo import SUPERUSER_ID, _, http, api

_logger = logging.getLogger(__name__)
papermuncher_state = 'install'

def _get_paper_muncher_bin():
    return find_in_path('paper-muncher')


try:
    process = subprocess.Popen(
        [_get_paper_muncher_bin(), '--usage'], stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
except (OSError, IOError):
    _logger.info('You need \'paper-muncher\' to print a pdf version of the reports.')
    papermuncher_state = 'broken'
else:
    _logger.info(f'Will use the \'paper-muncher\' binary at {_get_paper_muncher_bin()}')
    papermuncher_state = 'ok'

class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    report_type = fields.Selection(selection_add=[('qweb-pdf-papermuncher', 'PDF (Paper Muncher)')], default='qweb-pdf', ondelete={'qweb-pdf-papermuncher': 'set qweb-pdf'})

    @api.model
    def get_pdf_engine_state(self, engine_name=None):
        if engine_name == 'papermuncher':
            return 'papermuncher', papermuncher_state
        return super().get_pdf_engine_state(engine_name)

    # COPIED FROM CONTROLLER, TBD -----------------------------------------------------------------------------
    @api.model
    def _get_assets(self, filename=None, unique=ANY_UNIQUE, nocache=False, assets_params=None):
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
                    raise UserError("c")
        if not attachment:
            raise UserError("d")

        return self.env['ir.binary']._get_stream_from(attachment, 'raw', filename)
    # COPIED FROM CONTROLLER, TBD -----------------------------------------------------------------------------

    @api.model
    def _communicate(self, body, process):
        def get_chunked_body():
            def read_chunk():
                def read_chunk_size():
                    chunk_size = b""
                    while True:
                        byte = process.stdout.read(1)

                        if len(byte) == 0 or process.poll() is not None:
                            return None

                        chunk_size += byte

                        if len(chunk_size) >= 2 and chunk_size[-2:] == b'\r\n':
                            break
                    return int(chunk_size[:-2])

                def read_chunk_content(size):
                    chunk = b""
                    max_buffer_size = 1024
                    while size > 0:
                        bs = min(max_buffer_size, size)
                        byte = process.stdout.read(bs)
                        chunk += byte

                        size -= bs
                    return chunk

                size = read_chunk_size()
                chunk = read_chunk_content(size)

                endline = process.stdout.read(2)
                assert (endline == b'\r\n')

                return chunk

            pdf = b""
            while True:
                chunk = read_chunk()

                if chunk is None:
                    return None

                if len(chunk) == 0:
                    break

                pdf += chunk

            return pdf

        def read_request_lines():
            request_lines = []

            while True:
                request_line = process.stdout.readline().decode()

                if len(request_line) == 0 or process.poll() is not None:
                    return None

                if request_line == "\r\n":
                    break

                request_lines.append(request_line)

            return request_lines

        def parse_request(request_lines):
            try:
                method, path, version = request_lines[0].split()
            except:
                raise Exception("Ill-formed first line")

            # We dont care about header
            return (method, path)

        def fetch_requested_resource(path):
            if path == "/stdin":
                return {'resource': body.encode("utf-8")}

            _, _, _, unique, filename = path.split("/")
            x = self._get_assets(filename, unique)
            return {'resource': x.read()}

        def send(response_dict):
            response = None
            if response_dict["code"] == 200:
                if "resource" in response_dict:
                    response = b"\r\n".join([
                        b"HTTP/1.1 200 OK",
                        f"Content-Length: {len(response_dict['resource'])}".encode(),
                        b"Content-Type: text/css",
                        b"",
                        response_dict["resource"]
                    ])
                else:
                    response = b"HTTP/1.1 200 OK\r\n\r\n"
            else:
                response = f"HTTP/1.1 {response_dict['code']} NOTOK\r\n\r\n".encode()

            process.stdin.write(response)
            process.stdin.flush()

        while True:
            raw_request_lines = read_request_lines()

            if raw_request_lines is None:
                break

            try:
                method, path = parse_request(raw_request_lines)
            except Exception as e:
                send({'code': 400})  # best code?
                raise e

            if method == "GET":
                try:
                    resource = fetch_requested_resource(path)
                except Exception:
                    send({'code': 404})
                    continue
            elif method == "POST":
                body = get_chunked_body()
                send({'code': 200})
                return body
            else:
                send({'code': 400})  # ?
                break

            send(resource | {"code": 200})

    @api.model
    def _run_papermuncher(
            self,
            bodies,
            report_ref=False,
            header=None,
            footer=None,
            landscape=False,
            specific_paperformat_args=None,
            set_viewport_size=False) -> bytes:
        '''Execute wkhtmltopdf as a subprocess in order to convert html given in input into a pdf
        document.

        :param list[str] bodies: The html bodies of the report, one per page.
        :param report_ref: report reference that is needed to get report paperformat.
        :param str header: The html header of the report containing all headers.
        :param str footer: The html footer of the report containing all footers.
        :param landscape: Force the pdf to be rendered under a landscape format.
        :param specific_paperformat_args: dict of prioritized paperformat arguments.
        :param set_viewport_size: Enable a viewport sized '1024x1280' or '1280x1024' depending of landscape arg.
        :return: Content of the pdf as bytes
        :rtype: bytes
        '''

        args: list[str] = ["--httpipe"]
        if landscape:
            args += ['--orientation', 'landscape']

        paperformat_id = self._get_report(report_ref).get_paperformat() if report_ref else self.get_paperformat()
        if paperformat_id:
            if paperformat_id.format and paperformat_id.format != 'custom':
                args += ['--paper', str(paperformat_id.format)]

            if paperformat_id.page_height and paperformat_id.page_width and paperformat_id.format == 'custom':
                args += ['--width', str(paperformat_id.page_width) + 'mm']
                args += ['--height', str(paperformat_id.page_height) + 'mm']

        if len(bodies) != 1:
            raise ValueError('Paper Muncher only supports one body per report')

        body = bodies[0]

        command: list[str] = [_get_paper_muncher_bin(), "print"] + args

        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        try:
            output = self._communicate(body, process)
        except Exception as e:
            raise UserError(f'{e}')

        process.wait()
        if process.returncode != 0:
            raise UserError(f'Error while running paper-muncher:\n{process.stderr.read().decode("utf-8")}')

        return output
