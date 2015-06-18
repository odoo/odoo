# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
from cStringIO import StringIO
from werkzeug.utils import redirect
from odoo import http
from odoo.http import request
from odoo.addons.website_portal.controllers.main import website_account
from odoo.addons.website_sale.controllers.main import website_sale


class WebsiteSaleDigitalConfirmation(website_sale):

    @http.route([
        '/shop/confirmation',
    ], type='http', auth="public", website=True)
    def payment_confirmation(self, **post):
        response = super(WebsiteSaleDigitalConfirmation, self).payment_confirmation(**post)
        order_lines = response.qcontext['order'].order_line
        response.qcontext.update(digital=bool(order_lines.filtered(lambda line: line.product_id.type == 'digital')))
        return response


class WebsiteSaleDigital(website_account):

    orders_page = '/my/orders'

    @http.route([
        '/my/orders/<int:order>',
    ], type='http', auth='user', website=True)
    def orders_followup(self, order=None, **post):
        response = super(WebsiteSaleDigital, self).orders_followup(order=order, **post)

        order = response.qcontext['order']
        # Ignore the lines that do not have digital product
        invoiced_lines = request.env['account.invoice.line'].sudo().search([('invoice_id', 'in', order.invoice_ids.ids), ('invoice_id.state', '=', 'paid')]).filtered(lambda line: line.product_id.product_tmpl_id.type == 'digital')

        purchased_products_attachments = {}
        for line in invoiced_lines:
            product = line.product_id

            # Search for product attachments
            attachments = request.env['ir.attachment'].search(
                ['|', '&', ('res_model', '=', product._name), ('res_id', '=', product.id), '&', ('res_model', '=', product.product_tmpl_id._name), ('res_id', '=', product.product_tmpl_id.id)],
                order='write_date desc'
            )

            # Ignore products with no attachments
            if not attachments:
                continue

            purchased_products_attachments[product.id] = attachments

        response.qcontext.update({
            'digital_attachments': purchased_products_attachments,
        })
        return response

    @http.route([
        '/my/download',
    ], type='http', auth='public')
    def download_attachment(self, attachment_id):
        # Check if this is a valid attachment id
        attachment = request.env['ir.attachment'].sudo().search([('id', '=', int(attachment_id))])

        if not attachment:
            return redirect(self.orders_page)


        # Check if the user has bought the associated product
        res_model = attachment.res_model
        res_id = attachment.res_id
        purchased_products = request.env['account.invoice.line'].get_digital_purchases()

        if res_model == 'product.product':
            if res_id not in purchased_products.ids:
                return redirect(self.orders_page)

        # Also check for attachments in the product templates
        elif res_model == 'product.template':
            if res_id not in purchased_products.mapped('product_tmpl_id.id'):
                return redirect(self.orders_page)

        else:
            return redirect(self.orders_page)

        # The client has bought the product, otherwise it would have been blocked by now
        if attachment.type == 'url':
            return redirect(attachment.url) if attachment.url else request.not_found()
        elif attachment.datas:
            data = StringIO(base64.standard_b64decode(attachment.datas))
            return http.send_file(data, filename=attachment.name, as_attachment=True)
        else:
            return request.not_found()
