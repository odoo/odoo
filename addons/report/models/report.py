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

from openerp.osv import osv
from openerp.tools import config
from openerp.tools.translate import _
from openerp.addons.web.http import request
from openerp.tools.safe_eval import safe_eval as eval

import re
import time
import base64
import logging
import tempfile
import lxml.html
import cStringIO
import subprocess
from distutils.version import LooseVersion
try:
    from pyPdf import PdfFileWriter, PdfFileReader
except ImportError:
    PdfFileWriter = PdfFileReader = None


_logger = logging.getLogger(__name__)


"""Check the presence of wkhtmltopdf and return its version at OpnerERP start-up."""
wkhtmltopdf_state = 'install'
try:
    process = subprocess.Popen(
        ['wkhtmltopdf', '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
except OSError:
    _logger.info('You need wkhtmltopdf to print a pdf version of the reports.')
else:
    out, err = process.communicate()
    version = re.search('([0-9.]+)', out).group(0)
    if LooseVersion(version) < LooseVersion('0.12.0'):
        _logger.info('Upgrade wkhtmltopdf to (at least) 0.12.0')
        wkhtmltopdf_state = 'upgrade'
    else:
        wkhtmltopdf_state = 'ok'

    if config['workers'] == 1:
        _logger.info('You need to start OpenERP with at least two workers to print a pdf version of the reports.')
        wkhtmltopdf_state = 'workers'


class Report(osv.Model):
    _name = "report"
    _description = "Report"

    public_user = None

    MINIMAL_HTML_PAGE = """
<base href="{base_url}">
<!DOCTYPE html>
<html style="height: 0;">
    <head>
        <link href="/report/static/src/css/reset.min.css" rel="stylesheet"/>
        <link href="/web/static/lib/bootstrap/css/bootstrap.css" rel="stylesheet"/>
        <link href="/website/static/src/css/website.css" rel="stylesheet"/>
        <link href="/web/static/lib/fontawesome/css/font-awesome.css" rel="stylesheet"/>
        <style type='text/css'>{css}</style>
        {subst}
    </head>
    <body class="container" onload="subst()">
        {body}
    </body>
</html>"""

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
            website = request.website
        values.update(
            time=time,
            translate_doc=translate_doc,
            editable=True,  # Will active inherit_branding
            user=user,
            res_company=user.company_id,
            website=website,
            editable_no_editor=True,
        )
        return view_obj.render(cr, uid, template, values, context=context)

    #--------------------------------------------------------------------------
    # Main report methods
    #--------------------------------------------------------------------------
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
        subst = "<script src='/report/static/src/js/subst.js'></script> "
        css = ''  # Will contain local css
        headerhtml = []
        contenthtml = []
        footerhtml = []
        base_url = self.pool['ir.config_parameter'].get_param(cr, uid, 'web.base.url')

        # The received html report must be simplified. We convert it in a xml tree
        # in order to extract headers, bodies and footers.
        try:
            root = lxml.html.fromstring(html)

            for node in root.xpath("//html/head/style"):
                css += node.text

            for node in root.xpath("//div[@class='header']"):
                body = lxml.html.tostring(node)
                header = self.MINIMAL_HTML_PAGE.format(css=css, subst=subst, body=body, base_url=base_url)
                headerhtml.append(header)

            for node in root.xpath("//div[@class='footer']"):
                body = lxml.html.tostring(node)
                footer = self.MINIMAL_HTML_PAGE.format(css=css, subst=subst, body=body, base_url=base_url)
                footerhtml.append(footer)

            for node in root.xpath("//div[@class='page']"):
                # Previously, we marked some reports to be saved in attachment via their ids, so we
                # must set a relation between report ids and report's content. We use the QWeb
                # branding in order to do so: searching after a node having a data-oe-model
                # attribute with the value of the current report model and read its oe-id attribute
                oemodelnode = node.find(".//*[@data-oe-model='%s']" % report.model)
                if oemodelnode is not None:
                    reportid = oemodelnode.get('data-oe-id')
                    if reportid:
                        reportid = int(reportid)
                else:
                    reportid = False

                body = lxml.html.tostring(node)
                reportcontent = self.MINIMAL_HTML_PAGE.format(css=css, subst='', body=body, base_url=base_url)

                # FIXME: imo the best way to extract record id from html reports is by using the
                # qweb branding. As website editor is not yet splitted in a module independant from
                # website, when we print a unique report we can use the id passed in argument to
                # identify it.
                if ids and len(ids) == 1:
                    reportid = ids[0]

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
        pdf = self._generate_wkhtml_pdf(
            cr, uid, headerhtml, footerhtml, contenthtml, context.get('landscape'),
            paperformat, specific_paperformat_args, save_in_attachment
        )
        return pdf

    def get_action(self, cr, uid, ids, report_name, data=None, context=None):
        """Return an action of type ir.actions.report.xml.

        :param ids: Ids of the records to print (if not used, pass an empty list)
        :param report_name: Name of the template to generate an action for
        """
        if ids:
            if not isinstance(ids, list):
                ids = [ids]
            context['active_ids'] = ids

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

    #--------------------------------------------------------------------------
    # Report generation helpers
    #--------------------------------------------------------------------------
    def _check_attachment_use(self, cr, uid, ids, report):
        """ Check attachment_use field. If set to true and an existing pdf is already saved, load
        this one now. Else, mark save it.
        """
        save_in_attachment = {}
        if report.attachment_use is True:
            save_in_attachment['model'] = report.model
            save_in_attachment['loaded_documents'] = {}

            for record_id in ids:
                obj = self.pool[report.model].browse(cr, uid, record_id)
                filename = eval(report.attachment, {'object': obj, 'time': time})

                if filename is False:  # May be false if, for instance, the record is in draft state
                    continue
                else:
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
                    else:
                        # Mark current document to be saved
                        save_in_attachment[record_id] = filename
        return save_in_attachment

    def _check_wkhtmltopdf(self):
        return wkhtmltopdf_state

    def _generate_wkhtml_pdf(self, cr, uid, headers, footers, bodies, landscape, paperformat, spec_paperformat_args=None, save_in_attachment=None):
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
        command = ['wkhtmltopdf']
        command_args = []
        tmp_dir = tempfile.gettempdir()

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
        for index, reporthtml in enumerate(bodies):
            local_command_args = []
            pdfreport = tempfile.NamedTemporaryFile(suffix='.pdf', prefix='report.tmp.', mode='w+b')

            # Directly load the document if we already have it
            if save_in_attachment and save_in_attachment['loaded_documents'].get(reporthtml[0]):
                pdfreport.write(save_in_attachment['loaded_documents'].get(reporthtml[0]))
                pdfreport.seek(0)
                pdfdocuments.append(pdfreport)
                continue

            # Wkhtmltopdf handles header/footer as separate pages. Create them if necessary.
            if headers:
                head_file = tempfile.NamedTemporaryFile(suffix='.html', prefix='report.header.tmp.', dir=tmp_dir, mode='w+')
                head_file.write(headers[index])
                head_file.seek(0)
                local_command_args.extend(['--header-html', head_file.name])
            if footers:
                foot_file = tempfile.NamedTemporaryFile(suffix='.html', prefix='report.footer.tmp.', dir=tmp_dir, mode='w+')
                foot_file.write(footers[index])
                foot_file.seek(0)
                local_command_args.extend(['--footer-html', foot_file.name])

            # Body stuff
            content_file = tempfile.NamedTemporaryFile(suffix='.html', prefix='report.body.tmp.', dir=tmp_dir, mode='w+')
            content_file.write(reporthtml[1])
            content_file.seek(0)

            try:
                wkhtmltopdf = command + command_args + local_command_args
                wkhtmltopdf += [content_file.name] + [pdfreport.name]

                process = subprocess.Popen(wkhtmltopdf, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                out, err = process.communicate()

                if process.returncode not in [0, 1]:
                    raise osv.except_osv(_('Report (PDF)'),
                                         _('Wkhtmltopdf failed (error code: %s). '
                                           'Message: %s') % (str(process.returncode), err))

                # Save the pdf in attachment if marked
                if reporthtml[0] is not False and save_in_attachment.get(reporthtml[0]):
                    attachment = {
                        'name': save_in_attachment.get(reporthtml[0]),
                        'datas': base64.encodestring(pdfreport.read()),
                        'datas_fname': save_in_attachment.get(reporthtml[0]),
                        'res_model': save_in_attachment.get('model'),
                        'res_id': reporthtml[0],
                    }
                    self.pool['ir.attachment'].create(cr, uid, attachment)
                    _logger.info('The PDF document %s is now saved in the '
                                 'database' % attachment['name'])

                pdfreport.seek(0)
                pdfdocuments.append(pdfreport)

                if headers:
                    head_file.close()
                if footers:
                    foot_file.close()
            except:
                raise

        # Return the entire document
        if len(pdfdocuments) == 1:
            content = pdfdocuments[0].read()
            pdfdocuments[0].close()
        else:
            content = self._merge_pdf(pdfdocuments)

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
        elif paperformat.margin_top:
            command_args.extend(['--margin-top', str(paperformat.margin_top)])

        if specific_paperformat_args and specific_paperformat_args.get('data-report-dpi'):
            command_args.extend(['--dpi', str(specific_paperformat_args['data-report-dpi'])])
        elif paperformat.dpi:
            command_args.extend(['--dpi', str(paperformat.dpi)])

        if specific_paperformat_args and specific_paperformat_args.get('data-report-header-spacing'):
            command_args.extend(['--header-spacing', str(specific_paperformat_args['data-report-header-spacing'])])
        elif paperformat.header_spacing:
            command_args.extend(['--header-spacing', str(paperformat.header_spacing)])

        if paperformat.margin_left:
            command_args.extend(['--margin-left', str(paperformat.margin_left)])
        if paperformat.margin_bottom:
            command_args.extend(['--margin-bottom', str(paperformat.margin_bottom)])
        if paperformat.margin_right:
            command_args.extend(['--margin-right', str(paperformat.margin_right)])
        if paperformat.orientation:
            command_args.extend(['--orientation', str(paperformat.orientation)])
        if paperformat.header_line:
            command_args.extend(['--header-line'])

        return command_args

    def _merge_pdf(self, documents):
        """Merge PDF files into one.

        :param documents: list of pdf files
        :returns: string containing the merged pdf
        """
        writer = PdfFileWriter()
        for document in documents:
            reader = PdfFileReader(file(document.name, "rb"))
            for page in range(0, reader.getNumPages()):
                writer.addPage(reader.getPage(page))
            document.close()
        merged = cStringIO.StringIO()
        writer.write(merged)
        merged.seek(0)
        content = merged.read()
        merged.close()
        return content
