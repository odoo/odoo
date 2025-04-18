# Part of Odoo. See LICENSE file for full copyright and licensing details.
import io
import json
import logging
import typing
from ast import literal_eval
from collections import OrderedDict
from collections.abc import Iterable

import lxml.html
from PIL import Image, ImageFile
from lxml import etree
from markupsafe import Markup
from reportlab.graphics.barcode import createBarcodeDrawing
from reportlab.pdfbase.pdfmetrics import getFont, TypeFace

from odoo import api, fields, models, modules, tools, _
from odoo.exceptions import UserError, AccessError, RedirectWarning
from odoo.fields import Domain
from odoo.service import security
from odoo.tools import check_barcode_encoding, is_html_empty
from odoo.tools.misc import find_in_path
from odoo.tools.pdf import PdfFileReader, PdfFileWriter, PdfReadError
from odoo.tools.safe_eval import safe_eval, time

# Allow truncated images
ImageFile.LOAD_TRUNCATED_IMAGES = True

_logger = logging.getLogger(__name__)

# A lock occurs when the user wants to print a report having multiple barcode while the server is
# started in threaded-mode. The reason is that reportlab has to build a cache of the T1 fonts
# before rendering a barcode (done in a C extension) and this part is not thread safe. We attempt
# here to init the T1 fonts cache at the start-up of Odoo so that rendering of barcode in multiple
# thread does not lock the server.
_DEFAULT_BARCODE_FONT = 'Courier'
try:
    available = TypeFace(_DEFAULT_BARCODE_FONT).findT1File()
    if not available:
        substitution_font = 'NimbusMonoPS-Regular'
        fnt = getFont(substitution_font)
        if fnt:
            _DEFAULT_BARCODE_FONT = substitution_font
            fnt.ascent = 629
            fnt.descent = -157
    createBarcodeDrawing('Code128', value='foo', format='png', width=100, height=100, humanReadable=1, fontName=_DEFAULT_BARCODE_FONT).asString('png')
except Exception:
    pass


class IrActionsReport(models.Model):
    _name = 'ir.actions.report'
    _description = 'Report Action'
    _inherit = ['ir.actions.actions']
    _table = 'ir_act_report_xml'
    _order = 'name, id'
    _allow_sudo_commands = False

    type = fields.Char(default='ir.actions.report')
    binding_type = fields.Selection(default='report')
    model = fields.Char(required=True, string='Model Name')
    model_id = fields.Many2one('ir.model', string='Model', compute='_compute_model_id', search='_search_model_id')

    report_type = fields.Selection([
        ('qweb-html', 'HTML'),
        ('qweb-pdf', 'PDF'),
        ('qweb-text', 'Text'),
    ], required=True, default='qweb-html',
    help='The type of the report that will be rendered, each one having its own'
        ' rendering method. HTML means the report will be opened directly in your'
        ' browser PDF means the report will be rendered using Wkhtmltopdf and'
        ' downloaded by the user.')
    report_name = fields.Char(string='Template Name', required=True)
    report_file = fields.Char(string='Report File', required=False, readonly=False, store=True,
                              help="The path to the main report file (depending on Report Type) or empty if the content is in another field")
    group_ids = fields.Many2many('res.groups', 'res_groups_report_rel', 'uid', 'gid', string='Groups')
    multi = fields.Boolean(string='On Multiple Doc.', help="If set to true, the action will not be displayed on the right toolbar of a form view.")

    paperformat_id = fields.Many2one('report.paperformat', 'Paper Format', index='btree_not_null')
    print_report_name = fields.Char('Printed Report Name', translate=True,
                                    help="This is the filename of the report going to download. Keep empty to not change the report filename. You can use a python expression with the 'object' and 'time' variables.")
    attachment_use = fields.Boolean(string='Reload from Attachment',
                                    help='If enabled, then the second time the user prints with same attachment name, it returns the previous report.')
    attachment = fields.Char(string='Save as Attachment Prefix',
                             help='This is the filename of the attachment used to store the printing result. Keep empty to not save the printed reports. You can use a python expression with the object and time variables.')
    domain = fields.Char(string='Filter domain', help='If set, the action will only appear on records that matches the domain.')

    @api.depends('model')
    def _compute_model_id(self):
        for action in self:
            action.model_id = self.env['ir.model']._get(action.model).id

    def _search_model_id(self, operator, value):
        if Domain.is_negative_operator(operator):
            return NotImplemented
        models = self.env['ir.model']
        if isinstance(value, str):
            models = models.search(Domain('display_name', operator, value))
        elif isinstance(value, Domain):
            models = models.search(value)
        elif operator == 'any' or isinstance(value, int):
            models = models.search(Domain('id', operator, value))
        elif operator == 'in':
            models = models.search(Domain.OR(
                Domain('id' if isinstance(v, int) else 'display_name', operator, v)
                for v in value
                if v
            ))
        return Domain('model', 'in', models.mapped('model'))

    def _get_readable_fields(self):
        return super()._get_readable_fields() | {
            "report_name", "report_type", "target",
            # these two are not real fields of ir.actions.report but are
            # expected in the route /report/<converter>/<reportname> and must
            # not be removed by clean_action
            "context", "data",
            # and this one is used by the frontend later on.
            "close_on_report_download",
            "domain",
        }

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

    def create_action(self):
        """ Create a contextual action for each report. """
        for report in self:
            model = self.env['ir.model']._get(report.model)
            report.write({'binding_model_id': model.id, 'binding_type': 'report'})
        return True

    def unlink_action(self):
        """ Remove the contextual actions created for the reports. """
        self.check_access('write')
        self.filtered('binding_model_id').write({'binding_model_id': False})
        return True

    #--------------------------------------------------------------------------
    # Main report methods
    #--------------------------------------------------------------------------

    def retrieve_attachment(self, record):
        '''Retrieve an attachment for a specific record.

        :param record: The record owning of the attachment.
        :return: A recordset of length <=1 or None
        '''
        attachment_name = safe_eval(self.attachment, {'object': record, 'time': time}) if self.attachment else ''
        if not attachment_name:
            return None
        return self.env['ir.attachment'].search([
                ('name', '=', attachment_name),
                ('res_model', '=', self.model),
                ('res_id', '=', record.id)
        ], limit=1)

    @api.model
    def get_pdf_engine_state(self, engine_name=None) -> typing.Literal['ok', 'upgrade', 'workers', 'broken', 'install']:
        """
        Returns the requested engine status.
        The state of the pdf engine: install, ok, upgrade, workers or broken.
        * ok: A binary was found with a recent version.
        * upgrade: The binary is an older version.
        * workers: Not enough workers found to perform the pdf rendering process (< 2 workers).
        * broken: A binary was found but not responding.
        * install: Starting state.
        :return: state
        """
        return 'install'

    def get_paperformat(self):
        return self.paperformat_id or self.env.company.paperformat_id

    def get_paperformat_by_xmlid(self, xml_id):
        return self.env.ref(xml_id).get_paperformat() if xml_id else self.env.company.paperformat_id

    def _get_layout(self):
        return self.env.ref('web.minimal_layout', raise_if_not_found=False)

    def _get_report_url(self, layout=None):
        report_url = self.env['ir.config_parameter'].sudo().get_param('report.url')
        return report_url or (layout or self._get_layout() or self).get_base_url()

    def _prepare_html(self, html, report_model=False):
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

        # Return empty dictionary if 'web.minimal_layout' not found.
        layout = self._get_layout()
        if not layout:
            return {}
        base_url = self._get_report_url(layout=layout)

        root = lxml.html.fromstring(html, parser=lxml.html.HTMLParser(encoding='utf-8'))
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
            # set context language to body language
            IrQweb = self.env['ir.qweb']
            if node.get('data-oe-lang'):
                IrQweb = IrQweb.with_context(lang=node.get('data-oe-lang'))
            body = IrQweb._render(layout.id, {
                    'subst': False,
                    'body': Markup(lxml.html.tostring(node, encoding='unicode')),
                    'base_url': base_url,
                    'report_xml_id': self.xml_id,
                    'debug': self.env.context.get("debug"),
                }, raise_if_not_found=False)
            bodies.append(body)
            if node.get('data-oe-model') == report_model:
                res_ids.append(int(node.get('data-oe-id', 0)))
            else:
                res_ids.append(None)

        if not bodies:
            body = ''.join(lxml.html.tostring(c, encoding='unicode') for c in body_parent.getchildren())
            bodies.append(body)

        # Get paperformat arguments set in the root html tag. They are prioritized over
        # paperformat-record arguments.
        specific_paperformat_args = {}
        for attribute in root.items():
            if attribute[0].startswith('data-report-'):
                specific_paperformat_args[attribute[0]] = attribute[1]

        header = self.env['ir.qweb']._render(layout.id, {
            'subst': True,
            'body': Markup(lxml.html.tostring(header_node, encoding='unicode')),
            'base_url': base_url,
            'report_xml_id': self.xml_id,
            'debug': self.env.context.get("debug"),
        })
        footer = self.env['ir.qweb']._render(layout.id, {
            'subst': True,
            'body': Markup(lxml.html.tostring(footer_node, encoding='unicode')),
            'base_url': base_url,
            'report_xml_id': self.xml_id,
            'debug': self.env.context.get("debug"),
        })

        return bodies, res_ids, header, footer, specific_paperformat_args

    @api.model
    def _get_report_from_name(self, report_name):
        """Get the first record of ir.actions.report having the ``report_name`` as value for
        the field report_name.
        """
        report_obj = self.env['ir.actions.report']
        conditions = [('report_name', '=', report_name)]
        context = self.env['res.users'].context_get()
        return report_obj.with_context(context).sudo().search(conditions, limit=1)

    @api.model
    def _get_report(self, report_ref):
        """Get the report (with sudo) from a reference
        report_ref: can be one of
            - ir.actions.report id
            - ir.actions.report record
            - ir.model.data reference to ir.actions.report
            - ir.actions.report report_name
        """
        ReportSudo = self.env['ir.actions.report'].sudo()
        if isinstance(report_ref, int):
            return ReportSudo.browse(report_ref)
        if isinstance(report_ref, models.Model):
            if report_ref._name != self._name:
                raise ValueError("Expected report of type %s, got %s" % (self._name, report_ref._name))
            return report_ref.sudo()
        report = ReportSudo.search([('report_name', '=', report_ref)], limit=1)
        if report:
            return report
        report = self.env.ref(report_ref)
        if report:
            if report._name != "ir.actions.report":
                raise ValueError("Fetching report %r: type %s, expected ir.actions.report" % (report_ref, report._name))
            return report.sudo()
        raise ValueError("Fetching report %r: report not found" % report_ref)

    @api.model
    def barcode(self, barcode_type, value, **kwargs):
        defaults = {
            'width': (600, int),
            'height': (100, int),
            'humanreadable': (False, lambda x: bool(int(x))),
            'quiet': (True, lambda x: bool(int(x))),
            'mask': (None, lambda x: x),
            'barBorder': (4, int),
            # The QR code can have different layouts depending on the Error Correction Level
            # See: https://en.wikipedia.org/wiki/QR_code#Error_correction
            # Level 'L' – up to 7% damage   (default)
            # Level 'M' – up to 15% damage  (i.e. required by l10n_ch QR bill)
            # Level 'Q' – up to 25% damage
            # Level 'H' – up to 30% damage
            'barLevel': ('L', lambda x: x in ('L', 'M', 'Q', 'H') and x or 'L'),
        }
        kwargs = {k: validator(kwargs.get(k, v)) for k, (v, validator) in defaults.items()}
        kwargs['humanReadable'] = kwargs.pop('humanreadable')
        if kwargs['humanReadable']:
            kwargs['fontName'] = _DEFAULT_BARCODE_FONT

        if barcode_type == 'UPCA' and len(value) in (11, 12, 13):
            barcode_type = 'EAN13'
            if len(value) in (11, 12):
                value = '0%s' % value
        elif barcode_type == 'auto':
            symbology_guess = {8: 'EAN8', 13: 'EAN13'}
            barcode_type = symbology_guess.get(len(value), 'Code128')
        elif barcode_type == 'QR':
            # for `QR` type, `quiet` is not supported. And is simply ignored.
            # But we can use `barBorder` to get a similar behaviour.
            if kwargs['quiet']:
                kwargs['barBorder'] = 0

        if barcode_type in ('EAN8', 'EAN13') and not check_barcode_encoding(value, barcode_type):
            # If the barcode does not respect the encoding specifications, convert its type into Code128.
            # Otherwise, the report-lab method may return a barcode different from its value. For instance,
            # if the barcode type is EAN-8 and the value 11111111, the report-lab method will take the first
            # seven digits and will compute the check digit, which gives: 11111115 -> the barcode does not
            # match the expected value.
            barcode_type = 'Code128'

        try:
            barcode = createBarcodeDrawing(barcode_type, value=value, format='png', **kwargs)

            # If a mask is asked and it is available, call its function to
            # post-process the generated QR-code image
            if kwargs['mask']:
                available_masks = self.get_available_barcode_masks()
                mask_to_apply = available_masks.get(kwargs['mask'])
                if mask_to_apply:
                    mask_to_apply(kwargs['width'], kwargs['height'], barcode)

            return barcode.asString('png')
        except (ValueError, AttributeError):
            if barcode_type == 'Code128':
                raise ValueError("Cannot convert into barcode.")
            elif barcode_type == 'QR':
                raise ValueError("Cannot convert into QR code.")
            else:
                return self.barcode('Code128', value, **kwargs)

    @api.model
    def get_available_barcode_masks(self):
        """ Hook for extension.
        This function returns the available QR-code masks, in the form of a
        list of (code, mask_function) elements, where code is a string identifying
        the mask uniquely, and mask_function is a function returning a reportlab
        Drawing object with the result of the mask, and taking as parameters:
            - width of the QR-code, in pixels
            - height of the QR-code, in pixels
            - reportlab Drawing object containing the barcode to apply the mask on
        """
        return {}

    def _render_template(self, template, values=None):
        """Allow to render a QWeb template python-side. This function returns the 'ir.ui.view'
        render but embellish it with some variables/methods used in reports.
        :param values: additional methods/variables used in the rendering
        :returns: html representation of the template
        :rtype: bytes
        """
        if values is None:
            values = {}

        # Browse the user instead of using the sudo self.env.user
        user = self.env['res.users'].browse(self.env.uid)
        view_obj = self.env['ir.ui.view'].with_context(inherit_branding=False)
        values.update(
            time=time,
            context_timestamp=lambda t: fields.Datetime.context_timestamp(self.with_context(tz=user.tz), t),
            user=user,
            res_company=self.env.company,
            web_base_url=self.env['ir.config_parameter'].sudo().get_param('web.base.url', default=''),
        )
        return view_obj._render_template(template, values).encode()

    def _handle_merge_pdfs_error(self, error=None, error_stream=None):
        raise UserError(_("Odoo is unable to merge the generated PDFs."))

    @api.model
    def _merge_pdfs(self, streams, handle_error=_handle_merge_pdfs_error):
        writer = PdfFileWriter()
        for stream in streams:
            try:
                reader = PdfFileReader(stream)
                writer.appendPagesFromReader(reader)
            except (PdfReadError, TypeError, NotImplementedError, ValueError) as e:
                handle_error(error=e, error_stream=stream)
        result_stream = io.BytesIO()
        streams.append(result_stream)
        writer.write(result_stream)
        return result_stream

    def _render_qweb_pdf_prepare_streams(self, report_ref, data, res_ids=None):
        if not data:
            data = {}
        data.setdefault('report_type', 'pdf')

        # access the report details with sudo() but evaluation context as current user
        report_sudo = self._get_report(report_ref)
        has_duplicated_ids = res_ids and len(res_ids) != len(set(res_ids))

        collected_streams = OrderedDict()

        # Fetch the existing attachments from the database for later use.
        # Reload the stream from the attachment in case of 'attachment_use'.
        if res_ids:
            records = self.env[report_sudo.model].browse(res_ids)
            for record in records:
                res_id = record.id
                if res_id in collected_streams:
                    continue

                stream = None
                attachment = None
                if not has_duplicated_ids and report_sudo.attachment and not self._context.get("report_pdf_no_attachment"):
                    attachment = report_sudo.retrieve_attachment(record)

                    # Extract the stream from the attachment.
                    if attachment and report_sudo.attachment_use:
                        stream = io.BytesIO(attachment.raw)

                        # Ensure the stream can be saved in Image.
                        if attachment.mimetype.startswith('image'):
                            img = Image.open(stream)
                            new_stream = io.BytesIO()
                            img.convert("RGB").save(new_stream, format="pdf")
                            stream.close()
                            stream = new_stream

                collected_streams[res_id] = {
                    'stream': stream,
                    'attachment': attachment,
                }

        # Call 'wkhtmltopdf' to generate the missing streams.
        res_ids_wo_stream = [res_id for res_id, stream_data in collected_streams.items() if not stream_data['stream']]
        all_res_ids_wo_stream = res_ids if has_duplicated_ids else res_ids_wo_stream
        if self.env.company.report_rendering_engine == 'html':
            additional_context = {'debug': False}
            data.setdefault("debug", False)
            return self.with_context(**additional_context)\
                ._render_qweb_html(report_ref, all_res_ids_wo_stream, data=data)[0]
        is_pdf_engine_required = not res_ids or res_ids_wo_stream
        if is_pdf_engine_required:
            engine_name = report_sudo.report_type.rpartition('-')[2]
            if engine_name == 'pdf':
                engine_name = self.env.company.report_rendering_engine
            engine_status = self.get_pdf_engine_state(engine_name)
            if engine_status == 'install':
                # pdf engine is not installed
                # the call should be catched before (cf /report/get_pdf_engine_state) but
                # if get_pdf is called manually (email template), the check could be
                # bypassed
                raise UserError(_("Unable to find the pdf engine on this system. The PDF can not be created."))
            elif engine_status == 'workers':
                # the pdf engine is installed but not enough workers are available
                raise UserError(_("Not enough workers to generate the PDF. Please try another engine or upgrade your setup."))
            # Disable the debug mode in the PDF rendering in order to not split the assets bundle
            # into separated files to load. This is done because of an issue in wkhtmltopdf
            # failing to load the CSS/Javascript resources in time.
            # Without this, the header/footer of the reports randomly disappear
            # because the resources files are not loaded in time.
            # https://github.com/wkhtmltopdf/wkhtmltopdf/issues/2083
            additional_context = {'debug': False}
            data.setdefault("debug", False)

            html = self.with_context(**additional_context)._render_qweb_html(report_ref, all_res_ids_wo_stream, data=data)[0]
            pdf_content, html_ids = self._run_pdf_engine(engine_name, html, report_ref=report_ref, landscape=self._context.get('landscape'))
            if not has_duplicated_ids and report_sudo.attachment and set(res_ids_wo_stream) != set(html_ids):
                raise UserError(_(
                    "Report template “%s” has an issue, please contact your administrator. \n\n"
                    "Cannot separate file to save as attachment because the report's template does not contain the"
                    " attributes 'data-oe-model' and 'data-oe-id' as part of the div with 'article' classname.",
                    report_sudo.name,
                ))
            pdf_content_stream = io.BytesIO(pdf_content)

            # Printing a PDF report without any records. The content could be returned directly.
            if has_duplicated_ids or not res_ids:
                return {
                    False: {
                        'stream': pdf_content_stream,
                        'attachment': None,
                    }
                }

            # Split the pdf for each record using the PDF outlines.

            # Only one record: append the whole PDF.
            if len(res_ids_wo_stream) == 1:
                collected_streams[res_ids_wo_stream[0]]['stream'] = pdf_content_stream
                return collected_streams

            # In case of multiple docs, we need to split the pdf according the records.
            # In the simplest case of 1 res_id == 1 page, we use the PDFReader to print the
            # pages one by one.
            html_ids_wo_none = [x for x in html_ids if x]
            reader = PdfFileReader(pdf_content_stream)
            if reader.numPages == len(res_ids_wo_stream):
                for i in range(reader.numPages):
                    attachment_writer = PdfFileWriter()
                    attachment_writer.addPage(reader.getPage(i))
                    stream = io.BytesIO()
                    attachment_writer.write(stream)
                    collected_streams[res_ids_wo_stream[i]]['stream'] = stream
                return collected_streams

            # In cases where the number of res_ids != the number of pages,
            # we split the pdf based on top outlines computed by wkhtmltopdf.
            # An outline is a <h?> html tag found on the document. To retrieve this table,
            # we look on the pdf structure using pypdf to compute the outlines_pages from
            # the top level heading in /Outlines.
            if len(res_ids_wo_stream) > 1 and set(res_ids_wo_stream) == set(html_ids_wo_none):
                root = reader.trailer['/Root']
                has_valid_outlines = '/Outlines' in root and '/First' in root['/Outlines']
                if not has_valid_outlines:
                    return {False: {
                        'report_action': self,
                        'stream': pdf_content_stream,
                        'attachment': None,
                    }}

                outlines_pages = []
                node = root['/Outlines']['/First']
                while True:
                    outlines_pages.append(root['/Dests'][node['/Dest']][0])
                    if '/Next' not in node:
                        break
                    node = node['/Next']
                outlines_pages = sorted(set(outlines_pages))

                # The number of outlines must be equal to the number of records to be able to split the document.
                has_same_number_of_outlines = len(outlines_pages) == len(res_ids_wo_stream)

                # There should be a top-level heading on first page
                has_top_level_heading = outlines_pages[0] == 0

                if has_same_number_of_outlines and has_top_level_heading:
                    # Split the PDF according to outlines.
                    for i, num in enumerate(outlines_pages):
                        to = outlines_pages[i + 1] if i + 1 < len(outlines_pages) else reader.numPages
                        attachment_writer = PdfFileWriter()
                        for j in range(num, to):
                            attachment_writer.addPage(reader.getPage(j))
                        stream = io.BytesIO()
                        attachment_writer.write(stream)
                        collected_streams[res_ids_wo_stream[i]]['stream'] = stream

                    return collected_streams

            collected_streams[False] = {'stream': pdf_content_stream, 'attachment': None}

        return collected_streams

    def _prepare_pdf_report_attachment_vals_list(self, report, streams):
        """Hook to prepare attachment values needed for attachments creation
        during the pdf report generation.

        :param report: The report (with sudo) from a reference report_ref.
        :param streams: Dict of streams for each report containing the pdf content and existing attachments.
        :return: attachment values list needed for attachments creation.
        """
        attachment_vals_list = []
        for res_id, stream_data in streams.items():
            # An attachment already exists.
            if stream_data['attachment']:
                continue

            # if res_id is false
            # we are unable to fetch the record, it won't be saved as we can't split the documents unambiguously
            if not res_id or not stream_data['stream']:
                _logger.warning(
                    "These documents were not saved as an attachment because the template of %s doesn't "
                    "have any headers seperating different instances of it. If you want it saved,"
                    "please print the documents separately", report.report_name)
                continue
            record = self.env[report.model].browse(res_id)
            attachment_name = safe_eval(report.attachment, {'object': record, 'time': time})

            # Unable to compute a name for the attachment.
            if not attachment_name:
                continue

            attachment_vals_list.append({
                'name': attachment_name,
                'raw': stream_data['stream'].getvalue(),
                'res_model': report.model,
                'res_id': record.id,
                'type': 'binary',
            })
        return attachment_vals_list

    def _pre_render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        if not data:
            data = {}
        if isinstance(res_ids, int):
            res_ids = [res_ids]
        data.setdefault('report_type', 'pdf')
        # In case of test environment without enough workers to perform calls to wkhtmltopdf,
        # fallback to render_html.
        if (modules.module.current_test or tools.config['test_enable']) and not self.env.context.get('force_report_rendering'):
            return self._render_qweb_html(report_ref, res_ids, data=data)

        self = self.with_context(webp_as_jpg=True)
        return self._render_qweb_pdf_prepare_streams(report_ref, data, res_ids=res_ids), 'pdf'

    def _render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        if not data:
            data = {}
        if isinstance(res_ids, int):
            res_ids = [res_ids]
        data.setdefault('report_type', 'pdf')

        collected_streams, report_type = self._pre_render_qweb_pdf(report_ref, res_ids=res_ids, data=data)
        if report_type != 'pdf':
            return collected_streams, report_type

        has_duplicated_ids = res_ids and len(res_ids) != len(set(res_ids))

        # access the report details with sudo() but keep evaluation context as current user
        report_sudo = self._get_report(report_ref)

        # Generate the ir.attachment if needed.
        if not has_duplicated_ids and report_sudo.attachment and not self._context.get("report_pdf_no_attachment"):
            attachment_vals_list = self._prepare_pdf_report_attachment_vals_list(report_sudo, collected_streams)
            if attachment_vals_list:
                attachment_names = ', '.join(x['name'] for x in attachment_vals_list)
                try:
                    self.env['ir.attachment'].create(attachment_vals_list)
                except AccessError:
                    _logger.info("Cannot save PDF report %r attachments for user %r", attachment_names, self.env.user.display_name)
                else:
                    _logger.info("The PDF documents %r are now saved in the database", attachment_names)

        def custom_handle_merge_pdfs_error(error, error_stream):
            error_record_ids.append(stream_to_ids[error_stream])

        stream_to_ids = {v['stream']: k for k, v in collected_streams.items() if v['stream']}
        # Merge all streams together for a single record.
        streams_to_merge = list(stream_to_ids.keys())
        error_record_ids = []

        if len(streams_to_merge) == 1:
            pdf_content = streams_to_merge[0].getvalue()
        else:
            with self._merge_pdfs(streams_to_merge, custom_handle_merge_pdfs_error) as pdf_merged_stream:
                pdf_content = pdf_merged_stream.getvalue()

        if error_record_ids:
            action = {
                'type': 'ir.actions.act_window',
                'name': _('Problematic record(s)'),
                'res_model': report_sudo.model,
                'domain': [('id', 'in', error_record_ids)],
                'views': [(False, 'list'), (False, 'form')],
            }
            num_errors = len(error_record_ids)
            if num_errors == 1:
                action.update({
                    'views': [(False, 'form')],
                    'res_id': error_record_ids[0],
                })
            raise RedirectWarning(
                message=_('Odoo is unable to merge the generated PDFs because of %(num_errors)s corrupted file(s)', num_errors=num_errors),
                action=action,
                button_text=_('View Problematic Record(s)'),
            )

        for stream in streams_to_merge:
            stream.close()

        if res_ids:
            _logger.info("The PDF report has been generated for model: %s, records %s.", report_sudo.model, str(res_ids))

        return pdf_content, 'pdf'

    @api.model
    def _render_qweb_text(self, report_ref, docids, data=None):
        if not data:
            data = {}
        data.setdefault('report_type', 'text')
        report = self._get_report(report_ref)
        data = self._get_rendering_context(report, docids, data)
        return self._render_template(report.report_name, data), 'text'

    @api.model
    def _render_qweb_html(self, report_ref, docids, data=None):
        if not data:
            data = {}
        data.setdefault('report_type', 'html')
        report = self._get_report(report_ref)
        data = self._get_rendering_context(report, docids, data)
        return self._render_template(report.report_name, data), 'html'

    def _get_rendering_context_model(self, report):
        report_model_name = 'report.%s' % report.report_name
        return self.env.get(report_model_name)

    def _get_rendering_context(self, report, docids, data):
        # If the report is using a custom model to render its html, we must use it.
        # Otherwise, fallback on the generic html rendering.
        report_model = self._get_rendering_context_model(report)

        data = data and dict(data) or {}

        if report_model is not None:
            data.update(report_model._get_report_values(docids, data=data))
        else:
            docs = self.env[report.model].browse(docids)
            data.update({
                'doc_ids': docids,
                'doc_model': report.model,
                'docs': docs,
            })
        data['is_html_empty'] = is_html_empty
        return data

    def _run_pdf_engine(
        self, engine_name: str, html: str, report_ref: typing.Union[str, bool] = False,
        landscape: bool = False, **kwargs) -> tuple[bytes, list[int]]:
        """This function run associated pdf engine if exists with the given
        html.

        :param engine_name: The name of the pdf engine to use.
        :param html: The html to convert to pdf.
        :param report_ref: The report reference (opt.).
        :param landscape: If the pdf should be in landscape mode (opt.).
        :param kwargs: Additional arguments to pass to the pdf engine. (e.g. page size, margins, etc.)
        :return: a tuple of (pdf, html_ids) where pdf is the generated pdf content and html ids to separate the
            pdf content.
        """
        pdf_rendering_method = getattr(self, engine_name, None)
        if callable(pdf_rendering_method):
            return pdf_rendering_method(html, report_ref=report_ref, landscape=landscape, **kwargs)
        raise NotImplementedError(f"Unknown PDF engine: {engine_name}")

    @api.model
    def _render(self, report_ref, res_ids, data=None):
        report = self._get_report(report_ref)
        report_type = report.report_type.lower().replace('-', '_')
        render_func = getattr(self, '_render_' + report_type, None)
        if not render_func:
            return None
        return render_func(report_ref, res_ids, data=data)

    def report_action(self, docids, data=None, config=True):
        """Return an action of type ir.actions.report.

        :param docids: id/ids/browse record of the records to print (if not used, pass an empty list)
        :param data:
        :param bool config:
        :rtype: bytes
        """
        context = self.env.context
        if docids:
            if isinstance(docids, models.Model):
                active_ids = docids.ids
            elif isinstance(docids, int):
                active_ids = [docids]
            elif isinstance(docids, list):
                active_ids = docids
            context = dict(self.env.context, active_ids=active_ids)

        report_action = {
            'context': context,
            'data': data,
            'type': 'ir.actions.report',
            'report_name': self.report_name,
            'report_type': self.report_type,
            'report_file': self.report_file,
            'name': self.name,
        }

        discard_logo_check = self.env.context.get('discard_logo_check')
        if self.env.is_admin() and not self.env.company.external_report_layout_id and config and not discard_logo_check:
            return self._action_configure_external_report_layout(report_action)

        return report_action

    def _action_configure_external_report_layout(self, report_action, xml_id="web.action_base_document_layout_configurator"):
        action = self.env["ir.actions.actions"]._for_xml_id(xml_id)
        py_ctx = json.loads(action.get('context', {}))
        report_action['close_on_report_download'] = True
        py_ctx['report_action'] = report_action
        action['context'] = py_ctx
        return action

    def get_valid_action_reports(self, model, record_ids):
        """ Return the list of ids of actions for which the domain is
        satisfied by at least one record in record_ids.
        :param model: the model of the records to validate
        :param record_ids: list of ids of records to validate
        """
        records = self.env[model].browse(record_ids)
        actions_with_domain = self.filtered('domain')
        valid_action_report_ids = (self - actions_with_domain).ids  # actions without domain are always valid
        for action in actions_with_domain:
            if records.filtered_domain(literal_eval(action.domain)):
                valid_action_report_ids.append(action.id)
        return valid_action_report_ids
