# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale
import json
from collections import OrderedDict


class WebsiteSaleProductComparison(WebsiteSale):

    @http.route('/shop/compare/', type='http', auth="public", website=True)
    def product_compare(self, **post):
        values = {}
        product_ids = [int(i) for i in post.get('products', '').split(',') if i.isdigit()]
        if not product_ids:
            return request.redirect("/shop")
        # use search to check read access on each record/ids
        products = request.env['product.product'].search([('id', 'in', product_ids)])
        values['products'] = products.with_context(display_default_code=False)

        res = OrderedDict()
        attrs = products.mapped('attribute_line_ids.attribute_id').filtered(lambda x: x.create_variant)
        for attr in attrs.sorted(lambda att: (att.category_id.sequence, att.sequence)):
            cat_name = attr.category_id.name or _('Uncategorized')
            res.setdefault(cat_name, OrderedDict()).setdefault(attr.name, [' - '] * len(products))
        for num, product in enumerate(products):
            for var in product.attribute_line_ids.filtered(lambda x: x.attribute_id.create_variant):
                cat_name = var.attribute_id.category_id.name or _('Uncategorized')
                att_name = var.attribute_id.name
                val = product.attribute_value_ids.filtered(lambda x: x.attribute_id == var.attribute_id)
                if val:
                    res[cat_name][att_name][num] = val[0].name
        values['specs'] = res
        values['compute_currency'] = self._get_compute_currency_and_context()[0]
        return request.render("website_sale_comparison.product_compare", values)

    @http.route(['/shop/get_product_data'], type='json', auth="public", website=True)
    def get_product_data(self, product_ids, cookies=None):
        ret = {}
        compute_currency, pricelist_context, _ = self._get_compute_currency_and_context()
        prods = request.env['product.product'].with_context(pricelist_context, display_default_code=False).search([('id', 'in', product_ids)])

        if cookies is not None:
            ret['cookies'] = json.dumps(request.env['product.product'].search([('id', 'in', list(set(product_ids + cookies)))]).ids)

        prods.mapped('name')
        for prod in prods:
            ret[prod.id] = {
                'render': request.env['ir.ui.view'].render_template(
                    "website_sale_comparison.product_product",
                    {'compute_currency': compute_currency, 'product': prod, 'website': request.website}
                ),
                'product': dict(id=prod.id, name=prod.name, display_name=prod.display_name),
            }
        return ret
