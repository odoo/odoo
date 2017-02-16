# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale
import json


class WebsiteSaleProductComparison(WebsiteSale):

    def get_compute_currency_and_context(self):
        pricelist_context = dict(request.env.context)
        pricelist = False
        if not pricelist_context.get('pricelist'):
            pricelist = request.website.get_current_pricelist()
            pricelist_context['pricelist'] = pricelist.id
        else:
            pricelist = request.env['product.pricelist'].browse(pricelist_context['pricelist'])

        from_currency = request.env.user.company_id.currency_id
        to_currency = pricelist.currency_id
        compute_currency = lambda price: from_currency.compute(price, to_currency)
        return compute_currency, pricelist_context

    @http.route('/shop/compare/', type='http', auth="public", website=True)
    def product_compare(self, **post):
        values = {}
        if post.get('products'):
            product_ids = [int(i) for i in post.get('products').split(',') if i.isdigit()]
            # use search to check read access on each record/ids
            products = request.env['product.product'].search([('id', 'in', product_ids)]).exists()
            values['products'] = products

            res = {}
            for num, product in enumerate(products):
                for var in product.attribute_line_ids:
                    cat_name = var.attribute_id.category_id.name
                    att_name = var.attribute_id.name
                    res.setdefault(cat_name, {})
                    if not res[cat_name].get(att_name):
                        res[cat_name][att_name] = [' - '] * len(products)
                    val = product.attribute_value_ids.filtered(lambda x: x.attribute_id == var.attribute_id)
                    res[cat_name][att_name][num] = val and val[0].name or ' - '
            values['specs'] = res

        values['compute_currency'], pricelist_context = self.get_compute_currency_and_context()
        return request.render("website_product_comparison.product_compare", values)

    @http.route(['/shop/get_product_data'], type='json', auth="public", website=True)
    def get_product_data(self, product_ids):
        compute_currency, pricelist_context = self.get_compute_currency_and_context()
        prods = request.env['product.product'].with_context(pricelist_context).browse(product_ids)
        ret = {}
        for prod in prods:
            ret[prod.id] = {
                'render': request.env['ir.ui.view'].render_template(
                    "website_product_comparison.product_product",
                    {'compute_currency': compute_currency, 'product': prod, 'website': request.website}
                ),
                'product': prod.read(['name', 'id', 'public_categ_ids'])[0]
            }
        return ret

    @http.route(['/shop/compare_active'], type='json', auth="public", website=True)
    def check_comparator_active(self, **kw):
        return request.env.ref('website_product_comparison.add_to_compare').active

    @http.route(['/shop/wishlist_active'], type='json', auth="public", website=True)
    def check_wishlist_active(self, **kw):
        return request.env.ref('website_product_comparison.add_to_wishlist').active

    @http.route(['/shop/wishlist/add'], type='json', auth="user", website=True)
    def add_to_wishlist(self, product_id, price=False, **kw):
        if not price:
            compute_currency, pricelist_context = self.get_compute_currency_and_context()
            p = request.env['product.product'].with_context(pricelist_context).browse(product_id)
            price = p.website_price

        request.env['product.wishlist']._add_to_wishlist(
            request.env.user.partner_id.id,
            request.website.get_current_pricelist().id,
            request.website.get_current_pricelist().currency_id.id,
            request.website.id,
            price,
            product_id
        )
        return True

    @http.route(['/shop/wishlist/rm'], type='json', auth="user", website=True)
    def rm_from_wishlist(self, wish, **kw):
        request.env['product.wishlist'].browse(wish).unlink()
        return True

    @http.route(['/shop/wishlist'], type='http', auth="user", website=True)
    def get_wishlist(self, count=False, **kw):
        values = request.env['product.wishlist'].search([('partner_id', '=', request.env.user.partner_id.id)])
        if count:
            return request.make_response(json.dumps(values.mapped('product_id').ids))

        if len(values) == 0:
            return request.redirect("/shop")

        return request.render("website_product_comparison.product_wishlist", dict(wishes=values))
