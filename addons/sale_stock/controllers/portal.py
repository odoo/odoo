# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from werkzeug.exceptions import NotFound

from odoo import exceptions, SUPERUSER_ID
from odoo.addons.sale.controllers.portal import CustomerPortal
from odoo.http import request, route
from odoo.tools import consteq


class SaleStockPortal(CustomerPortal):

    def _stock_picking_check_access(self, picking_id, access_token=None):
        picking = request.env['stock.picking'].browse([picking_id])
        picking_sudo = picking.sudo()
        try:
            picking.check_access('read')
        except exceptions.AccessError:
            if not access_token or not consteq(picking_sudo.sale_id.access_token, access_token):
                raise
        return picking_sudo

    @route(['/my/picking/pdf/<int:picking_id>'], type='http', auth="public", website=True)
    def portal_my_picking_report(self, picking_id, access_token=None, **kw):
        """ Print delivery slip for customer, using either access rights or access token
        to be sure customer has access """
        try:
            picking_sudo = self._stock_picking_check_access(picking_id, access_token=access_token)
        except (exceptions.AccessError, exceptions.MissingError):
            return NotFound()

        # print report with sudo, since it require access to product, taxes, payment term etc.. and portal does not have those access rights.
        pdf = request.env['ir.actions.report'].sudo()._render_qweb_pdf('stock.action_report_delivery', [picking_sudo.id])[0]
        pdfhttpheaders = [
            ('Content-Type', 'application/pdf'),
            ('Content-Length', len(pdf)),
        ]
        return request.make_response(pdf, headers=pdfhttpheaders)

    @route(['/my/picking/return/pdf/<int:picking_id>'], type='http', auth="public", website=True)
    def portal_my_picking_return_report(self, picking_id, access_token=None, **kw):
        """ Print return label for customer, using either access rights or access token
        to be sure customer has access """
        try:
            picking_sudo = self._stock_picking_check_access(picking_id, access_token=access_token)
        except (exceptions.AccessError, exceptions.MissingError):
            return NotFound()

        pdf = \
        request.env['ir.actions.report'].sudo()._render_qweb_pdf('stock.return_label_report', [picking_sudo.id])[0]
        pdfhttpheaders = [
            ('Content-Type', 'application/pdf'),
            ('Content-Length', len(pdf)),
        ]
        return request.make_response(pdf, headers=pdfhttpheaders)
