# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import io
import os
import mimetypes
from werkzeug.utils import redirect

from odoo import http
from odoo.http import request
from odoo.addons.sale.controllers.portal import CustomerPortal
from odoo.addons.website_sale.controllers.main import WebsiteSale


class WebsiteSaleDigitalConfirmation(WebsiteSale):
    @http.route([
        '/shop/confirmation',
    ], type='http', auth="public", website=True)
    def payment_confirmation(self, **post):
        response = super(WebsiteSaleDigitalConfirmation, self).payment_confirmation(**post)
        order_lines = response.qcontext['order'].order_line
        digital_content = any(x.product_id.type == 'digital' for x in order_lines)
        response.qcontext.update(digital=digital_content)
        return response


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
        invoiced_lines = request.env['account.move.line'].sudo().search([('move_id', 'in', order.invoice_ids.ids), ('move_id.invoice_payment_state', '=', 'paid')])
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
        attachment = request.env['ir.attachment'].sudo().search_read(
            [('id', '=', int(attachment_id))],
            ["name", "datas", "mimetype", "res_model", "res_id", "type", "url"]
        )

        if attachment:
            attachment = attachment[0]
        else:
            return redirect(self.orders_page)

        # Check if the user has bought the associated product
        res_model = attachment['res_model']
        res_id = attachment['res_id']
        purchased_products = request.env['account.move.line'].get_digital_purchases()

        if res_model == 'product.product':
            if res_id not in purchased_products:
                return redirect(self.orders_page)

        # Also check for attachments in the product templates
        elif res_model == 'product.template':
            template_ids = request.env['product.product'].sudo().browse(purchased_products).mapped('product_tmpl_id').ids
            if res_id not in template_ids:
                return redirect(self.orders_page)

        else:
            return redirect(self.orders_page)

        # The client has bought the product, otherwise it would have been blocked by now
        if attachment["type"] == "url":
            if attachment["url"]:
                return redirect(attachment["url"])
            else:
                return request.not_found()
        elif attachment["datas"]:
            data = io.BytesIO(base64.standard_b64decode(attachment["datas"]))
            # we follow what is done in ir_http's binary_content for the extension management
            extension = os.path.splitext(attachment["name"] or '')[1]
            extension = extension if extension else mimetypes.guess_extension(attachment["mimetype"] or '')
            filename = attachment['name']
            filename = filename if os.path.splitext(filename)[1] else filename + extension
            return http.send_file(data, filename=filename, as_attachment=True)
        else:
            return request.not_found()
