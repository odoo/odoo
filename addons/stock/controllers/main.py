import json

from werkzeug.exceptions import InternalServerError

from odoo.http import Controller, request, route
from odoo.http.dispatcher import serialize_exception
from odoo.http.stream import content_disposition
from odoo.tools.misc import html_escape


class StockReportController(Controller):

    @route('/stock/<string:output_format>/<string:report_name>', type='http', auth='user')
    def report(self, output_format, report_name=False, **kw):
        uid = request.session.uid
        domain = [('create_uid', '=', uid)]
        stock_traceability = request.env['stock.traceability.report'].with_user(uid).search(domain, limit=1)
        line_data = json.loads(kw['data'])
        try:
            if output_format == 'pdf':
                response = request.make_response(
                    stock_traceability.with_context(active_id=kw['active_id'], active_model=kw['active_model']).get_pdf(line_data),
                    headers=[
                        ('Content-Type', 'application/pdf'),
                        ('Content-Disposition', content_disposition('stock_traceability.pdf')),
                    ],
                )
                return response
        except Exception as e:
            se = serialize_exception(e)
            error = {
                'code': 0,
                'message': 'Odoo Server Error',
                'data': se,
            }
            res = request.make_response(html_escape(json.dumps(error)))
            raise InternalServerError(response=res) from e
