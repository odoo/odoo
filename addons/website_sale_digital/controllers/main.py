# -*- coding: utf-8 -*-

import base64
import util
from openerp import SUPERUSER_ID
from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp.addons.website.controllers.main import Website
from openerp.addons.website_sale.controllers.main import website_sale
from cStringIO import StringIO
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
        downloads_page,
    ], type='http', auth='public', website=True)
    def display_attachments(self, **post):
        purchased_products = util.get_digital_purchases(request.uid)

        # Superuser to be able to see product that are not published anymore, I bought the
        # right to download these products, even if they are not website_published anymore.
        A = request.env['ir.attachment'].sudo()
        P = request.env['product.product'].sudo()
        products = []
        names = {}
        attachments = {}
        for p_id in purchased_products:
            # Ignore duplicate products
            p_obj = P.browse(p_id)
            if p_obj in products:
                continue

            # Search for product attachments
            template = p_obj.product_tmpl_id
            att = A.search_read(
                domain=['|', '&', ('res_model', '=', p_obj._name), ('res_id', '=', p_id), '&', ('res_model', '=', template._name), ('res_id', '=', template.id)],
                fields=['name', 'write_date'],
                order='write_date desc',
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

    @http.route([
        '/shop/attachment',
    ], auth='public')
    def download_attachment(self, attachment_id):
        # Check if this is a valid attachment id
        attachment = request.env['ir.attachment'].sudo().search_read(
            [('id', '=', int(attachment_id))],
            ["name", "datas", "file_type", "res_model", "res_id", "type", "url"]
        )
        if attachment:
            attachment = attachment[0]
        else:
            redirect(self.downloads_page)

        # Check if the user has bought the associated product
        res_model = attachment['res_model']
        res_id = attachment['res_id']
        purchased_products = util.get_digital_purchases(request.uid)

        if res_model == 'product.product':
            if res_id not in purchased_products:
                return redirect(self.downloads_page)

        # Also check for attachments in the product templates
        elif res_model == 'product.template':
            P = request.env['product.product']
            template_ids = map(lambda x: P.browse(x).product_tmpl_id.id, purchased_products)
            if res_id not in template_ids:
                return redirect(self.downloads_page)

        else:
            return redirect(self.downloads_page)

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


class Website_Unpublished_Purchased_Products_Images(Website):

    @http.route([
        '/website/image/',
        '/website/image/<model>/<id>/<field>',
        '/website/image/<model>/<id>/<field>/<int:max_width>x<int:max_height>'
    ], auth="public", website=True)
    def website_image(self, model, id, field, max_width=None, max_height=None):
        """ Allows to display images for products with website_published=False
            if the requesting user already has them in his sale orders.
        """
        if model in ['product.product', 'product.template']:
            # Confirm = False to display images in cart
            purchased_products = util.get_digital_purchases(request.uid, confirmed=False)
            idsha = id.split('_')
            id = idsha[0]
            if int(id) in purchased_products:
                request.uid = SUPERUSER_ID

        return super(Website_Unpublished_Purchased_Products_Images, self).website_image(model, id, field, max_width, max_height)
