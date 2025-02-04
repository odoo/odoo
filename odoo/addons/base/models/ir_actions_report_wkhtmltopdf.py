import logging
import lxml.html
import os
import re
import subprocess
import tempfile
import unittest

from contextlib import closing, ExitStack
from itertools import islice
from lxml import etree
from urllib.parse import urlparse

from odoo import api, models, fields, modules, tools, _
from odoo.exceptions import UserError
from odoo.http import request, root
from odoo.service import security
from odoo.tools.misc import find_in_path
from odoo.tools import config, parse_version, split_every

_logger = logging.getLogger(__name__)


def _get_wkhtmltopdf_bin():
    return find_in_path('wkhtmltopdf')


def _get_wkhtmltoimage_bin():
    return find_in_path('wkhtmltoimage')


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


# Check the presence of Wkhtmltopdf and return its version at Odoo start-up
wkhtmltopdf_state = 'install'
wkhtmltopdf_dpi_zoom_ratio = False
try:
    process = subprocess.Popen(
        [_get_wkhtmltopdf_bin(), '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
except (OSError, IOError):
    _logger.info('You need Wkhtmltopdf to print a pdf version of the reports.')
else:
    _logger.info('Will use the Wkhtmltopdf binary at %s' % _get_wkhtmltopdf_bin())
    out, err = process.communicate()
    match = re.search(b'([0-9.]+)', out)
    if match:
        version = match.group(0).decode('ascii')
        if parse_version(version) < parse_version('0.12.0'):
            _logger.info('Upgrade Wkhtmltopdf to (at least) 0.12.0')
            wkhtmltopdf_state = 'upgrade'
        else:
            wkhtmltopdf_state = 'ok'
        if parse_version(version) >= parse_version('0.12.2'):
            wkhtmltopdf_dpi_zoom_ratio = True

        if config['workers'] == 1:
            _logger.info('You need to start Odoo with at least two workers to print a pdf version of the reports.')
            wkhtmltopdf_state = 'workers'
    else:
        _logger.info('Wkhtmltopdf seems to be broken.')
        wkhtmltopdf_state = 'broken'

wkhtmltoimage_version = None
try:
    process = subprocess.Popen(
        [_get_wkhtmltoimage_bin(), '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
except OSError:
    _logger.info('You need Wkhtmltoimage to generate images from html.')
else:
    _logger.info('Will use the Wkhtmltoimage binary at %s', _get_wkhtmltoimage_bin())
    out, err = process.communicate()
    match = re.search(b'([0-9.]+)', out)
    if match:
        wkhtmltoimage_version = parse_version(match.group(0).decode('ascii'))
        if config['workers'] == 1:
            _logger.info('You need to start Odoo with at least two workers to convert images to html.')
    else:
        _logger.info('Wkhtmltoimage seems to be broken.')


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    report_type = fields.Selection(selection_add=[('qweb-pdf-wkhtmltopdf', 'PDF (Wkhtmltopdf)')], default='qweb-pdf', ondelete={'qweb-pdf-wkhtmltopdf': 'set qweb-pdf'})

    @api.model
    def get_pdf_engine_state(self, engine_name=None):
        if not engine_name or engine_name == 'wkhtmltopdf':
            return 'wkhtmltopdf', wkhtmltopdf_state
        return super().get_pdf_engine_state(engine_name)

    @api.model
    def _build_wkhtmltopdf_args(
            self,
            paperformat_id,
            landscape,
            specific_paperformat_args=None,
            set_viewport_size=False):
        '''Build arguments understandable by wkhtmltopdf bin.

        :param paperformat_id: A report.paperformat record.
        :param landscape: Force the report orientation to be landscape.
        :param specific_paperformat_args: A dictionary containing prioritized wkhtmltopdf arguments.
        :param set_viewport_size: Enable a viewport sized '1024x1280' or '1280x1024' depending of landscape arg.
        :return: A list of string representing the wkhtmltopdf process command args.
        '''
        if landscape is None and specific_paperformat_args and specific_paperformat_args.get('data-report-landscape'):
            landscape = specific_paperformat_args.get('data-report-landscape')

        command_args = ['--disable-local-file-access']
        if set_viewport_size:
            command_args.extend(['--viewport-size', landscape and '1024x1280' or '1280x1024'])

        # Less verbose error messages
        command_args.extend(['--quiet'])

        # Build paperformat args
        if paperformat_id:
            if paperformat_id.format and paperformat_id.format != 'custom':
                command_args.extend(['--page-size', paperformat_id.format])

            if paperformat_id.page_height and paperformat_id.page_width and paperformat_id.format == 'custom':
                command_args.extend(['--page-width', str(paperformat_id.page_width) + 'mm'])
                command_args.extend(['--page-height', str(paperformat_id.page_height) + 'mm'])

            if specific_paperformat_args and specific_paperformat_args.get('data-report-margin-top'):
                command_args.extend(['--margin-top', str(specific_paperformat_args['data-report-margin-top'])])
            else:
                command_args.extend(['--margin-top', str(paperformat_id.margin_top)])

            dpi = None
            if specific_paperformat_args and specific_paperformat_args.get('data-report-dpi'):
                dpi = int(specific_paperformat_args['data-report-dpi'])
            elif paperformat_id.dpi:
                if os.name == 'nt' and int(paperformat_id.dpi) <= 95:
                    _logger.info("Generating PDF on Windows platform require DPI >= 96. Using 96 instead.")
                    dpi = 96
                else:
                    dpi = paperformat_id.dpi
            if dpi:
                command_args.extend(['--dpi', str(dpi)])
                if wkhtmltopdf_dpi_zoom_ratio:
                    command_args.extend(['--zoom', str(96.0 / dpi)])

            if specific_paperformat_args and specific_paperformat_args.get('data-report-header-spacing'):
                command_args.extend(['--header-spacing', str(specific_paperformat_args['data-report-header-spacing'])])
            elif paperformat_id.header_spacing:
                command_args.extend(['--header-spacing', str(paperformat_id.header_spacing)])

            command_args.extend(['--margin-left', str(paperformat_id.margin_left)])

            if specific_paperformat_args and specific_paperformat_args.get('data-report-margin-bottom'):
                command_args.extend(['--margin-bottom', str(specific_paperformat_args['data-report-margin-bottom'])])
            else:
                command_args.extend(['--margin-bottom', str(paperformat_id.margin_bottom)])

            command_args.extend(['--margin-right', str(paperformat_id.margin_right)])
            if not landscape and paperformat_id.orientation:
                command_args.extend(['--orientation', str(paperformat_id.orientation)])
            if paperformat_id.header_line:
                command_args.extend(['--header-line'])
            if paperformat_id.disable_shrinking:
                command_args.extend(['--disable-smart-shrinking'])

        # Add extra time to allow the page to render
        delay = self.env['ir.config_parameter'].sudo().get_param('report.print_delay', '1000')
        command_args.extend(['--javascript-delay', delay])

        if landscape:
            command_args.extend(['--orientation', 'landscape'])

        return command_args

    @api.model
    def _run_wkhtmltoimage(self, bodies, width, height, image_format="jpg"):
        """
        :bodies str: valid html documents as strings
        :param width int: width in pixels
        :param height int: height in pixels
        :param image_format union['jpg', 'png']: format of the image
        :return list[bytes|None]:
        """
        if (modules.module.current_test or tools.config['test_enable']) and not self.env.context.get('force_image_rendering'):
            return [None] * len(bodies)
        if not wkhtmltoimage_version or wkhtmltoimage_version < parse_version('0.12.0'):
            raise UserError(_('wkhtmltoimage 0.12.0^ is required in order to render images from html'))
        command_args = [
            '--disable-local-file-access', '--disable-javascript',
            '--quiet',
            '--width', str(width), '--height', str(height),
            '--format', image_format,
        ]
        with ExitStack() as stack:
            files = []
            for body in bodies:
                input_file = stack.enter_context(tempfile.NamedTemporaryFile(suffix='.html', prefix='report_image_html_input.tmp.'))
                output_file = stack.enter_context(tempfile.NamedTemporaryFile(suffix=f'.{image_format}', prefix='report_image_output.tmp.'))
                input_file.write(body.encode())
                files.append((input_file, output_file))
            output_images = []
            for input_file, output_file in files:
                # smaller bodies may be held in a python buffer until close, force flush
                input_file.flush()
                wkhtmltoimage = [_get_wkhtmltoimage_bin()] + command_args + [input_file.name, output_file.name]
                # start and block, no need for parallelism for now
                completed_process = subprocess.run(wkhtmltoimage, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=False)
                if completed_process.returncode:
                    message = _(
                        'Wkhtmltoimage failed (error code: %(error_code)s). Message: %(error_message_end)s',
                        error_code=completed_process.returncode,
                        error_message_end=completed_process.stderr[-1000:],
                    )
                    _logger.warning(message)
                    output_images.append(None)
                else:
                    output_images.append(output_file.read())
        return output_images

    @api.model
    def _run_wkhtmltopdf(
            self,
            bodies,
            report_ref=False,
            header=None,
            footer=None,
            landscape=False,
            specific_paperformat_args=None,
            set_viewport_size=False):
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
        paperformat_id = self._get_report(report_ref).get_paperformat() if report_ref else self.get_paperformat()

        # Build the base command args for wkhtmltopdf bin
        command_args = self._build_wkhtmltopdf_args(
            paperformat_id,
            landscape,
            specific_paperformat_args=specific_paperformat_args,
            set_viewport_size=set_viewport_size)

        files_command_args = []

        def delete_file(file_path):
            try:
                os.unlink(file_path)
            except OSError:
                _logger.error('Error when trying to remove file %s', file_path)

        with ExitStack() as stack:

            # Passing the cookie to wkhtmltopdf in order to resolve internal links.
            if request and request.db:
                # Create a temporary session which will not create device logs
                temp_session = root.session_store.new()
                temp_session.update({
                    **request.session,
                    '_trace_disable': True,
                })
                if temp_session.uid:
                    temp_session.session_token = security.compute_session_token(temp_session, self.env)
                root.session_store.save(temp_session)
                stack.callback(root.session_store.delete, temp_session)

                base_url = self._get_report_url()
                domain = urlparse(base_url).hostname
                cookie = f'session_id={temp_session.sid}; HttpOnly; domain={domain}; path=/;'
                cookie_jar_file_fd, cookie_jar_file_path = tempfile.mkstemp(suffix='.txt', prefix='report.cookie_jar.tmp.')
                stack.callback(delete_file, cookie_jar_file_path)
                with closing(os.fdopen(cookie_jar_file_fd, 'wb')) as cookie_jar_file:
                    cookie_jar_file.write(cookie.encode())
                command_args.extend(['--cookie-jar', cookie_jar_file_path])

            if header:
                head_file_fd, head_file_path = tempfile.mkstemp(suffix='.html', prefix='report.header.tmp.')
                with closing(os.fdopen(head_file_fd, 'wb')) as head_file:
                    head_file.write(header.encode())
                stack.callback(delete_file, head_file_path)
                files_command_args.extend(['--header-html', head_file_path])
            if footer:
                foot_file_fd, foot_file_path = tempfile.mkstemp(suffix='.html', prefix='report.footer.tmp.')
                with closing(os.fdopen(foot_file_fd, 'wb')) as foot_file:
                    foot_file.write(footer.encode())
                stack.callback(delete_file, foot_file_path)
                files_command_args.extend(['--footer-html', foot_file_path])

            paths = []
            for i, body in enumerate(bodies):
                prefix = '%s%d.' % ('report.body.tmp.', i)
                body_file_fd, body_file_path = tempfile.mkstemp(suffix='.html', prefix=prefix)
                with closing(os.fdopen(body_file_fd, 'wb')) as body_file:
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
                paths.append(body_file_path)
                stack.callback(delete_file, body_file_path)

            pdf_report_fd, pdf_report_path = tempfile.mkstemp(suffix='.pdf', prefix='report.tmp.')
            os.close(pdf_report_fd)
            stack.callback(delete_file, pdf_report_path)

            wkhtmltopdf = [_get_wkhtmltopdf_bin()] + command_args + files_command_args + paths + [pdf_report_path]
            process = subprocess.Popen(wkhtmltopdf, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8")
            _out, err = process.communicate()

            match process.returncode:
                case 0:
                    pass
                case 1:
                    if len(bodies) > 1:
                        v = subprocess.run([_get_wkhtmltopdf_bin(), '--version'], stdout=subprocess.PIPE, check=True, encoding="utf-8")
                        if '(with patched qt)' not in v.stdout:
                            if modules.module.current_test or tools.config['test_enable']:
                                raise unittest.SkipTest("Unable to convert multiple documents via wkhtmltopdf using unpatched QT")
                            raise UserError(_("Tried to convert multiple documents in wkhtmltopdf using unpatched QT"))

                    _logger.warning("wkhtmltopdf: %s", err)
                case c:
                    message = _(
                        'Wkhtmltopdf failed (error code: %(error_code)s). Memory limit too low or maximum file number of subprocess reached. Message : %(message)s',
                        error_code=c,
                        message=err[-1000:],
                    ) if c == -11 else _(
                        'Wkhtmltopdf failed (error code: %(error_code)s). Message: %(message)s',
                        error_code=c,
                        message=err[-1000:],
                    )
                    _logger.warning(message)
                    raise UserError(message)

            with open(pdf_report_path, 'rb') as pdf_document:
                pdf_content = pdf_document.read()

        return pdf_content
