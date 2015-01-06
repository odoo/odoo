# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2014-Today OpenERP SA (<http://www.openerp.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import api
from openerp import SUPERUSER_ID
from openerp.exceptions import AccessError
from openerp.osv import osv
from openerp.tools import config
from openerp.tools.misc import find_in_path
from openerp.tools.translate import _
from openerp.addons.web.http import request
from openerp.tools.safe_eval import safe_eval as eval

import re
import time
import base64
import logging
import tempfile
import lxml.html
import os
import subprocess
from contextlib import closing
from distutils.version import LooseVersion
from functools import partial
from pyPdf import PdfFileWriter, PdfFileReader


#--------------------------------------------------------------------------
# Helpers
#--------------------------------------------------------------------------
_logger = logging.getLogger(__name__)

def _get_wkhtmltopdf_bin():
    wkhtmltopdf_bin = find_in_path('wkhtmltopdf')
    if wkhtmltopdf_bin is None:
        raise IOError
    return wkhtmltopdf_bin


#--------------------------------------------------------------------------
# Check the presence of Wkhtmltopdf and return its version at Odoo start-up
#--------------------------------------------------------------------------
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
    version = re.search('([0-9.]+)', out).group(0)
    if LooseVersion(version) < LooseVersion('0.12.0'):
        _logger.info('Upgrade Wkhtmltopdf to (at least) 0.12.0')
        wkhtmltopdf_state = 'upgrade'
    else:
        wkhtmltopdf_state = 'ok'

    if config['workers'] == 1:
        _logger.info('You need to start Odoo with at least two workers to print a pdf version of the reports.')
        wkhtmltopdf_state = 'workers'


class Report(osv.Model):
    _name = "report"
    _description = "Report"

    public_user = None

    #--------------------------------------------------------------------------
    # Extension of ir_ui_view.render with arguments frequently used in reports
    #--------------------------------------------------------------------------
    def render(self, cr, uid, ids, template, values=None, context=None):
        """Allow to render a QWeb template python-side. This function returns the 'ir.ui.view'
        render but embellish it with some variables/methods used in reports.

        :param values: additionnal methods/variables used in the rendering
        :returns: html representation of the template
        """
        if values is None:
            values = {}

        if context is None:
            context = {}

        context = dict(context, inherit_branding=True)  # Tell QWeb to brand the generated html

        view_obj = self.pool['ir.ui.view']

        def translate_doc(doc_id, model, lang_field, template):
            """Helper used when a report should be translated into a specific lang.

            <t t-foreach="doc_ids" t-as="doc_id">
            <t t-raw="translate_doc(doc_id, doc_model, 'partner_id.lang', account.report_invoice_document')"/>
            </t>

            :param doc_id: id of the record to translate
            :param model: model of the record to translate
            :param lang_field': field of the record containing the lang
            :param template: name of the template to translate into the lang_field
            """
            ctx = context.copy()
            doc = self.pool[model].browse(cr, uid, doc_id, context=ctx)
            qcontext = values.copy()
            # Do not force-translate if we chose to display the report in a specific lang
            if ctx.get('translatable') is True:
                qcontext['o'] = doc
            else:
                # Reach the lang we want to translate the doc into
                ctx['lang'] = eval('doc.%s' % lang_field, {'doc': doc})
                qcontext['o'] = self.pool[model].browse(cr, uid, doc_id, context=ctx)
            return view_obj.render(cr, uid, template, qcontext, context=ctx)

        user = self.pool['res.users'].browse(cr, uid, uid)
        website = None
        if request and hasattr(request, 'website'):
            if request.website is not None:
                website = request.website
                context = dict(context, translatable=context.get('lang') != request.website.default_lang_code)
        values.update(
            time=time,
            translate_doc=translate_doc,
            editable=True,
            user=user,
            res_company=user.company_id,
            website=website,
        )
        return view_obj.render(cr, uid, template, values, context=context)

    #--------------------------------------------------------------------------
    # Main report methods
    #--------------------------------------------------------------------------
    @api.v7
    def get_html(self, cr, uid, ids, report_name, data=None, context=None):
        """This method generates and returns html version of a report.
        """
        # If the report is using a custom model to render its html, we must use it.
        # Otherwise, fallback on the generic html rendering.
        try:
            report_model_name = 'report.%s' % report_name
            particularreport_obj = self.pool[report_model_name]
            return particularreport_obj.render_html(cr, uid, ids, data=data, context=context)
        except KeyError:
            report = self._get_report_from_name(cr, uid, report_name)
            report_obj = self.pool[report.model]
            docs = report_obj.browse(cr, uid, ids, context=context)
            docargs = {
                'doc_ids': ids,
                'doc_model': report.model,
                'docs': docs,
            }
            return self.render(cr, uid, [], report.report_name, docargs, context=context)

    @api.v8
    def get_html(self, records, report_name, data=None):
        return self._model.get_html(self._cr, self._uid, records.ids, report_name,
                                    data=data, context=self._context)

    @api.v7
    def get_pdf(self, cr, uid, ids, report_name, html=None, data=None, context=None):
        """This method generates and returns pdf version of a report.
        """
        if context is None:
            context = {}

        if html is None:
            html = self.get_html(cr, uid, ids, report_name, data=data, context=context)

        html = html.decode('utf-8')  # Ensure the current document is utf-8 encoded.

        # Get the ir.actions.report.xml record we are working on.
        report = self._get_report_from_name(cr, uid, report_name)
        # Check if we have to save the report or if we have to get one from the db.
        save_in_attachment = self._check_attachment_use(cr, uid, ids, report)
        # Get the paperformat associated to the report, otherwise fallback on the company one.
        if not report.paperformat_id:
            user = self.pool['res.users'].browse(cr, uid, uid)
            paperformat = user.company_id.paperformat_id
        else:
            paperformat = report.paperformat_id

        # Preparing the minimal html pages
        css = ''  # Will contain local css
        headerhtml = []
        contenthtml = []
        footerhtml = []
        irconfig_obj = self.pool['ir.config_parameter']
        base_url = irconfig_obj.get_param(cr, SUPERUSER_ID, 'report.url') or irconfig_obj.get_param(cr, SUPERUSER_ID, 'web.base.url')

        # Minimal page renderer
        view_obj = self.pool['ir.ui.view']
        render_minimal = partial(view_obj.render, cr, uid, 'report.minimal_layout', context=context)

        # The received html report must be simplified. We convert it in a xml tree
        # in order to extract headers, bodies and footers.
        try:
            root = lxml.html.fromstring(html)
            match_klass = "//div[contains(concat(' ', normalize-space(@class), ' '), ' {} ')]"

            for node in root.xpath("//html/head/style"):
                css += node.text

            for node in root.xpath(match_klass.format('header')):
                body = lxml.html.tostring(node)
                header = render_minimal(dict(css=css, subst=True, body=body, base_url=base_url))
                headerhtml.append(header)

            for node in root.xpath(match_klass.format('footer')):
                body = lxml.html.tostring(node)
                footer = render_minimal(dict(css=css, subst=True, body=body, base_url=base_url))
                footerhtml.append(footer)

            for node in root.xpath(match_klass.format('page')):
                # Previously, we marked some reports to be saved in attachment via their ids, so we
                # must set a relation between report ids and report's content. We use the QWeb
                # branding in order to do so: searching after a node having a data-oe-model
                # attribute with the value of the current report model and read its oe-id attribute
                if ids and len(ids) == 1:
                    reportid = ids[0]
                else:
                    oemodelnode = node.find(".//*[@data-oe-model='%s']" % report.model)
                    if oemodelnode is not None:
                        reportid = oemodelnode.get('data-oe-id')
                        if reportid:
                            reportid = int(reportid)
                    else:
                        reportid = False

                # Extract the body
                body = lxml.html.tostring(node)
                reportcontent = render_minimal(dict(css=css, subst=False, body=body, base_url=base_url))

                contenthtml.append(tuple([reportid, reportcontent]))

        except lxml.etree.XMLSyntaxError:
            contenthtml = []
            contenthtml.append(html)
            save_in_attachment = {}  # Don't save this potentially malformed document

        # Get paperformat arguments set in the root html tag. They are prioritized over
        # paperformat-record arguments.
        specific_paperformat_args = {}
        for attribute in root.items():
            if attribute[0].startswith('data-report-'):
                specific_paperformat_args[attribute[0]] = attribute[1]

        # Run wkhtmltopdf process
        return self._run_wkhtmltopdf(
            cr, uid, headerhtml, footerhtml, contenthtml, context.get('landscape'),
            paperformat, specific_paperformat_args, save_in_attachment
        )

    @api.v8
    def get_pdf(self, records, report_name, html=None, data=None):
        return self._model.get_pdf(self._cr, self._uid, records.ids, report_name,
                                   html=html, data=data, context=self._context)

    @api.v7
    def get_action(self, cr, uid, ids, report_name, data=None, context=None):
        """Return an action of type ir.actions.report.xml.

        :param ids: Ids of the records to print (if not used, pass an empty list)
        :param report_name: Name of the template to generate an action for
        """
        if ids:
            if not isinstance(ids, list):
                ids = [ids]
            context = dict(context or {}, active_ids=ids)

        report_obj = self.pool['ir.actions.report.xml']
        idreport = report_obj.search(cr, uid, [('report_name', '=', report_name)], context=context)
        try:
            report = report_obj.browse(cr, uid, idreport[0], context=context)
        except IndexError:
            raise osv.except_osv(
                _('Bad Report Reference'),
                _('This report is not loaded into the database: %s.' % report_name)
            )

        return {
            'context': context,
            'data': data,
            'type': 'ir.actions.report.xml',
            'report_name': report.report_name,
            'report_type': report.report_type,
            'report_file': report.report_file,
            'context': context,
        }

    @api.v8
    def get_action(self, records, report_name, data=None):
        return self._model.get_action(self._cr, self._uid, records.ids, report_name,
                                      data=data, context=self._context)

    #--------------------------------------------------------------------------
    # Report generation helpers
    #--------------------------------------------------------------------------
    @api.v7
    def _check_attachment_use(self, cr, uid, ids, report):
        """ Check attachment_use field. If set to true and an existing pdf is already saved, load
        this one now. Else, mark save it.
        """
        save_in_attachment = {}
        save_in_attachment['model'] = report.model
        save_in_attachment['loaded_documents'] = {}

        if report.attachment:
            for record_id in ids:
                obj = self.pool[report.model].browse(cr, uid, record_id)
                filename = eval(report.attachment, {'object': obj, 'time': time})

                # If the user has checked 'Reload from Attachment'
                if report.attachment_use:
                    alreadyindb = [('datas_fname', '=', filename),
                                   ('res_model', '=', report.model),
                                   ('res_id', '=', record_id)]
                    attach_ids = self.pool['ir.attachment'].search(cr, uid, alreadyindb)
                    if attach_ids:
                        # Add the loaded pdf in the loaded_documents list
                        pdf = self.pool['ir.attachment'].browse(cr, uid, attach_ids[0]).datas
                        pdf = base64.decodestring(pdf)
                        save_in_attachment['loaded_documents'][record_id] = pdf
                        _logger.info('The PDF document %s was loaded from the database' % filename)

                        continue  # Do not save this document as we already ignore it

                # If the user has checked 'Save as Attachment Prefix'
                if filename is False:
                    # May be false if, for instance, the 'attachment' field contains a condition
                    # preventing to save the file.
                    continue
                else:
                    save_in_attachment[record_id] = filename  # Mark current document to be saved

        return save_in_attachment

    @api.v8
    def _check_attachment_use(self, records, report):
        return self._model._check_attachment_use(
            self._cr, self._uid, records.ids, report, context=self._context)

    def _check_wkhtmltopdf(self):
        return wkhtmltopdf_state

    def _run_wkhtmltopdf(self, cr, uid, headers, footers, bodies, landscape, paperformat, spec_paperformat_args=None, save_in_attachment=None):
        """Execute wkhtmltopdf as a subprocess in order to convert html given in input into a pdf
        document.

        :param header: list of string containing the headers
        :param footer: list of string containing the footers
        :param bodies: list of string containing the reports
        :param landscape: boolean to force the pdf to be rendered under a landscape format
        :param paperformat: ir.actions.report.paperformat to generate the wkhtmltopf arguments
        :param specific_paperformat_args: dict of prioritized paperformat arguments
        :param save_in_attachment: dict of reports to save/load in/from the db
        :returns: Content of the pdf as a string
        """
        command_args = []

        # Passing the cookie to wkhtmltopdf in order to resolve internal links.
        try:
            if request:
                command_args.extend(['--cookie', 'session_id', request.session.sid])
        except AttributeError:
            pass

        # Wkhtmltopdf arguments
        command_args.extend(['--quiet'])  # Less verbose error messages
        if paperformat:
            # Convert the paperformat record into arguments
            command_args.extend(self._build_wkhtmltopdf_args(paperformat, spec_paperformat_args))

        # Force the landscape orientation if necessary
        if landscape and '--orientation' in command_args:
            command_args_copy = list(command_args)
            for index, elem in enumerate(command_args_copy):
                if elem == '--orientation':
                    del command_args[index]
                    del command_args[index]
                    command_args.extend(['--orientation', 'landscape'])
        elif landscape and not '--orientation' in command_args:
            command_args.extend(['--orientation', 'landscape'])

        # Execute WKhtmltopdf
        pdfdocuments = []
        temporary_files = []

        for index, reporthtml in enumerate(bodies):
            local_command_args = []
            pdfreport_fd, pdfreport_path = tempfile.mkstemp(suffix='.pdf', prefix='report.tmp.')
            temporary_files.append(pdfreport_path)

            # Directly load the document if we already have it
            if save_in_attachment and save_in_attachment['loaded_documents'].get(reporthtml[0]):
                with closing(os.fdopen(pdfreport_fd, 'w')) as pdfreport:
                    pdfreport.write(save_in_attachment['loaded_documents'][reporthtml[0]])
                pdfdocuments.append(pdfreport_path)
                continue
            else:
                os.close(pdfreport_fd)

            # Wkhtmltopdf handles header/footer as separate pages. Create them if necessary.
            if headers:
                head_file_fd, head_file_path = tempfile.mkstemp(suffix='.html', prefix='report.header.tmp.')
                temporary_files.append(head_file_path)
                with closing(os.fdopen(head_file_fd, 'w')) as head_file:
                    head_file.write(headers[index])
                local_command_args.extend(['--header-html', head_file_path])
            if footers:
                foot_file_fd, foot_file_path = tempfile.mkstemp(suffix='.html', prefix='report.footer.tmp.')
                temporary_files.append(foot_file_path)
                with closing(os.fdopen(foot_file_fd, 'w')) as foot_file:
                    foot_file.write(footers[index])
                local_command_args.extend(['--footer-html', foot_file_path])

            # Body stuff
            content_file_fd, content_file_path = tempfile.mkstemp(suffix='.html', prefix='report.body.tmp.')
            temporary_files.append(content_file_path)
            with closing(os.fdopen(content_file_fd, 'w')) as content_file:
                content_file.write(reporthtml[1])

            try:
                wkhtmltopdf = [_get_wkhtmltopdf_bin()] + command_args + local_command_args
                wkhtmltopdf += [content_file_path] + [pdfreport_path]

                process = subprocess.Popen(wkhtmltopdf, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                out, err = process.communicate()

                if process.returncode not in [0, 1]:
                    raise osv.except_osv(_('Report (PDF)'),
                                         _('Wkhtmltopdf failed (error code: %s). '
                                           'Message: %s') % (str(process.returncode), err))

                # Save the pdf in attachment if marked
                if reporthtml[0] is not False and save_in_attachment.get(reporthtml[0]):
                    with open(pdfreport_path, 'rb') as pdfreport:
                        attachment = {
                            'name': save_in_attachment.get(reporthtml[0]),
                            'datas': base64.encodestring(pdfreport.read()),
                            'datas_fname': save_in_attachment.get(reporthtml[0]),
                            'res_model': save_in_attachment.get('model'),
                            'res_id': reporthtml[0],
                        }
                        try:
                            self.pool['ir.attachment'].create(cr, uid, attachment)
                        except AccessError:
                            _logger.warning("Cannot save PDF report %r as attachment",
                                            attachment['name'])
                        else:
                            _logger.info('The PDF document %s is now saved in the database',
                                         attachment['name'])

                pdfdocuments.append(pdfreport_path)
            except:
                raise

        # Return the entire document
        if len(pdfdocuments) == 1:
            entire_report_path = pdfdocuments[0]
        else:
            entire_report_path = self._merge_pdf(pdfdocuments)
            temporary_files.append(entire_report_path)

        with open(entire_report_path, 'rb') as pdfdocument:
            content = pdfdocument.read()

        # Manual cleanup of the temporary files
        for temporary_file in temporary_files:
            try:
                os.unlink(temporary_file)
            except (OSError, IOError):
                _logger.error('Error when trying to remove file %s' % temporary_file)

        return content

    def _get_report_from_name(self, cr, uid, report_name):
        """Get the first record of ir.actions.report.xml having the ``report_name`` as value for
        the field report_name.
        """
        report_obj = self.pool['ir.actions.report.xml']
        qwebtypes = ['qweb-pdf', 'qweb-html']
        conditions = [('report_type', 'in', qwebtypes), ('report_name', '=', report_name)]
        idreport = report_obj.search(cr, uid, conditions)[0]
        return report_obj.browse(cr, uid, idreport)

    def _build_wkhtmltopdf_args(self, paperformat, specific_paperformat_args=None):
        """Build arguments understandable by wkhtmltopdf from a report.paperformat record.

        :paperformat: report.paperformat record
        :specific_paperformat_args: a dict containing prioritized wkhtmltopdf arguments
        :returns: list of string representing the wkhtmltopdf arguments
        """
        command_args = []
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
        if paperformat.orientation:
            command_args.extend(['--orientation', str(paperformat.orientation)])
        if paperformat.header_line:
            command_args.extend(['--header-line'])

        return command_args

    def _merge_pdf(self, documents):
        """Merge PDF files into one.

        :param documents: list of path of pdf files
        :returns: path of the merged pdf
        """
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
