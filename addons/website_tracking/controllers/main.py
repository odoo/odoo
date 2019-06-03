# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json

from odoo import http

from odoo.addons.auth_signup.controllers.main import AuthSignupHome as Home
from odoo.http import request
from odoo.osv import expression

class SaleAuthLogin(Home):
    @http.route()
    def web_auth_signup(self, *args, **kwargs):
        response = super(SaleAuthLogin, self).web_auth_signup(*args, **kwargs)
        user = request.env['res.users'].sudo().search([('login', '=', kwargs.get('login'))])
        if 'error' not in response.qcontext and request.httprequest.method == 'POST':
            recently_viewed = json.loads(request.httprequest.cookies.get('recently_viewed_product_ids', "[]"))[:15]
            if recently_viewed:
                product_views = []
                for template_id, product_id in recently_viewed[::-1]:
                    product_views.append({'res_partner_id': user.partner_id.id, 'product_template_id': template_id, 'last_product_id': product_id})
                request.env['product.view'].create(product_views)
                response.delete_cookie('recently_viewed_product_ids')
        return response

class WebsiteTracking(http.Controller):
    # --------------------------------------------------------------------------
    # Products Recently Viewed
    # --------------------------------------------------------------------------

    @http.route('/shop/products/recently_viewed', type='json', auth='public', website=True)
    def products_recently_viewed(self, excluded_template_ids=[], **kwargs):
        """
        Returns list of recently viewed products according to current user and product options
        """

        excluded_product_ids = []
        current_sale_order = request.session.get('sale_order_id')
        if current_sale_order:
            order_lines = request.env['sale.order.line'].sudo().search([('order_id', '=', current_sale_order)])
            excluded_product_ids = order_lines.mapped('product_id.id')

        partner = request.env.user.partner_id
        if not request.env.user._is_public():
            domain = [('res_partner_id', '=', partner.id)]
            if excluded_template_ids:
                domain = expression.AND([domain, [('product_template_id', 'not in', excluded_template_ids)]])
            if excluded_product_ids:
                domain = expression.AND([domain, [('last_product_id', 'not in', excluded_product_ids)]])

            products = request.env['product.view'].search(domain, limit=10, order='write_date desc').mapped('last_product_id')
        else:
            recently_viewed = json.loads(request.httprequest.cookies.get('recently_viewed_product_ids', "[]"))[:15]
            product_ids = [product_id for template_id, product_id in recently_viewed if template_id not in excluded_template_ids and product_id not in excluded_product_ids]
            products = request.env['product.product'].browse(product_ids[:10])

        fields = ['id', 'name', 'website_url']
        res = {
            'products': products.read(fields),
        }

        FieldMonetary = request.env['ir.qweb.field.monetary']
        monetary_options = {
            'display_currency': request.website.get_current_pricelist().currency_id,
        }
        for res_product, product in zip(res['products'], products):
            combination_info = product._get_combination_info_variant()
            res_product.update(combination_info)
            res_product['list_price'] = FieldMonetary.value_to_html(res_product['list_price'], monetary_options)
            res_product['price'] = FieldMonetary.value_to_html(res_product['price'], monetary_options)

        return res

    @http.route('/shop/products/recently_viewed_update', type='json', auth='public', website=True)
    def products_recently_viewed_update(self, product_template_id, product_id, **kwargs):

        partner = request.env.user.partner_id
        if not request.env.user._is_public():
            request.env['product.view'].create_productview({'res_partner_id': partner.id, 'product_template_id': product_template_id, 'last_product_id': product_id})
        else:
            recently_viewed = json.loads(request.httprequest.cookies.get('recently_viewed_product_ids', "[]"))[:15]
            for idx, values in enumerate(recently_viewed):
                if values[0] == product_template_id:
                    del recently_viewed[idx]
                    break
            recently_viewed.insert(0, (product_template_id, product_id))

            return {'recently_viewed_product_ids': json.dumps(recently_viewed[:15])}
