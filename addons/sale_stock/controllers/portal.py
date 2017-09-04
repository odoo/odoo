# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.exceptions import AccessError
from odoo.http import request
from odoo.tools import consteq


class PortalDelivery(CustomerPortal):
    @http.route(['/my/deliveryslip/pdf/<int:delivery_id>'], type='http', auth="public", website=True)
    def portal_my_delivery_report(self, delivery_id, access_token=None, **kw):
        delivery = request.env['stock.picking'].browse([delivery_id])
        delivery_sudo = delivery.sudo()
        try:
            delivery.check_access_rights('read')
            delivery.check_access_rule('read')
        except AccessError:
            if not access_token or not consteq(delivery_sudo.access_token, access_token):
                raise
            return request.redirect('/my')

        # print report as sudo, since it require access to product, taxes, payment term etc.. and portal does not have those access rights.
        pdf = request.env.ref('stock.action_report_delivery').sudo().render_qweb_pdf([delivery_sudo.id])[0]
        pdfhttpheaders = [
            ('Content-Type', 'application/pdf'),
            ('Content-Length', len(pdf)),
        ]
        return request.make_response(pdf, headers=pdfhttpheaders)
