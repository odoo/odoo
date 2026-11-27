# Part of Odoo. See LICENSE file for full copyright and licensing details.
import functools
import logging
import os
import re
import subprocess
import tempfile
import typing
import unittest
from contextlib import ExitStack, closing
from itertools import islice
from urllib.parse import urlparse

import lxml.html
from lxml import etree

from odoo import api, fields, models, modules
from odoo.exceptions import UserError
from odoo.http import request
from odoo.http.session import session_store, update_session_token
from odoo.tools import config, find_in_path, parse_version, split_every

from odoo.addons.base.models.ir_actions_report import ReportPageSetup

_logger = logging.getLogger(__name__)


def _split_table(tree, max_rows):
    """
    Walks through the etree and splits tables with more than max_rows rows into
    multiple tables with max_rows rows.

    This function is needed because wkhtmltopdf has a exponential processing
    time growth when processing tables with many rows. This function is a
    workaround for this problem.

    :param tree: The etree to process
    :param max_rows: The maximum number of rows per table
    """
    for table in list(tree.iter('table')):
        prev = table
        for rows in islice(split_every(max_rows, table), 1, None):
            sibling = etree.Element('table', attrib=table.attrib)
            sibling.extend(rows)
            prev.addnext(sibling)
            prev = sibling


class WkhtmlInfo(typing.NamedTuple):
    state: str
    dpi_zoom_ratio: bool
    bin: str
    version: str
    is_patched_qt: bool
    wkhtmltoimage_bin: str
    wkhtmltoimage_version: tuple[str, ...] | None


@functools.cache
def _wkhtml() -> WkhtmlInfo:
    state = 'install'
    bin_path = 'wkhtmltopdf'
    version = ''
    is_patched_qt = False
    dpi_zoom_ratio = False
    try:
        bin_path = find_in_path('wkhtmltopdf')
        process = subprocess.Popen(
            [bin_path, '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
    except OSError:
        _logger.info('You need Wkhtmltopdf to print a pdf version of the reports.')
    else:
        _logger.info('Will use the Wkhtmltopdf binary at %s', bin_path)
        out, _err = process.communicate()
        version = out.decode('ascii')
        if '(with patched qt)' in version:
            is_patched_qt = True
        match = re.search(r'([0-9.]+)', version)
        if match:
            version = match.group(0)
            if parse_version(version) < parse_version('0.12.0'):
                _logger.info('Upgrade Wkhtmltopdf to (at least) 0.12.0')
                state = 'upgrade'
            else:
                state = 'ok'
            if parse_version(version) >= parse_version('0.12.2'):
                dpi_zoom_ratio = True

            if config['workers'] == 1:
                _logger.info('You need to start Odoo with at least two workers to print a pdf version of the reports.')
                state = 'workers'
        else:
            _logger.info('Wkhtmltopdf seems to be broken.')
            state = 'broken'

    wkhtmltoimage_version = None
    image_bin_path = 'wkhtmltoimage'
    try:
        image_bin_path = find_in_path('wkhtmltoimage')
        process = subprocess.Popen(
            [image_bin_path, '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
    except OSError:
        _logger.info('You need Wkhtmltoimage to generate images from html.')
    else:
        _logger.info('Will use the Wkhtmltoimage binary at %s', image_bin_path)
        out, _err = process.communicate()
        match = re.search(rb'([0-9.]+)', out)
        if match:
            wkhtmltoimage_version = parse_version(match.group(0).decode('ascii'))
            if config['workers'] == 1:
                _logger.info('You need to start Odoo with at least two workers to convert images to html.')
        else:
            _logger.info('Wkhtmltoimage seems to be broken.')

    return WkhtmlInfo(
        state=state,
        dpi_zoom_ratio=dpi_zoom_ratio,
        bin=bin_path,
        version=version,
        is_patched_qt=is_patched_qt,
        wkhtmltoimage_bin=image_bin_path,
        wkhtmltoimage_version=wkhtmltoimage_version,
    )


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    report_type = fields.Selection(
        selection_add=[('qweb-pdf-wkhtmltopdf', 'PDF (Wkhtmltopdf)')],
        ondelete={'qweb-pdf-wkhtmltopdf': 'set qweb-pdf'},
    )

    def _run_wkhtmltopdf__(self, args):
        """
        Runs the given arguments against the wkhtmltopdf binary.

        Returns:
            The process
        """
        bin_path = _wkhtml().bin
        return subprocess.run(
            [bin_path, *args],
            capture_output=True,
            encoding='utf-8',
            check=False,
        )

    @api.model
    def get_pdf_engine_state(self, engine_name):
        if engine_name != 'wkhtmltopdf':
            return super().get_pdf_engine_state(engine_name)
        return _wkhtml().state

    @api.model
    def _build_wkhtmltopdf_args(self, page_setup: ReportPageSetup, set_viewport_size=False):
        '''Build arguments understandable by wkhtmltopdf bin, but for the decorations.

        :param page_setup: The resolved page setup of the documents.
        :param set_viewport_size: Enable a viewport sized '1024x1280' or '1280x1024' depending on the orientation.
        :return: A list of string representing the wkhtmltopdf process command args.
        '''
        command_args = ['--disable-local-file-access']
        if set_viewport_size:
            command_args.extend(['--viewport-size', '1024x1280' if page_setup.landscape else '1280x1024'])

        # Less verbose error messages
        command_args.extend(['--quiet'])

        if page_setup.paper_format:
            command_args.extend(['--page-size', page_setup.paper_format])
        elif page_setup.page_width and page_setup.page_height:
            command_args.extend(['--page-width', f'{page_setup.page_width:g}mm'])
            command_args.extend(['--page-height', f'{page_setup.page_height:g}mm'])

        command_args.extend([
            '--margin-top', f'{page_setup.margin_top:g}',
            '--margin-bottom', f'{page_setup.margin_bottom:g}',
            '--margin-left', f'{page_setup.margin_left:g}',
            '--margin-right', f'{page_setup.margin_right:g}',
        ])
        if page_setup.header_spacing is not None:
            command_args.extend(['--header-spacing', f'{page_setup.header_spacing:g}'])

        dpi = page_setup.dpi
        if dpi and os.name == 'nt' and dpi <= 95:
            _logger.info("Generating PDF on Windows platform require DPI >= 96. Using 96 instead.")
            dpi = 96
        if dpi:
            command_args.extend(['--dpi', str(dpi)])
            if _wkhtml().dpi_zoom_ratio:
                command_args.extend(['--zoom', str(96.0 / dpi)])

        command_args.extend(['--orientation', 'landscape' if page_setup.landscape else 'portrait'])
        if page_setup.header_line:
            command_args.extend(['--header-line'])
        if page_setup.disable_shrinking:
            command_args.extend(['--disable-smart-shrinking'])

        # Add extra time to allow the page to render
        delay = self.env['ir.config_parameter'].sudo().get_int('report.print_delay') or 1000
        command_args.extend(['--javascript-delay', str(delay)])

        return command_args

    def _run_image_engine(self, engine_name, bodies, width, height, image_format="jpg") -> list[bytes | None]:
        if engine_name != 'wkhtmltopdf':
            return super()._run_image_engine(engine_name, bodies, width, height, image_format)
        if modules.module.current_test:
            return [None] * len(bodies)
        wkhtmltoimage_version = _wkhtml().wkhtmltoimage_version
        if not wkhtmltoimage_version or wkhtmltoimage_version < parse_version('0.12.0'):
            raise UserError(self.env._('wkhtmltoimage 0.12.0^ is required in order to render images from html'))
        command_args = [
            '--disable-local-file-access', '--disable-javascript',
            '--quiet',
            '--width', str(width), '--height', str(height),
            '--format', image_format,
        ]
        with ExitStack() as stack:
            files = []
            for body in bodies:
                (input_fd, input_path) = tempfile.mkstemp(suffix='.html', prefix='report_image_html_input.tmp.')
                (output_fd, output_path) = tempfile.mkstemp(suffix=f'.{image_format}', prefix='report_image_output.tmp.')
                stack.callback(os.remove, input_path)
                stack.callback(os.remove, output_path)
                os.close(output_fd)
                with closing(os.fdopen(input_fd, 'wb')) as input_file:
                    input_file.write(body.encode())
                files.append((input_path, output_path))
            output_images = []
            for (input_path, output_path) in files:
                wkhtmltoimage = [_wkhtml().wkhtmltoimage_bin, *command_args, input_path, output_path]
                # start and block, no need for parallelism for now
                completed_process = subprocess.run(wkhtmltoimage, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=False, encoding='utf-8')
                if completed_process.returncode:
                    message = self.env._(
                        'Wkhtmltoimage failed (error code: %(error_code)s). Message: %(error_message_end)s',
                        error_code=completed_process.returncode,
                        error_message_end=completed_process.stderr[-1000:] or '(empty stderr)',
                    )
                    _logger.warning(message)
                    output_images.append(None)
                else:
                    with open(output_path, 'rb') as output_file:
                        output_images.append(output_file.read())
        return output_images

    def _run_pdf_engine_with_documents(self, engine_name, documents, page_setup, **kwargs):
        if engine_name != 'wkhtmltopdf':
            return super()._run_pdf_engine_with_documents(engine_name, documents, page_setup, **kwargs)

        assert isinstance(self, IrActionsReport)

        # Build the base command args for wkhtmltopdf bin
        command_args = self._build_wkhtmltopdf_args(
            page_setup,
            set_viewport_size=kwargs.get('set_viewport_size', False),
        )

        with ExitStack() as stack:

            # Passing the cookie to wkhtmltopdf in order to resolve internal links.
            if request and request.db:
                # Create a temporary session which will not create device logs
                temp_session = session_store().new()
                temp_session.update({
                    **request.session,
                    'debug': '',
                    '_trace_disable': True,
                })
                if temp_session.uid:
                    update_session_token(temp_session, self.env)
                session_store().save(temp_session)
                stack.callback(session_store().delete, temp_session)

                base_url = self._get_report_url()
                domain = urlparse(base_url).hostname
                cookie = f'session_id={temp_session.sid}; HttpOnly; domain={domain}; path=/;'
                cookie_jar_file = stack.enter_context(tempfile.NamedTemporaryFile(suffix='.txt', prefix='report.cookie_jar.tmp.', delete_on_close=False))
                with closing(cookie_jar_file):
                    cookie_jar_file.write(cookie.encode())
                command_args.extend(['--cookie-jar', cookie_jar_file.name])

            decoration_paths = {}

            def decoration_path(kind, html):
                # documents sharing a decoration share its file
                if (kind, html) not in decoration_paths:
                    decoration_file = stack.enter_context(tempfile.NamedTemporaryFile(suffix='.html', prefix=f'report.{kind}.tmp.', delete_on_close=False))
                    with closing(decoration_file):
                        decoration_file.write(html.encode())
                    decoration_paths[kind, html] = decoration_file.name
                return decoration_paths[kind, html]

            pages_command_args = []
            body_idx = 0
            for body_idx, document in enumerate(documents):
                body = document.body
                prefix = f'report.body.tmp.{body_idx}.'
                body_file = stack.enter_context(tempfile.NamedTemporaryFile(suffix='.html', prefix=prefix, delete_on_close=False))
                with closing(body_file):
                    # HACK: wkhtmltopdf doesn't like big table at all and the
                    #       processing time become exponential with the number
                    #       of rows (like 1H for 250k rows).
                    #
                    #       So we split the table into multiple tables containing
                    #       500 rows each. This reduce the processing time to 1min
                    #       for 250k rows. The number 500 was taken from opw-1689673
                    if len(body) < 4 * 1024 * 1024:  # 4Mib
                        body_file.write(body.encode())
                    else:
                        tree = lxml.html.fromstring(body)
                        _split_table(tree, 500)
                        body_file.write(lxml.html.tostring(tree))
                # the decorations following a page only apply to it
                pages_command_args += ['page', body_file.name]
                if document.header:
                    pages_command_args += ['--header-html', decoration_path('header', document.header)]
                if document.footer:
                    pages_command_args += ['--footer-html', decoration_path('footer', document.footer)]

            pdf_report = stack.enter_context(tempfile.NamedTemporaryFile(suffix='.pdf', prefix='report.tmp.', delete_on_close=False))
            pdf_report.close()
            pdf_report_path = pdf_report.name

            process = self._run_wkhtmltopdf__(command_args + pages_command_args + [pdf_report_path])
            err = process.stderr or '(no stderr)'

            match process.returncode:
                case 0:
                    pass
                case 1 if body_idx and not _wkhtml().is_patched_qt:
                    if modules.module.current_test:
                        raise unittest.SkipTest("Unable to convert multiple documents via wkhtmltopdf using unpatched QT")
                    raise UserError(self.env._("Tried to convert multiple documents in wkhtmltopdf using unpatched QT"))
                case 1:
                    _logger.warning("wkhtmltopdf: %s", err)
                case -11:
                    message = self.env._(
                        'Wkhtmltopdf failed (error code: %(error_code)s). Memory limit too low or maximum file number of subprocess reached. Message : %(message)s',
                        error_code=-11,
                        message=err[-1000:],
                    )
                    _logger.warning(message)
                    raise UserError(message)
                case c:
                    message = self.env._(
                        'Wkhtmltopdf failed (error code: %(error_code)s). Message: %(message)s',
                        error_code=c,
                        message=err[-1000:],
                    )
                    _logger.warning(message)
                    raise UserError(message)

            with open(pdf_report_path, 'rb') as pdf_document:
                pdf_content = pdf_document.read()

        return pdf_content
