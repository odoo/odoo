# -*- coding: utf-8 -*-
import werkzeug
from werkzeug.exceptions import InternalServerError

from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.main import _serialize_exception

import json


class StockReportController(http.Controller):

    @http.route('/stock/<string:output_format>/<string:report_name>/<int:report_id>', type='http', auth='user')
    def report(self, output_format, report_name, token, report_id=False, **kw):
        uid = request.session.uid
        domain = [('create_uid', '=', uid)]
        stock_traceability = request.env['stock.traceability.report'].with_user(uid).search(domain, limit=1)
        line_data = json.loads(kw['data'])
        try:
            if output_format == 'pdf':
                response = request.make_response(
                    stock_traceability.with_context(active_id=report_id).get_pdf(line_data),
                    headers=[
                        ('Content-Type', 'application/pdf'),
                        ('Content-Disposition', 'attachment; filename=' + 'stock_traceability' + '.pdf;')
                    ]
                )
                response.set_cookie('fileToken', token)
                return response
        except Exception as e:
            se = _serialize_exception(e)
            error = {
                'code': 200,
                'message': 'Odoo Server Error',
                'data': se
            }
            res = werkzeug.wrappers.Response(
                json.dumps(error),
                status=500,
                headers=[("Content-Type", "application/json")]
            )
            raise InternalServerError(response=res) from e
