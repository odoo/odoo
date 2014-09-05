# -*- coding: utf-8 -*-

import base64
from openerp import SUPERUSER_ID as SU
from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp.addons.website_sale.controllers.main import website_sale
from itertools import groupby
from werkzeug.exceptions import NotFound


class website_sale_digital(website_sale):

    @http.route([
        '/shop/confirmation',
    ], type='http', auth="public", website=True)
    def display_attachments(self, **post):
        r = super(website_sale_digital, self).payment_confirmation(**post)
        return r

    @http.route([
        '/shop/attachment',
    ], auth='public')
    def download_attachment(self, attachment_id):
        res = request.env(user=SU)['ir.attachment'].search_read([('id', '=', int(attachment_id))], ["name", "datas", "file_type"])
        if res:
            res = res[0]
        else:
            raise NotFound()
        data = base64.standard_b64decode(res["datas"])
        headers = [
            ('Content-Type', res['file_type']),
            ('Content-Length', len(data)),
            ('Content-Disposition', 'attachment; filename="' + res['name'] + '"')
        ]
        return request.make_response(data, headers)

    @http.route([
        '/website_sale_digital/downloads',
    ], type='http', auth='public', website=True)
    def get_downloads(self):
        user = request.env['res.users'].browse(request.uid)
        partner = user.partner_id

        # purchased_products = request.env['sale.order.line'].read_group(
        #     domain = ['&', ('order_id.partner_id', '=', partner.id), ('state', '=', 'confirmed')],#, ('product_id.data','=' true)])
        #     fields = ['order_id', product_id'],
        #     groupby = 'product_id',
        #     #orderby = 'order_id',
        # )

        purchased_products = request.env['sale.order.line'].search_read(
            domain = ['&', ('order_id.partner_id', '=', partner.id), ('state', '=', 'confirmed')],#, ('product_id.data','=' true)])
            fields = ['product_id'],
        )

        products_ids = []
        names = {}
        attachments = {}
        A = request.env['ir.attachment']
        P = request.env['product.product']
        for product in purchased_products:
            # Ignore duplicate products
            p_id = product['product_id'][0]
            if p_id in products_ids:
                continue

            # Search for product attachments
            p_name = product['product_id'][1]
            p_obj = P.browse(p_id)
            template = p_obj.product_tmpl_id
            att = A.search_read(
                domain = ['|', '&', ('res_model', '=', 'product.product'), ('res_id', '=', p_id), '&', ('res_model', '=', 'product.template'), ('res_id', '=', template.id)],
                fields = ['name'],
            )

            # Ignore products with no attachments
            if not att:
                continue

            # Store values for QWeb
            products_ids.append(p_id)
            attributes = p_obj.attribute_value_ids
            if attributes:
                names[p_id] = template.name + ' (' + ', '.join([a.name for a in attributes]) + ')'
            else:
                names[p_id] = template.name
            attachments[p_id] = att

        return request.website.render('website_sale_digital.downloads', {
            'products': products_ids,
            'names': names,
            'attachments': attachments
        })