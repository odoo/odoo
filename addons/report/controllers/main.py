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

from openerp.osv.osv import except_osv
from openerp.addons.web import http
from openerp.tools.translate import _
from openerp.addons.web.http import request
import openerp.tools.config as config

import time
import base64
import logging
import tempfile
import lxml.html
import subprocess
import simplejson
try:
    import cStringIO as StringIO
except ImportError:
    import StringIO
import psutil
import signal
import os
from distutils.version import LooseVersion


from werkzeug import exceptions
from werkzeug.test import Client
from werkzeug.wrappers import BaseResponse
from werkzeug.datastructures import Headers
from reportlab.graphics.barcode import createBarcodeDrawing


_logger = logging.getLogger(__name__)
try:
    from pyPdf import PdfFileWriter, PdfFileReader
except ImportError:
    PdfFileWriter = PdfFileReader = None

class Report(http.Controller):

    @http.route(['/report/<reportname>/<docids>'], type='http', auth='user', website=True, multilang=True)
    def report_html(self, reportname, docids, **kwargs):
        """This is the generic route for QWeb reports. It is used for reports
        which do not need to preprocess the data (i.e. reports that just display
        fields of a record).

        It is given a ~fully qualified report name, for instance 'account.report_invoice'.
        Based on it, we know the module concerned and the name of the template. With the
        name of the template, we will make a search on the ir.actions.reports.xml table and
        get the record associated to finally know the model this template refers to.

        There is a way to declare the report (in module_report(s).xml) that you must respect:
            id="action_report_model"
            model="module.model"  # To know which model the report refers to
            string="Invoices"
            report_type="qweb-pdf"  # or qweb-html
            name="module.template_name"
            file="module.template_name"

        If you don't want your report listed under the print button, just add
        'menu=False'.
        """
        ids = [int(i) for i in docids.split(',')]
        ids = list(set(ids))
        report = self._get_report_from_name(reportname)
        report_obj = request.registry[report.model]
        docs = report_obj.browse(request.cr, request.uid, ids, context=request.context)

        docargs = {
            'doc_ids': ids,
            'doc_model': report.model,
            'docs': docs,
        }

        return request.registry['report'].render(request.cr, request.uid, [], report.report_name,
                                                 docargs, context=request.context)

    @http.route(['/report/pdf/<path:path>'], type='http', auth="user", website=True)
    def report_pdf(self, path=None, landscape=False, **post):
        """Route converting any reports to pdf. It will get the html-rendered report, extract
        header, page and footer in order to prepare minimal html pages that will be further passed
        to wkhtmltopdf.

        :param path: URL of the report (e.g. /report/account.report_invoice/1)
        :returns: a response with 'application/pdf' headers and the pdf as content
        """
        cr, uid, context = request.cr, request.uid, request.context

        # Get the report we are working on.
        # Pattern is /report/module.reportname(?a=1)
        reportname_in_path = path.split('/')[1].split('?')[0]
        report = self._get_report_from_name(reportname_in_path)

        # Check attachment_use field. If set to true and an existing pdf is already saved, load
        # this one now. If not, mark save it.
        save_in_attachment = {}

        if report.attachment_use is True:
            # Get the record ids we are working on.
            path_ids = [int(i) for i in path.split('/')[2].split('?')[0].split(',')]

            save_in_attachment['model'] = report.model
            save_in_attachment['loaded_documents'] = {}

            for path_id in path_ids:
                obj = request.registry[report.model].browse(cr, uid, path_id)
                filename = eval(report.attachment, {'object': obj, 'time': time})

                if filename is False:  # May be false if, for instance, the record is in draft state
                    continue
                else:
                    alreadyindb = [('datas_fname', '=', filename),
                                   ('res_model', '=', report.model),
                                   ('res_id', '=', path_id)]

                    attach_ids = request.registry['ir.attachment'].search(cr, uid, alreadyindb)
                    if attach_ids:
                        # Add the loaded pdf in the loaded_documents list
                        pdf = request.registry['ir.attachment'].browse(cr, uid, attach_ids[0]).datas
                        pdf = base64.decodestring(pdf)
                        save_in_attachment['loaded_documents'][path_id] = pdf
                        _logger.info('The PDF document %s was loaded from the database' % filename)
                    else:
                        # Mark current document to be saved
                        save_in_attachment[path_id] = filename

        # Get the paperformat associated to the report. If there is not, get the one associated to
        # the company.
        if not report.paperformat_id:
            user = request.registry['res.users'].browse(cr, uid, uid, context=context)
            paperformat = user.company_id.paperformat_id
        else:
            paperformat = report.paperformat_id

        # Get the html report.
        html = self._get_url_content('/' + path, post)[0]
        subst = self._get_url_content('/report/static/src/js/subst.js')[0]  # Used in age numbering
        css = ''  # Local css

        headerhtml = []
        contenthtml = []
        footerhtml = []
        base_url = request.registry['ir.config_parameter'].get_param(cr, uid, 'web.base.url')

        minimalhtml = """
<base href="{3}">
<!DOCTYPE html>
<html style="height: 0;">
    <head>
        <link href="/report/static/src/css/reset.min.css" rel="stylesheet"/>
        <link href="/web/static/lib/bootstrap/css/bootstrap.css" rel="stylesheet"/>
        <link href="/website/static/src/css/website.css" rel="stylesheet"/>
        <link href="/web/static/lib/fontawesome/css/font-awesome.css" rel="stylesheet"/>

        <style type='text/css'>{0}</style>

        <script type='text/javascript'>{1}</script>
    </head>
    <body class="container" onload='subst()'>
        {2}
    </body>
</html>"""

        # The retrieved html report must be simplified. We convert it into a xml tree
        # via lxml in order to extract headers, footers and content.
        try:
            root = lxml.html.fromstring(html)

            for node in root.xpath("//html/head/style"):
                css += node.text

            for node in root.xpath("//div[@class='header']"):
                body = lxml.html.tostring(node)
                header = minimalhtml.format(css, subst, body, base_url)
                headerhtml.append(header)

            for node in root.xpath("//div[@class='footer']"):
                body = lxml.html.tostring(node)
                footer = minimalhtml.format(css, subst, body, base_url)
                footerhtml.append(footer)

            for node in root.xpath("//div[@class='page']"):
                # Previously, we marked some reports to be saved in attachment via their ids, so we
                # must set a relation between report ids and report's content. We use the QWeb
                # branding in order to do so: searching after a node having a data-oe-model
                # attribute with the value of the current report model and read its oe-id attribute
                oemodelnode = node.find(".//*[@data-oe-model='" + report.model + "']")
                if oemodelnode is not None:
                    reportid = oemodelnode.get('data-oe-id', False)
                    if reportid is not False:
                        reportid = int(reportid)
                else:
                    reportid = False

                body = lxml.html.tostring(node)
                reportcontent = minimalhtml.format(css, '', body, base_url)
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

        # Execute wkhtmltopdf process.
        pdf = self._generate_wkhtml_pdf(headerhtml, footerhtml, contenthtml, landscape,
                                        paperformat, specific_paperformat_args, save_in_attachment)

        return self._make_pdf_response(pdf)

    def _get_url_content(self, url, post=None):
        """Resolve an internal webpage url and return its content with the help of
        werkzeug.test.client.

        :param url: string representing the url to resolve
        :param post: a dict representing the query string
        :returns: a tuple str(html), int(statuscode)
        """
        # Rebuilding the query string.
        if post:
            url += '?'
            url += '&'.join('%s=%s' % (k, v) for (k, v) in post.iteritems())

        # We have to pass the current headers in order to see the report.
        reqheaders = Headers(request.httprequest.headers)
        response = Client(request.httprequest.app, BaseResponse).get(url, headers=reqheaders,
                                                                     follow_redirects=True)
        content = response.data

        try:
            content = content.decode('utf-8')
        except UnicodeDecodeError:
            pass

        return tuple([content, response.headers])

    def _generate_wkhtml_pdf(self, headers, footers, bodies, landscape,
                             paperformat, spec_paperformat_args=None, save_in_attachment=None):
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
        tmp_dir = tempfile.gettempdir()

        command_args = []
        # Passing the cookie in order to resolve URL.
        command_args.extend(['--cookie', 'session_id', request.httprequest.cookies['session_id']])

        # Display arguments
        if paperformat:
            command_args.extend(self._build_wkhtmltopdf_args(paperformat, spec_paperformat_args))

        if landscape and '--orientation' in command_args:
            command_args_copy = list(command_args)
            for index, elem in enumerate(command_args_copy):
                if elem == '--orientation':
                    del command_args[index]
                    del command_args[index]
                    command_args.extend(['--orientation', 'landscape'])
        elif landscape and not '--orientation' in command_args:
            command_args.extend(['--orientation', 'landscape'])

        pdfdocuments = []
        # HTML to PDF thanks to WKhtmltopdf
        for index, reporthtml in enumerate(bodies):
            command_arg_local = []
            pdfreport = tempfile.NamedTemporaryFile(suffix='.pdf', prefix='report.tmp.',
                                                    mode='w+b')
            # Directly load the document if we have it
            if save_in_attachment and save_in_attachment['loaded_documents'].get(reporthtml[0]):
                pdfreport.write(save_in_attachment['loaded_documents'].get(reporthtml[0]))
                pdfreport.seek(0)
                pdfdocuments.append(pdfreport)
                continue

            # Header stuff
            if headers:
                head_file = tempfile.NamedTemporaryFile(suffix='.html', prefix='report.header.tmp.',
                                                        dir=tmp_dir, mode='w+')
                head_file.write(headers[index])
                head_file.seek(0)
                command_arg_local.extend(['--header-html', head_file.name])

            # Footer stuff
            if footers:
                foot_file = tempfile.NamedTemporaryFile(suffix='.html', prefix='report.footer.tmp.',
                                                        dir=tmp_dir, mode='w+')
                foot_file.write(footers[index])
                foot_file.seek(0)
                command_arg_local.extend(['--footer-html', foot_file.name])

            # Body stuff
            content_file = tempfile.NamedTemporaryFile(suffix='.html', prefix='report.body.tmp.',
                                                       dir=tmp_dir, mode='w+')
            content_file.write(reporthtml[1])
            content_file.seek(0)

            try:
                # If the server is running with only one worker, increase it to two to be able
                # to serve the http request from wkhtmltopdf.
                if config['workers'] == 1:
                    ppid = psutil.Process(os.getpid()).ppid
                    os.kill(ppid, signal.SIGTTIN)

                wkhtmltopdf = command + command_args + command_arg_local
                wkhtmltopdf += [content_file.name] + [pdfreport.name]

                process = subprocess.Popen(wkhtmltopdf, stdout=subprocess.PIPE,
                                           stderr=subprocess.PIPE)
                out, err = process.communicate()

                if config['workers'] == 1:
                    os.kill(ppid, signal.SIGTTOU)

                if process.returncode != 0:
                    raise except_osv(_('Report (PDF)'),
                                     _('wkhtmltopdf failed with error code = %s. '
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
                    request.registry['ir.attachment'].create(request.cr, request.uid, attachment)
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

        # Get and return the full pdf
        if len(pdfdocuments) == 1:
            content = pdfdocuments[0].read()
            pdfdocuments[0].close()
        else:
            content = self._merge_pdf(pdfdocuments)

        return content

    def _build_wkhtmltopdf_args(self, paperformat, specific_paperformat_args=None):
        """Build arguments understandable by wkhtmltopdf from an ir.actions.report.paperformat
        record.

        :paperformat: ir.actions.report.paperformat record associated to a document
        :specific_paperformat_args: a dict containing prioritized wkhtmltopdf arguments
        :returns: list of string containing the wkhtmltopdf arguments
        """
        command_args = []
        if paperformat.format and paperformat.format != 'custom':
            command_args.extend(['--page-size', paperformat.format])

        if paperformat.page_height and paperformat.page_width and paperformat.format == 'custom':
            command_args.extend(['--page-width', str(paperformat.page_width) + 'in'])
            command_args.extend(['--page-height', str(paperformat.page_height) + 'in'])

        if specific_paperformat_args and specific_paperformat_args['data-report-margin-top']:
            command_args.extend(['--margin-top',
                                 str(specific_paperformat_args['data-report-margin-top'])])
        elif paperformat.margin_top:
            command_args.extend(['--margin-top', str(paperformat.margin_top)])

        if paperformat.margin_left:
            command_args.extend(['--margin-left', str(paperformat.margin_left)])
        if paperformat.margin_bottom:
            command_args.extend(['--margin-bottom', str(paperformat.margin_bottom)])
        if paperformat.margin_right:
            command_args.extend(['--margin-right', str(paperformat.margin_right)])
        if paperformat.orientation:
            command_args.extend(['--orientation', str(paperformat.orientation)])
        if paperformat.header_spacing:
            command_args.extend(['--header-spacing', str(paperformat.header_spacing)])
        if paperformat.header_line:
            command_args.extend(['--header-line'])
        if paperformat.dpi:
            command_args.extend(['--dpi', str(paperformat.dpi)])

        return command_args

    def _get_report_from_name(self, report_name):
        """Get the first record of ir.actions.report.xml having the argument as value for
        the field report_name.
        """
        report_obj = request.registry['ir.actions.report.xml']
        qwebtypes = ['qweb-pdf', 'qweb-html']

        idreport = report_obj.search(request.cr, request.uid,
                                     [('report_type', 'in', qwebtypes),
                                      ('report_name', '=', report_name)])

        report = report_obj.browse(request.cr, request.uid, idreport[0],
                                   context=request.context)
        return report

    def _make_pdf_response(self, pdf):
        """Make a request response for a PDF file with correct http headers.

        :param pdf: content of a pdf in a string
        :returns: request response for a pdf document
        """
        pdfhttpheaders = [('Content-Type', 'application/pdf'),
                          ('Content-Length', len(pdf))]
        return request.make_response(pdf, headers=pdfhttpheaders)

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
        merged = StringIO.StringIO()
        writer.write(merged)
        merged.seek(0)
        content = merged.read()
        merged.close()
        return content

    @http.route(['/report/barcode', '/report/barcode/<type>/<path:value>'], type='http', auth="user")
    def barcode(self, type, value, width=300, height=50):
        """Contoller able to render barcode images thanks to reportlab.
        Samples: 
            <img t-att-src="'/report/barcode/QR/%s' % o.name"/>
            <img t-att-src="'/report/barcode/?type=%s&amp;value=%s&amp;width=%s&amp;height=%s' % ('QR', o.name, 200, 200)"/>

        :param type: Accepted types: 'Codabar', 'Code11', 'Code128', 'EAN13', 'EAN8', 'Extended39',
        'Extended93', 'FIM', 'I2of5', 'MSI', 'POSTNET', 'QR', 'Standard39', 'Standard93',
        'UPCA', 'USPS_4State'
        """
        try:
            width, height = int(width), int(height)
            barcode = createBarcodeDrawing(
                type, value=value, format='png', width=width, height=height
            )
            barcode = barcode.asString('png')
        except (ValueError, AttributeError):
            raise exceptions.HTTPException(description='Cannot convert into barcode.')

        return request.make_response(barcode, headers=[('Content-Type', 'image/png')])

    @http.route('/report/download', type='http', auth="user")
    def report_attachment(self, data, token):
        """This function is used by 'qwebactionmanager.js' in order to trigger the download of
        a report of any type.

        :param data: a javasscript array JSON.stringified containg report internal url ([0]) and
        type [1]
        :returns: Response with a filetoken cookie and an attachment header
        """
        requestcontent = simplejson.loads(data)
        url, type = requestcontent[0], requestcontent[1]
        file, fileheaders = self._get_url_content(url)

        if type == 'qweb-pdf':
            response = self._make_pdf_response(file)
            response.headers.add('Content-Disposition', 'attachment; filename=report.pdf;')
        elif type == 'controller':
            response = request.make_response(file)
            response.headers.add('Content-Disposition', fileheaders['Content-Disposition'])
            response.headers.add('Content-Type', fileheaders['Content-Type'])
        else:
            return

        response.headers.add('Content-Length', len(file))
        response.set_cookie('fileToken', token)
        return response

    @http.route('/report/check_wkhtmltopdf', type='json', auth="user")
    def check_wkhtmltopdf(self):
        """Check the presence of wkhtmltopdf and return its version. If wkhtmltopdf
        cannot be found, return False.
        """
        try:
            process = subprocess.Popen(['wkhtmltopdf', '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, err = process.communicate()
            if err:
                raise

            version = out.splitlines()[1].strip()
            version = version.split(' ')[1]

            if LooseVersion(version) < LooseVersion('0.12.0'):
                _logger.warning('Upgrade WKHTMLTOPDF to (at least) 0.12.0')
                return 'upgrade'

            return True
        except:
            _logger.error('You need WKHTMLTOPDF to print a pdf version of this report.')
            return False
