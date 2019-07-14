# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, tools, SUPERUSER_ID, _
from odoo.exceptions import UserError, AccessError
from odoo.tools.safe_eval import safe_eval
from odoo.tools.misc import find_in_path
from odoo.tools import config
from odoo.sql_db import TestCursor
from odoo.http import request
from odoo.osv.expression import NEGATIVE_TERM_OPERATORS, FALSE_DOMAIN

import time
import base64
import io
import logging
import os
import lxml.html
import tempfile
import subprocess
import re

from lxml import etree
from contextlib import closing
from distutils.version import LooseVersion
from reportlab.graphics.barcode import createBarcodeDrawing
from PyPDF2 import PdfFileWriter, PdfFileReader
from collections import OrderedDict
from collections.abc import Iterable


_logger = logging.getLogger(__name__)

# A lock occurs when the user wants to print a report having multiple barcode while the server is
# started in threaded-mode. The reason is that reportlab has to build a cache of the T1 fonts
# before rendering a barcode (done in a C extension) and this part is not thread safe. We attempt
# here to init the T1 fonts cache at the start-up of Odoo so that rendering of barcode in multiple
# thread does not lock the server.
try:
    createBarcodeDrawing('Code128', value='foo', format='png', width=100, height=100, humanReadable=1).asString('png')
except Exception:
    pass


def _get_wkhtmltopdf_bin():
    return find_in_path('wkhtmltopdf')


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
        if LooseVersion(version) < LooseVersion('0.12.0'):
            _logger.info('Upgrade Wkhtmltopdf to (at least) 0.12.0')
            wkhtmltopdf_state = 'upgrade'
        else:
            wkhtmltopdf_state = 'ok'
        if LooseVersion(version) >= LooseVersion('0.12.2'):
            wkhtmltopdf_dpi_zoom_ratio = True

        if config['workers'] == 1:
            _logger.info('You need to start Odoo with at least two workers to print a pdf version of the reports.')
            wkhtmltopdf_state = 'workers'
    else:
        _logger.info('Wkhtmltopdf seems to be broken.')
        wkhtmltopdf_state = 'broken'


class IrActionsReport(models.Model):
    _name = 'ir.actions.report'
    _description = 'Report Action'
    _inherit = 'ir.actions.actions'
    _table = 'ir_act_report_xml'
    _sequence = 'ir_actions_id_seq'
    _order = 'name'

    name = fields.Char(translate=True)
    type = fields.Char(default='ir.actions.report')
    binding_type = fields.Selection(default='report')
    model = fields.Char(required=True, string='Model Name')
    model_id = fields.Many2one('ir.model', string='Model', compute='_compute_model_id', search='_search_model_id')

    report_type = fields.Selection([
        ('qweb-html', 'HTML'),
        ('qweb-pdf', 'PDF'),
        ('qweb-text', 'Text'),
    ], required=True, default='qweb-pdf',
    help='The type of the report that will be rendered, each one having its own'
        ' rendering method. HTML means the report will be opened directly in your'
        ' browser PDF means the report will be rendered using Wkhtmltopdf and'
        ' downloaded by the user.')
    report_name = fields.Char(string='Template Name', required=True,
                              help="For QWeb reports, name of the template used in the rendering. The method 'render_html' of the model 'report.template_name' will be called (if any) to give the html. For RML reports, this is the LocalService name.")
    report_file = fields.Char(string='Report File', required=False, readonly=False, store=True,
                              help="The path to the main report file (depending on Report Type) or empty if the content is in another field")
    groups_id = fields.Many2many('res.groups', 'res_groups_report_rel', 'uid', 'gid', string='Groups')
    multi = fields.Boolean(string='On Multiple Doc.', help="If set to true, the action will not be displayed on the right toolbar of a form view.")

    paperformat_id = fields.Many2one('report.paperformat', 'Paper Format')
    print_report_name = fields.Char('Printed Report Name',
                                    help="This is the filename of the report going to download. Keep empty to not change the report filename. You can use a python expression with the 'object' and 'time' variables.")
    attachment_use = fields.Boolean(string='Reload from Attachment',
                                    help='If you check this, then the second time the user prints with same attachment name, it returns the previous report.')
    attachment = fields.Char(string='Save as Attachment Prefix',
                             help='This is the filename of the attachment used to store the printing result. Keep empty to not save the printed reports. You can use a python expression with the object and time variables.')

    @api.depends('model')
    def _compute_model_id(self):
        for action in self:
            action.model_id = self.env['ir.model']._get(action.model).id

    def _search_model_id(self, operator, value):
        ir_model_ids = None
        if isinstance(value, str):
            names = self.env['ir.model'].name_search(value, operator=operator)
            ir_model_ids = [n[0] for n in names]

        elif isinstance(value, Iterable):
            ir_model_ids = value

        elif isinstance(value, int) and not isinstance(value, bool):
            ir_model_ids = [value]

        if ir_model_ids:
            operator = 'not in' if operator in NEGATIVE_TERM_OPERATORS else 'in'
            ir_model = self.env['ir.model'].browse(ir_model_ids)
            return [('model', operator, ir_model.mapped('model'))]
        elif isinstance(value, bool) or value is None:
            return [('model', operator, value)]
        else:
            return FALSE_DOMAIN

    @api.multi
    def associated_view(self):
        """Used in the ir.actions.report form view in order to search naively after the view(s)
        used in the rendering.
        """
        self.ensure_one()
        action_ref = self.env.ref('base.action_ui_view')
        if not action_ref or len(self.report_name.split('.')) < 2:
            return False
        action_data = action_ref.read()[0]
        action_data['domain'] = [('name', 'ilike', self.report_name.split('.')[1]), ('type', '=', 'qweb')]
        return action_data

    @api.multi
    def create_action(self):
        """ Create a contextual action for each report. """
        for report in self:
            model = self.env['ir.model']._get(report.model)
            report.write({'binding_model_id': model.id, 'binding_type': 'report'})
        return True

    @api.multi
    def unlink_action(self):
        """ Remove the contextual actions created for the reports. """
        self.check_access_rights('write', raise_exception=True)
        self.filtered('binding_model_id').write({'binding_model_id': False})
        return True

    #--------------------------------------------------------------------------
    # Main report methods
    #--------------------------------------------------------------------------
    @api.multi
    def retrieve_attachment(self, record):
        '''Retrieve an attachment for a specific record.

        :param record: The record owning of the attachment.
        :param attachment_name: The optional name of the attachment.
        :return: A recordset of length <=1 or None
        '''
        attachment_name = safe_eval(self.attachment, {'object': record, 'time': time})
        if not attachment_name:
            return None
        return self.env['ir.attachment'].search([
                ('datas_fname', '=', attachment_name),
                ('res_model', '=', self.model),
                ('res_id', '=', record.id)
        ], limit=1)

    @api.multi
    def postprocess_pdf_report(self, record, buffer):
        '''Hook to handle post processing during the pdf report generation.
        The basic behavior consists to create a new attachment containing the pdf
        base64 encoded.

        :param record_id: The record that will own the attachment.
        :param pdf_content: The optional name content of the file to avoid reading both times.
        :return: A modified buffer if the previous one has been modified, None otherwise.
        '''
        attachment_name = safe_eval(self.attachment, {'object': record, 'time': time})
        if not attachment_name:
            return None
        attachment_vals = {
            'name': attachment_name,
            'datas': base64.encodestring(buffer.getvalue()),
            'datas_fname': attachment_name,
            'res_model': self.model,
            'res_id': record.id,
        }
        try:
            self.env['ir.attachment'].create(attachment_vals)
        except AccessError:
            _logger.info("Cannot save PDF report %r as attachment", attachment_vals['name'])
        else:
            _logger.info('The PDF document %s is now saved in the database', attachment_vals['name'])
        return buffer

    @api.model
    def get_wkhtmltopdf_state(self):
        '''Get the current state of wkhtmltopdf: install, ok, upgrade, workers or broken.
        * install: Starting state.
        * upgrade: The binary is an older version (< 0.12.0).
        * ok: A binary was found with a recent version (>= 0.12.0).
        * workers: Not enough workers found to perform the pdf rendering process (< 2 workers).
        * broken: A binary was found but not responding.

        :return: wkhtmltopdf_state
        '''
        return wkhtmltopdf_state

    @api.model
    def get_paperformat(self):
        return self.paperformat_id or self.env.user.company_id.paperformat_id

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

        # Passing the cookie to wkhtmltopdf in order to resolve internal links.
        try:
            if request:
                command_args.extend(['--cookie', 'session_id', request.session.sid])
        except AttributeError:
            pass

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
            command_args.extend(['--margin-bottom', str(paperformat_id.margin_bottom)])
            command_args.extend(['--margin-right', str(paperformat_id.margin_right)])
            if not landscape and paperformat_id.orientation:
                command_args.extend(['--orientation', str(paperformat_id.orientation)])
            if paperformat_id.header_line:
                command_args.extend(['--header-line'])

        if landscape:
            command_args.extend(['--orientation', 'landscape'])

        return command_args

    @api.multi
    def _prepare_html(self, html):
        '''Divide and recreate the header/footer html by merging all found in html.
        The bodies are extracted and added to a list. Then, extract the specific_paperformat_args.
        The idea is to put all headers/footers together. Then, we will use a javascript trick
        (see minimal_layout template) to set the right header/footer during the processing of wkhtmltopdf.
        This allows the computation of multiple reports in a single call to wkhtmltopdf.

        :param html: The html rendered by render_qweb_html.
        :type: bodies: list of string representing each one a html body.
        :type header: string representing the html header.
        :type footer: string representing the html footer.
        :type specific_paperformat_args: dictionary of prioritized paperformat values.
        :return: bodies, header, footer, specific_paperformat_args
        '''
        IrConfig = self.env['ir.config_parameter'].sudo()
        base_url = IrConfig.get_param('report.url') or IrConfig.get_param('web.base.url')

        # Return empty dictionary if 'web.minimal_layout' not found.
        layout = self.env.ref('web.minimal_layout', False)
        if not layout:
            return {}
        layout = self.env['ir.ui.view'].browse(self.env['ir.ui.view'].get_view_id('web.minimal_layout'))

        root = lxml.html.fromstring(html)
        match_klass = "//div[contains(concat(' ', normalize-space(@class), ' '), ' {} ')]"

        header_node = etree.Element('div', id='minimal_layout_report_headers')
        footer_node = etree.Element('div', id='minimal_layout_report_footers')
        bodies = []
        res_ids = []

        body_parent = root.xpath('//main')[0]
        # Retrieve headers
        for node in root.xpath(match_klass.format('header')):
            body_parent = node.getparent()
            node.getparent().remove(node)
            header_node.append(node)

        # Retrieve footers
        for node in root.xpath(match_klass.format('footer')):
            body_parent = node.getparent()
            node.getparent().remove(node)
            footer_node.append(node)

        # Retrieve bodies
        for node in root.xpath(match_klass.format('article')):
            layout_with_lang = layout
            # set context language to body language
            if node.get('data-oe-lang'):
                layout_with_lang = layout_with_lang.with_context(lang=node.get('data-oe-lang'))
            body = layout_with_lang.render(dict(subst=False, body=lxml.html.tostring(node), base_url=base_url))
            bodies.append(body)
            if node.get('data-oe-model') == self.model:
                res_ids.append(int(node.get('data-oe-id', 0)))
            else:
                res_ids.append(None)

        if not bodies:
            body = bytearray().join([lxml.html.tostring(c) for c in body_parent.getchildren()])
            bodies.append(body)

        # Get paperformat arguments set in the root html tag. They are prioritized over
        # paperformat-record arguments.
        specific_paperformat_args = {}
        for attribute in root.items():
            if attribute[0].startswith('data-report-'):
                specific_paperformat_args[attribute[0]] = attribute[1]

        header = layout.render(dict(subst=True, body=lxml.html.tostring(header_node), base_url=base_url))
        footer = layout.render(dict(subst=True, body=lxml.html.tostring(footer_node), base_url=base_url))

        return bodies, res_ids, header, footer, specific_paperformat_args

    @api.model
    def _run_wkhtmltopdf(
            self,
            bodies,
            header=None,
            footer=None,
            landscape=False,
            specific_paperformat_args=None,
            set_viewport_size=False):
        '''Execute wkhtmltopdf as a subprocess in order to convert html given in input into a pdf
        document.

        :param bodies: The html bodies of the report, one per page.
        :param header: The html header of the report containing all headers.
        :param footer: The html footer of the report containing all footers.
        :param landscape: Force the pdf to be rendered under a landscape format.
        :param specific_paperformat_args: dict of prioritized paperformat arguments.
        :param set_viewport_size: Enable a viewport sized '1024x1280' or '1280x1024' depending of landscape arg.
        :return: Content of the pdf as a string
        '''
        paperformat_id = self.get_paperformat()

        # Build the base command args for wkhtmltopdf bin
        command_args = self._build_wkhtmltopdf_args(
            paperformat_id,
            landscape,
            specific_paperformat_args=specific_paperformat_args,
            set_viewport_size=set_viewport_size)

        files_command_args = []
        temporary_files = []
        if header:
            head_file_fd, head_file_path = tempfile.mkstemp(suffix='.html', prefix='report.header.tmp.')
            with closing(os.fdopen(head_file_fd, 'wb')) as head_file:
                head_file.write(header)
            temporary_files.append(head_file_path)
            files_command_args.extend(['--header-html', head_file_path])
        if footer:
            foot_file_fd, foot_file_path = tempfile.mkstemp(suffix='.html', prefix='report.footer.tmp.')
            with closing(os.fdopen(foot_file_fd, 'wb')) as foot_file:
                foot_file.write(footer)
            temporary_files.append(foot_file_path)
            files_command_args.extend(['--footer-html', foot_file_path])

        paths = []
        for i, body in enumerate(bodies):
            prefix = '%s%d.' % ('report.body.tmp.', i)
            body_file_fd, body_file_path = tempfile.mkstemp(suffix='.html', prefix=prefix)
            with closing(os.fdopen(body_file_fd, 'wb')) as body_file:
                body_file.write(body)
            paths.append(body_file_path)
            temporary_files.append(body_file_path)

        pdf_report_fd, pdf_report_path = tempfile.mkstemp(suffix='.pdf', prefix='report.tmp.')
        os.close(pdf_report_fd)
        temporary_files.append(pdf_report_path)

        try:
            wkhtmltopdf = [_get_wkhtmltopdf_bin()] + command_args + files_command_args + paths + [pdf_report_path]
            process = subprocess.Popen(wkhtmltopdf, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, err = process.communicate()

            if process.returncode not in [0, 1]:
                if process.returncode == -11:
                    message = _(
                        'Wkhtmltopdf failed (error code: %s). Memory limit too low or maximum file number of subprocess reached. Message : %s')
                else:
                    message = _('Wkhtmltopdf failed (error code: %s). Message: %s')
                raise UserError(message % (str(process.returncode), err[-1000:]))
            else:
                if err:
                    _logger.warning('wkhtmltopdf: %s' % err)
        except:
            raise

        with open(pdf_report_path, 'rb') as pdf_document:
            pdf_content = pdf_document.read()

        # Manual cleanup of the temporary files
        for temporary_file in temporary_files:
            try:
                os.unlink(temporary_file)
            except (OSError, IOError):
                _logger.error('Error when trying to remove file %s' % temporary_file)

        return pdf_content

    @api.model
    def _get_report_from_name(self, report_name):
        """Get the first record of ir.actions.report having the ``report_name`` as value for
        the field report_name.
        """
        report_obj = self.env['ir.actions.report']
        conditions = [('report_name', '=', report_name)]
        context = self.env['res.users'].context_get()
        return report_obj.with_context(context).search(conditions, limit=1)

    @api.model
    def barcode(self, barcode_type, value, width=600, height=100, humanreadable=0):
        if barcode_type == 'UPCA' and len(value) in (11, 12, 13):
            barcode_type = 'EAN13'
            if len(value) in (11, 12):
                value = '0%s' % value
        try:
            width, height, humanreadable = int(width), int(height), bool(int(humanreadable))
            barcode = createBarcodeDrawing(
                barcode_type, value=value, format='png', width=width, height=height,
                humanReadable=humanreadable
            )
            return barcode.asString('png')
        except (ValueError, AttributeError):
            if barcode_type == 'Code128':
                raise ValueError("Cannot convert into barcode.")
            else:
                return self.barcode('Code128', value, width=width, height=height, humanreadable=humanreadable)

    @api.multi
    def render_template(self, template, values=None):
        """Allow to render a QWeb template python-side. This function returns the 'ir.ui.view'
        render but embellish it with some variables/methods used in reports.
        :param values: additionnal methods/variables used in the rendering
        :returns: html representation of the template
        """
        if values is None:
            values = {}

        context = dict(self.env.context, inherit_branding=values.get('enable_editor'))

        # Browse the user instead of using the sudo self.env.user
        user = self.env['res.users'].browse(self.env.uid)
        website = None
        if request and hasattr(request, 'website'):
            if request.website is not None:
                website = request.website
                context = dict(context, translatable=context.get('lang') != request.env['ir.http']._get_default_lang().code)

        view_obj = self.env['ir.ui.view'].with_context(context)
        values.update(
            time=time,
            context_timestamp=lambda t: fields.Datetime.context_timestamp(self.with_context(tz=user.tz), t),
            editable=values.get('enable_editor'),
            user=user,
            res_company=user.company_id,
            website=website,
            web_base_url=self.env['ir.config_parameter'].sudo().get_param('web.base.url', default=''),
        )
        return view_obj.render_template(template, values)

    @api.multi
    def _post_pdf(self, save_in_attachment, pdf_content=None, res_ids=None):
        '''Merge the existing attachments by adding one by one the content of the attachments
        and then, we add the pdf_content if exists. Create the attachments for each record individually
        if required.

        :param save_in_attachment: The retrieved attachments as map record.id -> attachment_id.
        :param pdf_content: The pdf content newly generated by wkhtmltopdf.
        :param res_ids: the ids of record to allow postprocessing.
        :return: The pdf content of the merged pdf.
        '''

        def close_streams(streams):
            for stream in streams:
                try:
                    stream.close()
                except Exception:
                    pass

        # Check special case having only one record with existing attachment.
        if len(save_in_attachment) == 1 and not pdf_content:
            return base64.decodestring(list(save_in_attachment.values())[0].datas)

        # Create a list of streams representing all sub-reports part of the final result
        # in order to append the existing attachments and the potentially modified sub-reports
        # by the postprocess_pdf_report calls.
        streams = []

        # In wkhtmltopdf has been called, we need to split the pdf in order to call the postprocess method.
        if pdf_content:
            pdf_content_stream = io.BytesIO(pdf_content)
            # Build a record_map mapping id -> record
            record_map = {r.id: r for r in self.env[self.model].browse([res_id for res_id in res_ids if res_id])}

            # If no value in attachment or no record specified, only append the whole pdf.
            if not record_map or not self.attachment:
                streams.append(pdf_content_stream)
            else:
                if len(res_ids) == 1:
                    # Only one record, so postprocess directly and append the whole pdf.
                    if res_ids[0] in record_map and not res_ids[0] in save_in_attachment:
                        new_stream = self.postprocess_pdf_report(record_map[res_ids[0]], pdf_content_stream)
                        # If the buffer has been modified, mark the old buffer to be closed as well.
                        if new_stream and new_stream != pdf_content_stream:
                            close_streams([pdf_content_stream])
                            pdf_content_stream = new_stream
                    streams.append(pdf_content_stream)
                else:
                    # In case of multiple docs, we need to split the pdf according the records.
                    # To do so, we split the pdf based on outlines computed by wkhtmltopdf.
                    # An outline is a <h?> html tag found on the document. To retrieve this table,
                    # we look on the pdf structure using pypdf to compute the outlines_pages that is
                    # an array like [0, 3, 5] that means a new document start at page 0, 3 and 5.
                    reader = PdfFileReader(pdf_content_stream)
                    if reader.trailer['/Root'].get('/Dests'):
                        outlines_pages = sorted(
                            [outline.getObject()[0] for outline in reader.trailer['/Root']['/Dests'].values()])
                        assert len(outlines_pages) == len(res_ids)
                        for i, num in enumerate(outlines_pages):
                            to = outlines_pages[i + 1] if i + 1 < len(outlines_pages) else reader.numPages
                            attachment_writer = PdfFileWriter()
                            for j in range(num, to):
                                attachment_writer.addPage(reader.getPage(j))
                            stream = io.BytesIO()
                            attachment_writer.write(stream)
                            if res_ids[i] and res_ids[i] not in save_in_attachment:
                                new_stream = self.postprocess_pdf_report(record_map[res_ids[i]], stream)
                                # If the buffer has been modified, mark the old buffer to be closed as well.
                                if new_stream and new_stream != stream:
                                    close_streams([stream])
                                    stream = new_stream
                            streams.append(stream)
                        close_streams([pdf_content_stream])
                    else:
                        # If no outlines available, do not save each record
                        streams.append(pdf_content_stream)

        # If attachment_use is checked, the records already having an existing attachment
        # are not been rendered by wkhtmltopdf. So, create a new stream for each of them.
        if self.attachment_use:
            for attachment_id in save_in_attachment.values():
                content = base64.decodestring(attachment_id.datas)
                streams.append(io.BytesIO(content))

        # Build the final pdf.
        # If only one stream left, no need to merge them (and then, preserve embedded files).
        if len(streams) == 1:
            result = streams[0].getvalue()
        else:
            writer = PdfFileWriter()
            for stream in streams:
                reader = PdfFileReader(stream)
                writer.appendPagesFromReader(reader)
            result_stream = io.BytesIO()
            streams.append(result_stream)
            writer.write(result_stream)
            result = result_stream.getvalue()

        # We have to close the streams after PdfFileWriter's call to write()
        close_streams(streams)
        return result

    @api.multi
    def render_qweb_pdf(self, res_ids=None, data=None):
        if not data:
            data = {}
        data.setdefault('report_type', 'pdf')

        # remove editor feature in pdf generation
        data.update(enable_editor=False)

        # In case of test environment without enough workers to perform calls to wkhtmltopdf,
        # fallback to render_html.
        if (tools.config['test_enable'] or tools.config['test_file']) and not self.env.context.get('force_report_rendering'):
            return self.render_qweb_html(res_ids, data=data)

        # As the assets are generated during the same transaction as the rendering of the
        # templates calling them, there is a scenario where the assets are unreachable: when
        # you make a request to read the assets while the transaction creating them is not done.
        # Indeed, when you make an asset request, the controller has to read the `ir.attachment`
        # table.
        # This scenario happens when you want to print a PDF report for the first time, as the
        # assets are not in cache and must be generated. To workaround this issue, we manually
        # commit the writes in the `ir.attachment` table. It is done thanks to a key in the context.
        context = dict(self.env.context)
        if not config['test_enable']:
            context['commit_assetsbundle'] = True

        # Disable the debug mode in the PDF rendering in order to not split the assets bundle
        # into separated files to load. This is done because of an issue in wkhtmltopdf
        # failing to load the CSS/Javascript resources in time.
        # Without this, the header/footer of the reports randomly disapear
        # because the resources files are not loaded in time.
        # https://github.com/wkhtmltopdf/wkhtmltopdf/issues/2083
        context['debug'] = False

        # The test cursor prevents the use of another environnment while the current
        # transaction is not finished, leading to a deadlock when the report requests
        # an asset bundle during the execution of test scenarios. In this case, return
        # the html version.
        if isinstance(self.env.cr, TestCursor):
            return self.with_context(context).render_qweb_html(res_ids, data=data)[0]

        save_in_attachment = OrderedDict()
        if res_ids:
            # Dispatch the records by ones having an attachment and ones requesting a call to
            # wkhtmltopdf.
            Model = self.env[self.model]
            record_ids = Model.browse(res_ids)
            wk_record_ids = Model
            if self.attachment:
                for record_id in record_ids:
                    attachment_id = self.retrieve_attachment(record_id)
                    if attachment_id:
                        save_in_attachment[record_id.id] = attachment_id
                    if not self.attachment_use or not attachment_id:
                        wk_record_ids += record_id
            else:
                wk_record_ids = record_ids
            res_ids = wk_record_ids.ids

        # A call to wkhtmltopdf is mandatory in 2 cases:
        # - The report is not linked to a record.
        # - The report is not fully present in attachments.
        if save_in_attachment and not res_ids:
            _logger.info('The PDF report has been generated from attachments.')
            return self._post_pdf(save_in_attachment), 'pdf'

        if self.get_wkhtmltopdf_state() == 'install':
            # wkhtmltopdf is not installed
            # the call should be catched before (cf /report/check_wkhtmltopdf) but
            # if get_pdf is called manually (email template), the check could be
            # bypassed
            raise UserError(_("Unable to find Wkhtmltopdf on this system. The PDF can not be created."))

        html = self.with_context(context).render_qweb_html(res_ids, data=data)[0]

        # Ensure the current document is utf-8 encoded.
        html = html.decode('utf-8')

        bodies, html_ids, header, footer, specific_paperformat_args = self.with_context(context)._prepare_html(html)

        if self.attachment and set(res_ids) != set(html_ids):
            raise UserError(_("The report's template '%s' is wrong, please contact your administrator. \n\n"
                "Can not separate file to save as attachment because the report's template does not contains the attributes 'data-oe-model' and 'data-oe-id' on the div with 'article' classname.") %  self.name)

        pdf_content = self._run_wkhtmltopdf(
            bodies,
            header=header,
            footer=footer,
            landscape=context.get('landscape'),
            specific_paperformat_args=specific_paperformat_args,
            set_viewport_size=context.get('set_viewport_size'),
        )
        if res_ids:
            _logger.info('The PDF report has been generated for records %s.' % (str(res_ids)))
            return self._post_pdf(save_in_attachment, pdf_content=pdf_content, res_ids=html_ids), 'pdf'
        return pdf_content, 'pdf'

    @api.model
    def render_qweb_text(self, docids, data=None):
        if not data:
            data = {}
        data.setdefault('report_type', 'text')
        data = self._get_rendering_context(docids, data)
        return self.render_template(self.report_name, data), 'text'

    @api.model
    def render_qweb_html(self, docids, data=None):
        """This method generates and returns html version of a report.
        """
        if not data:
            data = {}
        data.setdefault('report_type', 'html')
        data = self._get_rendering_context(docids, data)
        return self.render_template(self.report_name, data), 'html'

    @api.model
    def _get_rendering_context_model(self):
        report_model_name = 'report.%s' % self.report_name
        return self.env.get(report_model_name)

    @api.model
    def _get_rendering_context(self, docids, data):
        # If the report is using a custom model to render its html, we must use it.
        # Otherwise, fallback on the generic html rendering.
        report_model = self._get_rendering_context_model()

        data = data and dict(data) or {}

        if report_model is not None:
            data.update(report_model._get_report_values(docids, data=data))
        else:
            docs = self.env[self.model].browse(docids)
            data.update({
                'doc_ids': docids,
                'doc_model': self.model,
                'docs': docs,
            })
        return data

    @api.multi
    def render(self, res_ids, data=None):
        report_type = self.report_type.lower().replace('-', '_')
        render_func = getattr(self, 'render_' + report_type, None)
        if not render_func:
            return None
        return render_func(res_ids, data=data)

    @api.noguess
    def report_action(self, docids, data=None, config=True):
        """Return an action of type ir.actions.report.

        :param docids: id/ids/browserecord of the records to print (if not used, pass an empty list)
        :param report_name: Name of the template to generate an action for
        """
        discard_logo_check = self.env.context.get('discard_logo_check')
        if (self.env.user._is_admin()) and ((not self.env.user.company_id.external_report_layout_id) or (not discard_logo_check and not self.env.user.company_id.logo)) and config:
            template = self.env.ref('base.view_company_report_form_with_print') if self.env.context.get('from_transient_model', False) else self.env.ref('base.view_company_report_form')
            return {
                'name': _('Choose Your Document Layout'),
                'type': 'ir.actions.act_window',
                'context': {'default_report_name': self.report_name, 'discard_logo_check': True},
                'view_type': 'form',
                'view_mode': 'form',
                'res_id': self.env.user.company_id.id,
                'res_model': 'res.company',
                'views': [(template.id, 'form')],
                'view_id': template.id,
                'target': 'new',
            }

        context = self.env.context
        if docids:
            if isinstance(docids, models.Model):
                active_ids = docids.ids
            elif isinstance(docids, int):
                active_ids = [docids]
            elif isinstance(docids, list):
                active_ids = docids
            context = dict(self.env.context, active_ids=active_ids)

        return {
            'context': context,
            'data': data,
            'type': 'ir.actions.report',
            'report_name': self.report_name,
            'report_type': self.report_type,
            'report_file': self.report_file,
            'name': self.name,
        }
