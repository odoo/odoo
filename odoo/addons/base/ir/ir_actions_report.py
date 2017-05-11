# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, tools, SUPERUSER_ID, _
from odoo.exceptions import MissingError, UserError, ValidationError, AccessError
from odoo.tools.safe_eval import safe_eval, test_python_expr
from odoo.tools.misc import find_in_path
from odoo.tools import config
from odoo.sql_db import TestCursor
from odoo.http import request

import time
import base64
import logging
import os
import lxml.html
import tempfile
import subprocess
import re

from collections import namedtuple
from contextlib import closing
from pyPdf import PdfFileWriter, PdfFileReader
from distutils.version import LooseVersion
from reportlab.graphics.barcode import createBarcodeDrawing


_logger = logging.getLogger(__name__)


WkhtmltopdfObj = namedtuple('WkhtmltopdfObj',
                            ['header', 'content', 'footer', 'res_id', 'attachment_id', 'attachment_name'])


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
try:
    process = subprocess.Popen(
        [_get_wkhtmltopdf_bin(), '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
except (OSError, IOError):
    _logger.info('You need Wkhtmltopdf to print a pdf version of the reports.')
else:
    _logger.info('Will use the Wkhtmltopdf binary at %s' % _get_wkhtmltopdf_bin())
    out, err = process.communicate()
    match = re.search('([0-9.]+)', out)
    if match:
        version = match.group(0)
        if LooseVersion(version) < LooseVersion('0.12.0'):
            _logger.info('Upgrade Wkhtmltopdf to (at least) 0.12.0')
            wkhtmltopdf_state = 'upgrade'
        else:
            wkhtmltopdf_state = 'ok'

        if config['workers'] == 1:
            _logger.info('You need to start Odoo with at least two workers to print a pdf version of the reports.')
            wkhtmltopdf_state = 'workers'
    else:
        _logger.info('Wkhtmltopdf seems to be broken.')
        wkhtmltopdf_state = 'broken'


def _merge_pdf(documents):
    '''Merge PDF files into one.

    :param documents: list of path of pdf files
    :returns: path of the merged pdf
    '''
    writer = PdfFileWriter()
    streams = []  # We have to close the streams *after* PdfFilWriter's call to write()
    for document in documents:
        pdfreport = file(document, 'rb')
        streams.append(pdfreport)
        reader = PdfFileReader(pdfreport)
        for page in range(0, reader.getNumPages()):
            writer.addPage(reader.getPage(page))

    merged_file_fd, merged_file_path = tempfile.mkstemp(suffix='.html', prefix='report.merged.tmp.')
    with closing(os.fdopen(merged_file_fd, 'w')) as merged_file:
        writer.write(merged_file)

    for stream in streams:
        stream.close()

    return merged_file_path


class IrActionsReport(models.Model):
    _name = 'ir.actions.report'
    _inherit = 'ir.actions.actions'
    _table = 'ir_act_report_xml'
    _sequence = 'ir_actions_id_seq'
    _order = 'name'

    name = fields.Char(translate=True)
    type = fields.Char(default='ir.actions.report')
    model = fields.Char(required=True)

    report_type = fields.Selection([('qweb-html', 'HTML'), ('qweb-pdf', 'PDF')], required=True, default='qweb-pdf',
                                   help='The type of the report that will be rendered, each one having its own rendering method.'
                                        'HTML means the report will be opened directly in your browser'
                                        'PDF means the report will be rendered using Wkhtmltopdf and downloaded by the user.')
    report_name = fields.Char(string='Template Name', required=True,
                              help="For QWeb reports, name of the template used in the rendering. The method 'render_html' of the model 'report.template_name' will be called (if any) to give the html. For RML reports, this is the LocalService name.")
    report_file = fields.Char(string='Report File', required=False, readonly=False, store=True,
                              help="The path to the main report file (depending on Report Type) or empty if the content is in another field")
    groups_id = fields.Many2many('res.groups', 'res_groups_report_rel', 'uid', 'gid', string='Groups')
    ir_values_id = fields.Many2one('ir.values', string='More Menu entry', readonly=True,
                                   help='More menu entry.', copy=False)
    multi = fields.Boolean(string='On Multiple Doc.', help="If set to true, the action will not be displayed on the right toolbar of a form view.")

    paperformat_id = fields.Many2one('report.paperformat', 'Paper format')
    print_report_name = fields.Char('Printed Report Name',
                                    help="This is the filename of the report going to download. Keep empty to not change the report filename. You can use a python expression with the object and time variables.")
    attachment_use = fields.Boolean(string='Reload from Attachment',
                                    help='If you check this, then the second time the user prints with same attachment name, it returns the previous report.')
    attachment = fields.Char(string='Save as Attachment Prefix',
                             help='This is the filename of the attachment used to store the printing result. Keep empty to not save the printed reports. You can use a python expression with the object and time variables.')


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
            ir_values = self.env['ir.values'].sudo().create({
                'name': report.name,
                'model': report.model,
                'key2': 'client_print_multi',
                'value': "ir.actions.report,%s" % report.id,
            })
            report.write({'ir_values_id': ir_values.id})
        return True

    @api.multi
    def unlink_action(self):
        """ Remove the contextual actions created for the reports. """
        self.check_access_rights('write', raise_exception=True)
        for report in self:
            if report.ir_values_id:
                try:
                    report.ir_values_id.sudo().unlink()
                except Exception:
                    raise UserError(_('Deletion of the action record failed.'))
        return True

    #--------------------------------------------------------------------------
    # Main report methods
    #--------------------------------------------------------------------------
    @api.model
    def retrieve_attachment(self, record_id, attachment_name=None):
        '''Retrieve an attachment for a specific record.

        :param res_id: The record_id.
        :param attachment_name: The name of the attachment.
        :return: A recordset of length <= 1
        '''
        if not attachment_name:
            attachment_name = safe_eval(self.attachment, {'object': record_id, 'time': time})
        return self.env['ir.attachment'].search([
                ('datas_fname', '=', attachment_name),
                ('res_model', '=', self.model),
                ('res_id', '=', record_id.id)
        ], limit=1)

    @api.model
    def create_wkhtmltopdf_obj(self, header, content, footer, res_id=None):
        '''Create an object using namedtuple that represents a "sub-report" in wkhtmltopdf.
        This object contains header, content, footer, res_id and data related to the attachment:
        * attachment_id: an existing attachment_id found for the record.
        * attachment_name: the expected name of the attachment created (if necessary) after calling wkhtmltopdf.

        :param header: The header as a string.
        :param content: The content as a string.
        :param footer: The footer as a string.
        :param res_id: The related record of the report.
        :return: A new instance of WkhtmltopdfObj.
        '''
        attachment_id = attachment_name = None
        if res_id and len(self._ids) == 1 and self.attachment_use and self.attachment:
            record_id = self.env[self.model].browse(res_id)
            attachment_name = safe_eval(self.attachment, {'object': record_id, 'time': time})
            attachment_id = self.retrieve_attachment(record_id, attachment_name)
        return WkhtmltopdfObj(
            header=header,
            content=content,
            footer=footer,
            res_id=res_id,
            attachment_id=attachment_id,
            attachment_name=attachment_name
        )

    @api.model
    def postprocess_pdf_report(self, res_id, attachment_content, attachment_name):
        '''Hook to handle post processing during the pdf report generation.
        The basic behavior consists to create a new attachment containing the pdf
        base64 encoded.

        :param res_id: The record id.
        :param attachment_content: The pdf content newly generated by wkhtmltopdf.
        :param attachment_name: The name of the attachment.
        '''
        attachment = {
            'name': attachment_name,
            'datas': base64.encodestring(attachment_content),
            'datas_fname': attachment_name,
            'res_model': self.model,
            'res_id': res_id,
        }
        try:
            self.env['ir.attachment'].create(attachment)
        except AccessError:
            _logger.info("Cannot save PDF report %r as attachment", attachment['name'])
        else:
            _logger.info('The PDF document %s is now saved in the database', attachment['name'])

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
    def _build_wkhtmltopdf_args(
            self,
            paperformat,
            landscape,
            specific_paperformat_args=None,
            set_viewport_size=False):
        '''Build arguments understandable by wkhtmltopdf bin.

        :param paperformat: A report.paperformat record.
        :param landscape: Force the report orientation to be landscape.
        :param specific_paperformat_args: A dictionary containing prioritized wkhtmltopdf arguments.
        :param set_viewport_size: Enable a viewport sized '1024x1280' or '1280x1024' depending of landscape arg.
        :return: A list of string representing the wkhtmltopdf arguments.
        '''
        command_args = []
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
        if paperformat:
            if paperformat.format and paperformat.format != 'custom':
                command_args.extend(['--page-size', paperformat.format])

            if paperformat.page_height and paperformat.page_width and paperformat.format == 'custom':
                command_args.extend(['--page-width', str(paperformat.page_width) + 'mm'])
                command_args.extend(['--page-height', str(paperformat.page_height) + 'mm'])

            if specific_paperformat_args and specific_paperformat_args.get('data-report-margin-top'):
                command_args.extend(['--margin-top', str(specific_paperformat_args['data-report-margin-top'])])
            else:
                command_args.extend(['--margin-top', str(paperformat.margin_top)])

            if specific_paperformat_args and specific_paperformat_args.get('data-report-dpi'):
                command_args.extend(['--dpi', str(specific_paperformat_args['data-report-dpi'])])
            elif paperformat.dpi:
                if os.name == 'nt' and int(paperformat.dpi) <= 95:
                    _logger.info("Generating PDF on Windows platform require DPI >= 96. Using 96 instead.")
                    command_args.extend(['--dpi', '96'])
                else:
                    command_args.extend(['--dpi', str(paperformat.dpi)])

            if specific_paperformat_args and specific_paperformat_args.get('data-report-header-spacing'):
                command_args.extend(['--header-spacing', str(specific_paperformat_args['data-report-header-spacing'])])
            elif paperformat.header_spacing:
                command_args.extend(['--header-spacing', str(paperformat.header_spacing)])

            command_args.extend(['--margin-left', str(paperformat.margin_left)])
            command_args.extend(['--margin-bottom', str(paperformat.margin_bottom)])
            command_args.extend(['--margin-right', str(paperformat.margin_right)])
            if not landscape and paperformat.orientation:
                command_args.extend(['--orientation', str(paperformat.orientation)])
            if paperformat.header_line:
                command_args.extend(['--header-line'])

        if landscape:
            command_args.extend(['--orientation', 'landscape'])

        return command_args

    @api.model
    def _extract_wkhtmltopdf_data_from_html(self, res_ids, html):
        '''Extract information from the html passed as parameter and returns it as
         a dictionary.

        :param res_ids: The records ids.
        :param html: The html as a string.
        :return: data found in the html as a dictionary.
        '''
        IrConfig = self.env['ir.config_parameter'].sudo()
        headers = []
        contents = []
        footers = []
        ids = []
        base_url = IrConfig.get_param('report.url') or IrConfig.get_param('web.base.url')

        # Return empty dictionary if 'web.minimal_layout' not found.
        layout = self.env.ref('web.minimal_layout', False)
        if not layout:
            return {}
        layout = self.env['ir.ui.view'].browse(self.env['ir.ui.view'].get_view_id('web.minimal_layout'))

        root = lxml.html.fromstring(html)
        match_klass = "//div[contains(concat(' ', normalize-space(@class), ' '), ' {} ')]"

        # Retrieve headers
        for node in root.xpath(match_klass.format('header')):
            body = lxml.html.tostring(node)
            header = layout.render(dict(subst=True, body=body, base_url=base_url))
            headers.append(header)

        # Retrieve footers
        for node in root.xpath(match_klass.format('footer')):
            body = lxml.html.tostring(node)
            footer = layout.render(dict(subst=True, body=body, base_url=base_url))
            footers.append(footer)

        # Retrieve content & ids
        for node in root.xpath(match_klass.format('article')):
            # Previously, we marked some reports to be saved in attachment via their ids, so we
            # must set a relation between report ids and report's content. We use the QWeb
            # branding in order to do so: searching after a node having a data-oe-model
            # attribute with the value of the current report model and read its oe-id attribute
            if res_ids and len(res_ids) == 1:
                report_id = res_ids[0]
            else:
                oemodelnode = node.find(".//*[@data-oe-model='%s']" % self.model)
                if oemodelnode is not None:
                    report_id = oemodelnode.get('data-oe-id')
                    if report_id:
                        report_id = int(report_id)
                else:
                    report_id = False

            # Extract the body
            body = lxml.html.tostring(node)
            content = layout.render(dict(subst=False, body=body, base_url=base_url))

            contents.append(content)
            ids.append(report_id)

        # Create a list of wkhtmltopdf_objs, each one representing a "sub-report".
        wkhtmltopdf_objs = []
        for i in range(0, len(contents)):
            header = headers[i] if headers else None
            footer = footers[i] if footers else None
            wkhtmltopdf_obj = self.create_wkhtmltopdf_obj(header, contents[i], footer, ids[i])
            wkhtmltopdf_objs.append(wkhtmltopdf_obj)

        # Get paperformat arguments set in the root html tag. They are prioritized over
        # paperformat-record arguments.
        specific_paperformat_args = {}
        for attribute in root.items():
            if attribute[0].startswith('data-report-'):
                specific_paperformat_args[attribute[0]] = attribute[1]

        return {
            'wkhtmltopdf_objs': wkhtmltopdf_objs,
            'specific_paperformat_args': specific_paperformat_args,
        }

    @api.model
    def _run_wkhtmltopdf(
            self,
            wkhtmltopdf_objs,
            landscape,
            paperformat,
            specific_paperformat_args=None,
            set_viewport_size=False):
        '''Execute wkhtmltopdf as a subprocess in order to convert html given in input into a pdf
        document.

        :param wkhtmltopdf_objs: A list of WkhtmltopdfObj generated by the method create_wkhtmltopdf_obj in ir.actions.report
        :param landscape: Force the pdf to be rendered under a landscape format.
        :param paperformat: ir.actions.report.paperformat to generate the wkhtmltopf arguments.
        :param specific_paperformat_args: dict of prioritized paperformat arguments.
        :param set_viewport_size: Enable a viewport sized '1024x1280' or '1280x1024' depending of landscape arg.
        :param postprocess_method: A method that will be called for each "sub-report" to perform a post processing like
                                    the generation of report attachments.
        :return: Content of the pdf as a string
        '''
        # Build the base command args for wkhtmltopdf bin
        command_args = self._build_wkhtmltopdf_args(
            paperformat,
            landscape,
            specific_paperformat_args=specific_paperformat_args,
            set_viewport_size=set_viewport_size)

        # Execute WKhtmltopdf
        pdfdocuments = []
        temporary_files = []

        # In most case, the report is created for a single report and an attachment is created (business report).
        # To avoid reading the resulting report two times (one to return the content to the user and one during
        # the post process). Then, in this specific case, the content is kept in memory to avoid a second reading.
        content_read = None

        for wkhtmltopdf_obj in wkhtmltopdf_objs:
            local_command_args = []
            pdfreport_fd, pdfreport_path = tempfile.mkstemp(suffix='.pdf', prefix='report.tmp.')
            temporary_files.append(pdfreport_path)

            # Directly load the document if we already have it
            if wkhtmltopdf_obj.attachment_id:
                with closing(os.fdopen(pdfreport_fd, 'w')) as pdfreport:
                    pdfreport.write(base64.decodestring(wkhtmltopdf_obj.attachment_id.datas))
                pdfdocuments.append(pdfreport_path)
                continue
            else:
                os.close(pdfreport_fd)

            # Wkhtmltopdf handles header/footer as separate pages. Create them if necessary.
            if wkhtmltopdf_obj.header:
                head_file_fd, head_file_path = tempfile.mkstemp(suffix='.html', prefix='report.header.tmp.')
                temporary_files.append(head_file_path)
                with closing(os.fdopen(head_file_fd, 'w')) as head_file:
                    head_file.write(wkhtmltopdf_obj.header)
                local_command_args.extend(['--header-html', head_file_path])
            if wkhtmltopdf_obj.footer:
                foot_file_fd, foot_file_path = tempfile.mkstemp(suffix='.html', prefix='report.footer.tmp.')
                temporary_files.append(foot_file_path)
                with closing(os.fdopen(foot_file_fd, 'w')) as foot_file:
                    foot_file.write(wkhtmltopdf_obj.footer)
                local_command_args.extend(['--footer-html', foot_file_path])

            # Body stuff
            content_file_fd, content_file_path = tempfile.mkstemp(suffix='.html', prefix='report.body.tmp.')
            temporary_files.append(content_file_path)
            with closing(os.fdopen(content_file_fd, 'w')) as content_file:
                content_file.write(wkhtmltopdf_obj.content)

            try:
                wkhtmltopdf = [_get_wkhtmltopdf_bin()] + command_args + local_command_args
                wkhtmltopdf += [content_file_path] + [pdfreport_path]
                process = subprocess.Popen(wkhtmltopdf, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                out, err = process.communicate()

                if process.returncode not in [0, 1]:
                    if process.returncode == -11:
                        message = _(
                            'Wkhtmltopdf failed (error code: %s). Memory limit too low or maximum file number of subprocess reached. Message : %s')
                    else:
                        message = _('Wkhtmltopdf failed (error code: %s). Message: %s')
                    raise UserError(message % (str(process.returncode), err[-1000:]))
                pdfdocuments.append(pdfreport_path)
            except:
                raise

            # Call the postprocess method on the ir.actions.report.
            if wkhtmltopdf_obj.res_id and wkhtmltopdf_obj.attachment_name:
                with open(pdfreport_path, 'rb') as pdfreport:
                    content_read = pdfreport.read()
                self.postprocess_pdf_report(wkhtmltopdf_obj.res_id, content_read, wkhtmltopdf_obj.attachment_name)

        # Return the entire document
        if len(pdfdocuments) == 1:
            entire_report_path = pdfdocuments[0]
        else:
            entire_report_path = _merge_pdf(pdfdocuments)
            temporary_files.append(entire_report_path)
            content_read = None

        if not content_read:
            with open(entire_report_path, 'rb') as pdfdocument:
                content_read = pdfdocument.read()

        # Manual cleanup of the temporary files
        for temporary_file in temporary_files:
            try:
                os.unlink(temporary_file)
            except (OSError, IOError):
                _logger.error('Error when trying to remove file %s' % temporary_file)

        return content_read

    @api.model
    def _get_report_from_name(self, report_name):
        """Get the first record of ir.actions.report having the ``report_name`` as value for
        the field report_name.
        """
        report_obj = self.env['ir.actions.report']
        qwebtypes = ['qweb-pdf', 'qweb-html']
        conditions = [('report_type', 'in', qwebtypes), ('report_name', '=', report_name)]
        context = self.env['res.users'].context_get()
        return report_obj.with_context(context).search(conditions, limit=1)

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
            raise ValueError("Cannot convert into barcode.")

    @api.model
    def render_template(self, template, values=None):
        """Allow to render a QWeb template python-side. This function returns the 'ir.ui.view'
        render but embellish it with some variables/methods used in reports.
        :param values: additionnal methods/variables used in the rendering
        :returns: html representation of the template
        """
        if values is None:
            values = {}

        context = dict(self.env.context, inherit_branding=True)  # Tell QWeb to brand the generated html

        # Browse the user instead of using the sudo self.env.user
        user = self.env['res.users'].browse(self.env.uid)
        website = None
        if request and hasattr(request, 'website'):
            if request.website is not None:
                website = request.website
                context = dict(context, translatable=context.get('lang') != request.website.default_lang_code)

        view_obj = self.env['ir.ui.view'].with_context(context)
        values.update(
            time=time,
            context_timestamp=lambda t: fields.Datetime.context_timestamp(self.with_context(tz=user.tz), t),
            editable=True,
            user=user,
            res_company=user.company_id,
            website=website,
            web_base_url=self.env['ir.config_parameter'].sudo().get_param('web.base.url', default='')
        )
        return view_obj.render_template(template, values)

    @api.model
    def render_qweb_pdf(self, res_ids, html=None, data=None):
        # In case of test environment without enough workers to perform calls to wkhtmltopdf,
        # fallback to render_html.
        if tools.config['test_enable'] and not tools.config['test_report_directory']:
            return self.render_qweb_html(res_ids, data=data)

        if self.get_wkhtmltopdf_state() == 'install':
            # wkhtmltopdf is not installed
            # the call should be catched before (cf /report/check_wkhtmltopdf) but
            # if get_pdf is called manually (email template), the check could be
            # bypassed
            raise UserError(_("Unable to find Wkhtmltopdf on this system. The PDF can not be created."))

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

        if html is None:
            html = self.with_context(context).render_qweb_html(res_ids, data=data)[0]

        # The test cursor prevents the use of another environnment while the current
        # transaction is not finished, leading to a deadlock when the report requests
        # an asset bundle during the execution of test scenarios. In this case, return
        # the html version.
        if isinstance(self.env.cr, TestCursor):
            return html

        html = html.decode('utf-8')  # Ensure the current document is utf-8 encoded.

        # Get the paperformat associated to the report, otherwise fallback on the company one.
        if not self.paperformat_id:
            user = self.env['res.users'].browse(self.env.uid)  # Rebrowse to avoid sudo user from self.env.user
            paperformat = user.company_id.paperformat_id
        else:
            paperformat = self.paperformat_id

        html_data = self.with_context(context)._extract_wkhtmltopdf_data_from_html(res_ids, html)
        wkhtmltopdf_objs = html_data.get('wkhtmltopdf_objs', [])
        specific_paperformat_args = html_data.get('specific_paperformat_args', None)

        return self._run_wkhtmltopdf(
            wkhtmltopdf_objs,
            context.get('landscape'),
            paperformat,
            specific_paperformat_args=specific_paperformat_args,
            set_viewport_size=context.get('set_viewport_size'),
        ), 'pdf'

    @api.model
    def render_qweb_html(self, docids, data=None):
        """This method generates and returns html version of a report.
        """
        # If the report is using a custom model to render its html, we must use it.
        # Otherwise, fallback on the generic html rendering.
        report_model_name = 'report.%s' % self.report_name
        report_model = self.env.get(report_model_name)

        if report_model is not None:
            data = report_model.get_report_values(docids, data=data)
        else:
            docs = self.env[self.model].browse(docids)
            data = {
                'doc_ids': docids,
                'doc_model': self.model,
                'docs': docs,
            }
        return self.render_template(self.report_name, data), 'html'

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
        if (self.env.uid == SUPERUSER_ID) and ((not self.env.user.company_id.external_report_layout) or (not self.env.user.company_id.logo)) and config:
            template = self.env.ref('base.view_company_report_form')
            return {
                'name': _('Choose Your Document Layout'),
                'type': 'ir.actions.act_window',
                'context': {'default_report_name': self.report_name},
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
