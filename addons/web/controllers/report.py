# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging

import werkzeug.exceptions
from werkzeug.urls import url_parse

from odoo import http
from odoo.http import content_disposition, request
from odoo.tools.misc import html_escape
from odoo.tools.safe_eval import safe_eval, time


_logger = logging.getLogger(__name__)


class ReportController(http.Controller):

    #------------------------------------------------------
    # Report controllers
    #------------------------------------------------------
    @http.route([
        '/report/<converter>/<reportname>',
        '/report/<converter>/<reportname>/<docids>',
    ], type='http', auth='user', website=True)
    def report_routes(self, reportname, docids=None, converter=None, **data):
        report = request.env['ir.actions.report']
        context = dict(request.env.context)

        if docids:
            docids = [int(i) for i in docids.split(',') if i.isdigit()]
        if data.get('options'):
            data.update(json.loads(data.pop('options')))
        if data.get('context'):
            data['context'] = json.loads(data['context'])
            context.update(data['context'])
        if converter == 'html':
            html = report.with_context(context)._render_qweb_html(reportname, docids, data=data)[0]
            return request.make_response(html)
        elif converter == 'pdf':
            pdf = report.with_context(context)._render_qweb_pdf(reportname, docids, data=data)[0]
            pdfhttpheaders = [('Content-Type', 'application/pdf'), ('Content-Length', len(pdf))]
            return request.make_response(pdf, headers=pdfhttpheaders)
        elif converter == 'text':
            text = report.with_context(context)._render_qweb_text(reportname, docids, data=data)[0]
            texthttpheaders = [('Content-Type', 'text/plain'), ('Content-Length', len(text))]
            return request.make_response(text, headers=texthttpheaders)
        else:
            raise werkzeug.exceptions.HTTPException(description='Converter %s not implemented.' % converter)

    #------------------------------------------------------
    # Misc. route utils
    #------------------------------------------------------
    @http.route(['/report/barcode', '/report/barcode/<barcode_type>/<path:value>'], type='http', auth="public")
    def report_barcode(self, barcode_type, value, **kwargs):
        """Contoller able to render barcode images thanks to reportlab.
        Samples::

            <img t-att-src="'/report/barcode/QR/%s' % o.name"/>
            <img t-att-src="'/report/barcode/?barcode_type=%s&amp;value=%s&amp;width=%s&amp;height=%s' %
                ('QR', o.name, 200, 200)"/>

        :param barcode_type: Accepted types: 'Codabar', 'Code11', 'Code128', 'EAN13', 'EAN8',
        'Extended39', 'Extended93', 'FIM', 'I2of5', 'MSI', 'POSTNET', 'QR', 'Standard39',
        'Standard93', 'UPCA', 'USPS_4State'
        :param width: Pixel width of the barcode
        :param height: Pixel height of the barcode
        :param humanreadable: Accepted values: 0 (default) or 1. 1 will insert the readable value
        at the bottom of the output image
        :param quiet: Accepted values: 0 (default) or 1. 1 will display white
        margins on left and right.
        :param mask: The mask code to be used when rendering this QR-code.
                     Masks allow adding elements on top of the generated image,
                     such as the Swiss cross in the center of QR-bill codes.
        :param barLevel: QR code Error Correction Levels. Default is 'L'.
        ref: https://hg.reportlab.com/hg-public/reportlab/file/830157489e00/src/reportlab/graphics/barcode/qr.py#l101
        """
        try:
            barcode = request.env['ir.actions.report'].barcode(barcode_type, value, **kwargs)
        except (ValueError, AttributeError):
            raise werkzeug.exceptions.HTTPException(description='Cannot convert into barcode.')

        return request.make_response(barcode, headers=[('Content-Type', 'image/png')])

    @http.route(['/report/download'], type='http', auth="user")
    def report_download(self, data, context=None, token=None):  # pylint: disable=unused-argument
        """This function is used by 'action_manager_report.js' in order to trigger the download of
        a pdf/controller report.

        :param data: a javascript array JSON.stringified containg report internal url ([0]) and
        type [1]
        :returns: Response with an attachment header

        """
        requestcontent = json.loads(data)
        url, type_ = requestcontent[0], requestcontent[1]
        reportname = '???'
        try:
            if type_ in ['qweb-pdf', 'qweb-text']:
                converter = 'pdf' if type_ == 'qweb-pdf' else 'text'
                extension = 'pdf' if type_ == 'qweb-pdf' else 'txt'

                pattern = '/report/pdf/' if type_ == 'qweb-pdf' else '/report/text/'
                reportname = url.split(pattern)[1].split('?')[0]

                docids = None
                if '/' in reportname:
                    reportname, docids = reportname.split('/')

                if docids:
                    # Generic report:
                    response = self.report_routes(reportname, docids=docids, converter=converter, context=context)
                else:
                    # Particular report:
                    data = url_parse(url).decode_query(cls=dict)  # decoding the args represented in JSON
                    if 'context' in data:
                        context, data_context = json.loads(context or '{}'), json.loads(data.pop('context'))
                        context = json.dumps({**context, **data_context})
                    response = self.report_routes(reportname, converter=converter, context=context, **data)

                report = request.env['ir.actions.report']._get_report_from_name(reportname)
                filename = "%s.%s" % (report.name, extension)

                if docids:
                    ids = [int(x) for x in docids.split(",") if x.isdigit()]
                    obj = request.env[report.model].browse(ids)
                    if report.print_report_name and not len(obj) > 1:
                        report_name = safe_eval(report.print_report_name, {'object': obj, 'time': time})
                        filename = "%s.%s" % (report_name, extension)
                response.headers.add('Content-Disposition', content_disposition(filename))
                return response
            else:
                return
        except Exception as e:
            _logger.exception("Error while generating report %s", reportname)
            se = http.serialize_exception(e)
            error = {
                'code': 200,
                'message': "Odoo Server Error",
                'data': se
            }
            res = request.make_response(html_escape(json.dumps(error)))
            raise werkzeug.exceptions.InternalServerError(response=res) from e

    @http.route(['/report/check_wkhtmltopdf'], type='json', auth="user")
    def check_wkhtmltopdf(self):
        return request.env['ir.actions.report'].get_wkhtmltopdf_state()
