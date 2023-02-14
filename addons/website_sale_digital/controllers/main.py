# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import io
import os
import mimetypes

from odoo import http
from odoo.exceptions import AccessError
from odoo.http import request
from odoo.addons.sale.controllers.portal import CustomerPortal


class WebsiteSaleDigital(CustomerPortal):
    orders_page = '/my/orders'

    @http.route([
        '/my/orders/<int:order_id>',
    ], type='http', auth='public', website=True)
    def portal_order_page(self, order_id=None, **post):
        response = super(WebsiteSaleDigital, self).portal_order_page(order_id=order_id, **post)
        if not 'sale_order' in response.qcontext:
            return response
        order = response.qcontext['sale_order']
        invoiced_lines = request.env['account.move.line'].sudo().search([('move_id', 'in', order.invoice_ids.ids), ('move_id.payment_state', 'in', ['paid', 'in_payment'])])
        products = invoiced_lines.mapped('product_id') | order.order_line.filtered(lambda r: not r.price_subtotal).mapped('product_id')
        if not order.amount_total:
            # in that case, we should add all download links to the products
            # since there is nothing to pay, so we shouldn't wait for an invoice
            products = order.order_line.mapped('product_id')

        Attachment = request.env['ir.attachment'].sudo()
        purchased_products_attachments = {}
        for product in products.filtered(lambda p: p.attachment_count):
            # Search for product attachments
            product_id = product.id
            template = product.product_tmpl_id
            att = Attachment.sudo().search_read(
                domain=['|', '&', ('res_model', '=', product._name), ('res_id', '=', product_id), '&', ('res_model', '=', template._name), ('res_id', '=', template.id), ('product_downloadable', '=', True)],
                fields=['name', 'write_date'],
                order='write_date desc',
            )

            # Ignore products with no attachments
            if not att:
                continue

            purchased_products_attachments[product_id] = att

        response.qcontext.update({
            'digital_attachments': purchased_products_attachments,
        })
        return response

    @http.route([
        '/my/download',
    ], type='http', auth='public')
    def download_attachment(self, attachment_id):
        # Check if this is a valid attachment id
        attachment = request.env['ir.attachment'].sudo().browse(int(attachment_id)).exists()
        if not attachment:
            return request.redirect(self.orders_page)

        try:
            request.env['ir.attachment'].browse(attachment_id).check('read')
        except AccessError:  # The user does not have read access on the attachment.
            # Check if access can be granted through their purchases.
            res_model = attachment['res_model']
            res_id = attachment['res_id']
            digital_purchases = request.env['account.move.line'].get_digital_purchases()
            if res_model == 'product.product':
                purchased_product_ids = digital_purchases
            elif res_model == 'product.template':
                purchased_product_ids = request.env['product.product'].sudo().browse(
                    digital_purchases
                ).mapped('product_tmpl_id').ids
            else:
                purchased_product_ids = []  # The purchases must be related to products.
            if res_id not in purchased_product_ids:  # No related purchase was found.
                return request.redirect(self.orders_page)  # Prevent the user from downloading.

        # The user has bought the product, or has the rights to the attachment
        return request.env['ir.binary']._get_stream_from(attachment).get_response(as_attachment=True)
