# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import AccessError, MissingError
from odoo.http import request, route

from odoo.addons.sale.controllers.portal import CustomerPortal


class SaleStockPortal(CustomerPortal):

    @route(['/my/orders/<int:order_id>/picking/<int:picking_id>'], type='http', auth="public", website=True)
    def portal_order_picking(self, order_id, picking_id, access_token=None):
        try:
            order_sudo = self._document_check_access('sale.order', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        if picking_id not in order_sudo.picking_ids.ids:
            # Picking doesn't exist, or is not linked to provided SO
            return request.redirect('/my')

        # print report with sudo, since it require access to product, taxes, payment term etc.. and portal does not have those access rights.
        pdf = request.env['ir.actions.report'].sudo()._render_qweb_pdf('stock.action_report_delivery', [picking_id])[0]

        return request.make_response(
            pdf,
            headers=[
                ('Content-Type', 'application/pdf'),
                ('Content-Length', len(pdf)),
            ]
        )
