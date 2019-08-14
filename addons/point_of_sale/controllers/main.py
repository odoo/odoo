# -*- coding: utf-8 -*-
import json
import logging
import werkzeug.utils

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class PosController(http.Controller):

    @http.route('/pos/web', type='http', auth='user')
    def pos_web(self, **k):
        # if user not logged in, log him in
        pos_sessions = request.env['pos.session'].sudo().search([
            ('state', '=', 'opened'),
            ('user_id', '=', request.session.uid),
            ('rescue', '=', False)])
        if not pos_sessions:
            return werkzeug.utils.redirect('/web#action=point_of_sale.action_client_pos_menu')
        pos_sessions.login()
        # The POS only work in one company, so we enforce the one of the session in the context
        session_info = request.env['ir.http'].session_info()
        session_info['user_context']['allowed_company_ids'] = pos_sessions.company_id.ids
        context = {
            'session_info': session_info
        }
        return request.render('point_of_sale.index', qcontext=context)

    @http.route('/pos/sale_details_report', type='http', auth='user')
    def print_sale_details(self, date_start=False, date_stop=False, **kw):
        r = request.env['report.point_of_sale.report_saledetails']
        pdf, _ = request.env.ref('point_of_sale.sale_details_report').with_context(date_start=date_start, date_stop=date_stop).render_qweb_pdf(r)
        pdfhttpheaders = [('Content-Type', 'application/pdf'), ('Content-Length', len(pdf))]
        return request.make_response(pdf, headers=pdfhttpheaders)
