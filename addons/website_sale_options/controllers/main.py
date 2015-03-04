# -*- coding: utf-8 -*-

from openerp import http
from openerp.http import request
from openerp.addons.website_sale.controllers.main import WebsiteSale


class WebsiteSaleOptions(WebsiteSale):

    @http.route(['/shop/product/<model("product.template"):product>'], type='http', auth="public", website=True)
    def product(self, product, category='', search='', **kwargs):
        r = super(WebsiteSaleOptions, self).product(product, category, search, **kwargs)

        optional_product_ids = []
        for p in product.optional_product_ids:
            optional_product_ids.append(request.env['product.template'].with_context(active_id=p.id).browse(p.id))
        r.qcontext['optional_product_ids'] = optional_product_ids
        return r

    @http.route(['/shop/cart/update_option'], type='http', auth="public", methods=['POST'], website=True)
    def cart_options_update_json(self, product_id, add_qty=1, set_qty=0, goto_shop=None, lang=None, **kw):
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
        if lang:
            context = dict(context, lang=lang)
            request.website = request.website.with_context(context)

        order = request.website.sale_get_order(force_create=1)
        product = request.env['product.product'].with_context(context).browse(int(product_id))

        options = product.optional_product_ids.mapped('product_variant_ids')
        optional_product_ids = []
        for k, v in kw.items():
            if "optional-product-" in k and int(kw.get(k.replace("product", "add"))) and int(v) in options.ids:
                optional_product_ids.append(int(v))

        value = {}
        if add_qty or set_qty:
            value = order._cart_update(product_id=int(product_id),
                add_qty=int(add_qty), set_qty=int(set_qty),
                optional_product_ids=optional_product_ids)

        # options have all time the same quantity
        for option_id in optional_product_ids:
            order._cart_update(product_id=option_id,
                set_qty=value.get('quantity'),
                linked_line_id=value.get('line_id'))

        return str(order.cart_quantity)

    @http.route(['/shop/modal'], type='json', auth="public", methods=['POST'], website=True)
    def modal(self, product_id, **kw):
        pricelist = self.get_pricelist()
        context = request.context
        if not context.get('pricelist'):
            context['pricelist'] = int(pricelist)

        website_context = kw.get('kwargs', {}).get('context', {})
        context = dict(context or {}, **website_context)
        from_currency = request.env['product.price.type'].search([('field', '=', 'list_price')], limit=1)
        to_currency = pricelist.currency_id
        compute_currency = lambda price: request.env['res.currency']._compute(from_currency, to_currency, price)
        product = request.env['product.product'].with_context(context).browse(int(product_id))
        request.website = request.website.with_context(context)

        return request.website._render("website_sale_options.modal", {
                'product': product,
                'compute_currency': compute_currency,
                'get_attribute_value_ids': self.get_attribute_value_ids,
            })
