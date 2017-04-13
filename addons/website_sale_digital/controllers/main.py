# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import io
import re
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
        order = response.qcontext['order']
        attachments = order.get_purchased_digital_content()
        response.qcontext.update(digital_content=attachments)
        return response


class WebsiteSaleDigital(CustomerPortal):
    orders_page = '/my/orders'

    @http.route([
        '/my/orders/<int:order>',
    ], type='http', auth='user', website=True)
    def portal_order_page(self, order=None, **post):
        response = super(WebsiteSaleDigital, self).portal_order_page(order=order, **post)
        if not 'order' in response.qcontext:
            return response
        order = response.qcontext['order']
        attachments = order.get_purchased_digital_content()
        response.qcontext.update({
            'digital_attachments': attachments,
        })
        return response

    @http.route([
        '/my/download',
    ], type='http', auth='public')
    def download_attachment(self, attachment_id):
        # Check if this is a valid attachment id
        attachment = request.env['ir.attachment'].sudo().search_read(
            [('id', '=', int(attachment_id)), ('product_downloadable', '=', True)], ["name", "download_count", "datas_fname", "datas", "res_model", "res_id", "type", "url"])

        if attachment:
            attachment = attachment[0]
        else:
            return redirect(self.orders_page)

        # Check if the user has bought the associated product

        res_model = attachment['res_model']
        res_id = attachment['res_id']
        partner = request.env.user.partner_id
        purchased_products = request.env['sale.order'].sudo().search(
            [('partner_id', '=', partner.id), ('payment_state', '=', 'done')]).mapped('order_line').mapped('product_id')
        purchased_products += request.env['account.invoice'].sudo().search(
            [('state', '=', 'paid'), ('partner_id', '=', partner.id)]).mapped('invoice_line_ids').mapped('product_id')

        if (res_model not in ['product.product', 'product.template'] or
                (res_model == 'product.product' and res_id not in purchased_products.ids) or
                (res_model == 'product.template' and res_id not in purchased_products.mapped('product_tmpl_id').ids)):
            return redirect(self.orders_page)

        attachment_record = request.env['ir.attachment'].sudo().browse(attachment['id'])
        # The client has bought the product, otherwise it would have been blocked by now
        if attachment['type'] == "url":
            if attachment['url']:
                attachment_record.download_count += 1
                if re.match(r'^(http://|https://|/)', attachment['url']):
                    return redirect(attachment['url'])
                else:
                    return redirect('http://' + attachment['url'])
            else:
                return request.not_found()
        elif attachment['datas']:
            data = io.BytesIO(base64.standard_b64decode(attachment['datas']))
            attachment_record.download_count += 1
            return http.send_file(data, filename=attachment['datas_fname'], as_attachment=True)
        else:
            return request.not_found()
