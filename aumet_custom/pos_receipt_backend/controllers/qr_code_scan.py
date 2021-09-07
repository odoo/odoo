# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http, _
from odoo.exceptions import AccessError, MissingError
from odoo.http import request


class QrCodeScan(http.Controller):
    
    @http.route('/verify/qr/<string:pos_reference>', type='http', auth="public", website=True, sitemap=False)
    def qrpdf(self, pos_reference=None, **kw):
        pos_order_id = request.env['pos.order'].search([('pos_reference','=',pos_reference)], limit=1)
        
        if pos_order_id:
            #pdf, _ = request.env.ref('sale.action_report_saleorder').sudo().render_qweb_pdf([pos_order_id])
            pdf = request.env.ref('pos_receipt_backend.action_pos_backend_receipt')._render_qweb_pdf(pos_order_id.id)[0]
            pdfhttpheaders = [('Content-Type', 'application/pdf'), ('Content-Length', u'%s' % len(pdf))]
            return request.make_response(pdf, headers=pdfhttpheaders)

