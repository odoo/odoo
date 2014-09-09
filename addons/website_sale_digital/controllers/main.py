# -*- coding: utf-8 -*-

import base64
import util
from openerp import SUPERUSER_ID
from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp.addons.website.controllers.main import Website
from openerp.addons.website_sale.controllers.main import website_sale
from werkzeug.utils import redirect


class website_sale_digital(website_sale):

    downloads_page = '/shop/downloads'

    @http.route([
        '/shop/confirmation',
    ], type='http', auth="public", website=True)
    def payment_confirmation(self, **post):
        response = super(website_sale_digital, self).payment_confirmation(**post)
        order_lines = response.qcontext['order'].order_line
        digital_content = map(lambda x: x.product_id.digital_content, order_lines)
        response.qcontext.update(digital=any(digital_content))
        return response

    @http.route([
        '/shop/attachment',
    ], auth='public')
    def download_attachment(self, attachment_id):
        # Check if this is a valid attachment id
        attachment = request.env['ir.attachment'].sudo().search_read(
            [('id', '=', int(attachment_id))],
            ["name", "datas", "file_type", "res_model", "res_id"]
        )
        if attachment:
            attachment = attachment[0]
        else:
            redirect(self.downloads_page)

        # Check if the user has bought the associated product
        res_model = attachment['res_model']
        res_id = attachment['res_id']
        purchased_products = util.get_digital_purchases(request.uid)
        product_ids = map(lambda x: x['product_id'][0], purchased_products)

        if res_model == 'product.template':
            P = request.env['product.product']
            template_ids = map(lambda x: P.browse(x).product_tmpl_id.id, product_ids)
            if res_id not in template_ids:
                return redirect(self.downloads_page)

        elif res_model == 'product.product':
            if res_id not in product_ids:
                return redirect(self.downloads_page)

        else:
            return redirect(self.downloads_page)

        # The client has bought the product, otherwise it would have been blocked by now
        data = base64.standard_b64decode(attachment["datas"])
        headers = [
            ('Content-Type', attachment['file_type']),
            ('Content-Length', len(data)),
            ('Content-Disposition', 'attachment; filename="' + attachment['name'] + '"')
        ]
        return request.make_response(data, headers)

    @http.route([
        downloads_page,
    ], type='http', auth='public', website=True)
    def display_attachments(self):
        purchased_products = util.get_digital_purchases(request.uid)

        # Superuser to be able to see product that are not published anymore, I bought the
        # right to download these products, even if they are not website_published anymore.
        A = request.env['ir.attachment'].sudo()
        P = request.env['product.product'].sudo()
        products = []
        names = {}
        attachments = {}
        for product in purchased_products:
            # Ignore duplicate products
            p_id = product['product_id'][0]
            p_obj = P.browse(p_id)
            if p_obj in products:
                continue

            # Search for product attachments
            template = p_obj.product_tmpl_id
            att = A.search_read(
                domain=['|', '&', ('res_model', '=', p_obj._name), ('res_id', '=', p_id), '&', ('res_model', '=', template._name), ('res_id', '=', template.id)],
                fields=['name'],
            )

            # Ignore products with no attachments
            if not att:
                continue

            # I want template_name (comma, separated, attributes), but not the product code like [A252]
            products.append(p_obj)
            attributes = p_obj.attribute_value_ids
            if attributes:
                names[p_id] = template.name + ' (' + ', '.join([a.name for a in attributes]) + ')'
            else:
                names[p_id] = template.name
            attachments[p_id] = att

        return request.website.render('website_sale_digital.downloads', {
            'products': products,
            'names': names,
            'attachments': attachments,
        })


class Website_Unpublished_Images_Server(Website):

    @http.route([
        '/website/image/<model>/<p_id>/<field>',
        '/website/image/<model>/<p_id>/<field>/<int:max_width>x<int:max_height>'
    ], auth="public", website=True)
    def website_image(self, model, p_id, field, max_width=None, max_height=None):
        """ Allows to display images for products with website_published=False
            Gives admin access to images if the user has bought the product.
        """
        if model in ['product.product', 'product.template']:
            # Confirm = False to display images in cart
            purchased_products = util.get_digital_purchases(request.uid, confirmed=False)
            product_ids = map(lambda x: x['product_id'][0], purchased_products)
            if int(p_id) in product_ids:
                request.uid = SUPERUSER_ID

        return super(Website_Unpublished_Images_Server, self).website_image(model, p_id, field, max_width, max_height)
