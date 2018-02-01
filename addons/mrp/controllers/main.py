# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import http, _
from odoo.http import request
from odoo.addons.web.controllers.main import _serialize_exception
from odoo.tools import html_escape

class MrpReportController(http.Controller):

    @http.route('/mrp/pdf/bom_report/<int:bom_id>', type='http', auth='user')
    def report(self, token, bom_id=False, **kw):
        child_bom_ids = json.loads(kw.get('child_bom_ids')) or []
        try:
            response = request.make_response(
                request.env['mrp.bom.report'].get_pdf(bom_id, child_bom_ids),
                headers=[
                    ('Content-Type', 'application/pdf'),
                    ('Content-Disposition', 'attachment; filename=mrp_bom_report.pdf;')
                ]
            )
            response.set_cookie('fileToken', token)
            return response
        except Exception as e:
            se = _serialize_exception(e)
            error = {
                'code': 500,
                'message': _('Odoo Server Error'),
                'data': se
            }
            return request.make_response(html_escape(json.dumps(error)))
