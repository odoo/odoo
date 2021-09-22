# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale
import json


class WebsiteSaleProductComparison(WebsiteSale):

    @http.route('/shop/compare', type='http', auth="public", website=True, sitemap=False)
    def product_compare(self, **post):
        values = {}
        product_ids = [int(i) for i in post.get('products', '').split(',') if i.isdigit()]
        if not product_ids:
            return request.redirect("/shop")
        # use search to check read access on each record/ids
        products = request.env['product.product'].search([('id', 'in', product_ids)])
        values['products'] = products.with_context(display_default_code=False)
        return request.render("website_sale_comparison.product_compare", values)

    @http.route(['/shop/get_product_data'], type='json', auth="public", website=True)
    def get_product_data(self, product_ids, cookies=None):
        ret = {}
        pricelist_context, pricelist = self._get_pricelist_context()
        prods = request.env['product.product'].with_context(pricelist_context, display_default_code=False).search([('id', 'in', product_ids)])

        if cookies is not None:
            ret['cookies'] = json.dumps(request.env['product.product'].search([('id', 'in', list(set(product_ids + cookies)))]).ids)

        prods.mapped('name')
        for prod in prods:
            ret[prod.id] = {
                'render': request.env['ir.ui.view']._render_template(
                    "website_sale_comparison.product_product",
                    {'product': prod, 'website': request.website}
                ),
                'product': dict(id=prod.id, name=prod.name, display_name=prod.display_name),
            }
        return ret
