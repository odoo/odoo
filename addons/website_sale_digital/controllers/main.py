# -*- coding: utf-8 -*-

import base64
from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp.addons.website_portal.controllers.main import website_account
from openerp.addons.website_sale.controllers.main import website_sale
from cStringIO import StringIO
from werkzeug.utils import redirect


class website_sale_digital_confirmation(website_sale):

    @http.route([
        '/shop/confirmation',
    ], type='http', auth="public", website=True)
    def payment_confirmation(self, **post):
        response = super(website_sale_digital_confirmation, self).payment_confirmation(**post)
        order_lines = response.qcontext['order'].order_line
        digital_content = map(lambda x: x.product_id.type == 'digital', order_lines)
        response.qcontext.update(digital=any(digital_content))
        return response


class website_sale_digital(website_account):

    orders_page = '/my/orders'

    @http.route([
        '/my/orders/<int:order>',
    ], type='http', auth='user', website=True)
    def orders_followup(self, order=None, **post):
        response = super(website_sale_digital, self).orders_followup(order=order, **post)

        order_products_attachments = {}
        order = response.qcontext['order']
        invoiced_lines = request.env['account.invoice.line'].sudo().search([('invoice_id', 'in', order.invoice_ids.ids), ('invoice_id.state', '=', 'paid')])

        purchased_products_attachments = {}
        for il in invoiced_lines:
            p_obj = il.product_id
            # Ignore products that do not have digital content
            if not p_obj.product_tmpl_id.type == 'digital':
                continue

            # Search for product attachments
            A = request.env['ir.attachment']
            p_id = p_obj.id
            template = p_obj.product_tmpl_id
            att = A.search_read(
                domain=['|', '&', ('res_model', '=', p_obj._name), ('res_id', '=', p_id), '&', ('res_model', '=', template._name), ('res_id', '=', template.id)],
                fields=['name', 'write_date'],
                order='write_date desc',
            )

            # Ignore products with no attachments
            if not att:
                continue

            purchased_products_attachments[p_id] = att

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
            ["name", "datas", "file_type", "res_model", "res_id", "type", "url"]
        )

        if attachment:
            attachment = attachment[0]
        else:
            return redirect(self.orders_page)


        # Check if the user has bought the associated product
        res_model = attachment['res_model']
        res_id = attachment['res_id']
        purchased_products = request.env['account.invoice.line'].get_digital_purchases(request.uid)

        if res_model == 'product.product':
            if res_id not in purchased_products:
                return redirect(self.orders_page)

        # Also check for attachments in the product templates
        elif res_model == 'product.template':
            P = request.env['product.product']
            template_ids = map(lambda x: P.browse(x).product_tmpl_id.id, purchased_products)
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
            data = StringIO(base64.standard_b64decode(attachment["datas"]))
            return http.send_file(data, filename=attachment['name'], as_attachment=True)
        else:
            return request.not_found()
