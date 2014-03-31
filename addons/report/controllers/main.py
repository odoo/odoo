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

from openerp.addons.web.http import Controller, route, request

import simplejson
import urlparse
from werkzeug import exceptions
from reportlab.graphics.barcode import createBarcodeDrawing


class ReportController(Controller):

    #------------------------------------------------------
    # Generic reports controller
    #------------------------------------------------------
    @route('/report/<reportname>/<docids>', type='http', auth='user', website=True, multilang=True)
    def report_html(self, reportname, docids):
        cr, uid, context = request.cr, request.uid, request.context
        docids = self._eval_params(docids)
        return request.registry['report'].get_html(cr, uid, docids, reportname, context=context)

    @route('/report/pdf/report/<reportname>/<docids>', type='http', auth="user", website=True)
    def report_pdf(self, reportname, docids):
        cr, uid, context = request.cr, request.uid, request.context
        docids = self._eval_params(docids)
        pdf = request.registry['report'].get_pdf(cr, uid, docids, reportname, context=context)
        pdfhttpheaders = [('Content-Type', 'application/pdf'), ('Content-Length', len(pdf))]
        return request.make_response(pdf, headers=pdfhttpheaders)

    #------------------------------------------------------
    # Particular reports controller
    #------------------------------------------------------
    @route('/report/<reportname>', type='http', auth='user', website=True, multilang=True)
    def report_html_particular(self, reportname, **data):
        cr, uid, context = request.cr, request.uid, request.context
        report_obj = request.registry['report']
        data = self._eval_params(data)  # Sanitizing
        return report_obj.get_html(cr, uid, [], reportname, data=data, context=context)

    @route('/report/pdf/report/<reportname>', type='http', auth='user', website=True, multilang=True)
    def report_pdf_particular(self, reportname, **data):
        cr, uid, context = request.cr, request.uid, request.context
        report_obj = request.registry['report']
        data = self._eval_params(data)  # Sanitizing
        pdf = report_obj.get_pdf(cr, uid, [], reportname, data=data, context=context)
        pdfhttpheaders = [('Content-Type', 'application/pdf'), ('Content-Length', len(pdf))]
        return request.make_response(pdf, headers=pdfhttpheaders)

    #------------------------------------------------------
    # Misc. route utils
    #------------------------------------------------------
    @route(['/report/barcode', '/report/barcode/<type>/<path:value>'], type='http', auth="user")
    def report_barcode(self, type, value, width=300, height=50):
        """Contoller able to render barcode images thanks to reportlab.
        Samples: 
            <img t-att-src="'/report/barcode/QR/%s' % o.name"/>
            <img t-att-src="'/report/barcode/?type=%s&amp;value=%s&amp;width=%s&amp;height=%s' % 
                ('QR', o.name, 200, 200)"/>

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

    @route(['/report/download'], type='http', auth="user", website=True)
    def report_download(self, data, token):
        """This function is used by 'qwebactionmanager.js' in order to trigger the download of
        a pdf report.

        :param data: a javascript array JSON.stringified containg report internal url ([0]) and
        type [1]
        :returns: Response with a filetoken cookie and an attachment header
        """
        requestcontent = simplejson.loads(data)
        url, type = requestcontent[0], requestcontent[1]
        if type == 'qweb-pdf':
            reportname = url.split('/report/pdf/report/')[1].split('?')[0].split('/')[0]

            if '?' not in url:
                # Generic report:
                docids = url.split('/')[-1]
                response = self.report_pdf(reportname, docids)
            else:
                # Particular report:
                querystring = url.split('?')[1]
                querystring = dict(urlparse.parse_qsl(querystring))
                response = self.report_pdf_particular(reportname, **querystring)

            response.headers.add('Content-Disposition', 'attachment; filename=%s.pdf;' % reportname)
            response.set_cookie('fileToken', token)
            return response
        elif type =='controller':
            from werkzeug.test import Client
            from werkzeug.wrappers import BaseResponse
            from werkzeug.datastructures import Headers
            reqheaders = Headers(request.httprequest.headers)
            response = Client(request.httprequest.app, BaseResponse).get(url, headers=reqheaders, follow_redirects=True)
            response.set_cookie('fileToken', token)
            return response
        else:
            return

    @route(['/report/check_wkhtmltopdf'], type='json', auth="user")
    def check_wkhtmltopdf(self):
        return request.registry['report']._check_wkhtmltopdf()

    def _eval_params(self, param):
        """Parse a dict generated by the webclient (javascript) into a python dict.
        """
        if isinstance(param, dict):
            for key, value in param.iteritems():
                if value.lower() == 'false':
                    param[key] = False
                elif value.lower() == 'true':
                    param[key] = True
                elif ',' in value:
                    param[key] = [int(i) for i in value.split(',')]
                else:
                    try:
                        param[key] = int(value)
                    except (ValueError, TypeError):
                        pass
        else:
            if isinstance(param, (str, unicode)):
                param = [int(i) for i in param.split(',')]
            if isinstance(param, list):
                param = list(set(param))
            if isinstance(param, int):
                param = [param]
        return param
