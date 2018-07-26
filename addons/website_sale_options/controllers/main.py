# -*- coding: utf-8 -*-

from openerp import SUPERUSER_ID
from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp.addons.website_sale.controllers.main import website_sale

class website_sale_options(website_sale):

    @http.route(['/shop/product/<model("product.template"):product>'], type='http', auth="public", website=True)
    def product(self, product, category='', search='', **kwargs):
        r = super(website_sale_options, self).product(product, category, search, **kwargs)

        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
        template_obj = pool['product.template']

        optional_product_ids = []
        for p in product.optional_product_ids:
            ctx = dict(context, active_id=p.id)
            optional_product_ids.append(template_obj.browse(cr, uid, p.id, context=ctx))

        r.qcontext['optional_product_ids'] = optional_product_ids
        return r

    @http.route(['/shop/cart/update_option'], type='http', auth="public", methods=['POST'], website=True, multilang=False)
    def cart_options_update_json(self, product_id, add_qty=1, set_qty=0, goto_shop=None, lang=None, **kw):
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
        if lang:
            context = dict(context, lang=lang)
            request.website = request.website.with_context(context)

        order = request.website.sale_get_order(force_create=1)
        product = pool['product.product'].browse(cr, uid, int(product_id), context=context)


        option_ids = [p.id for tmpl in product.optional_product_ids for p in tmpl.product_variant_ids]
        optional_product_ids = []
        for k, v in kw.items():
            if "optional-product-" in k and int(kw.get(k.replace("product", "add"))) and int(v) in option_ids:
                optional_product_ids.append(int(v))

        value = {}
        if add_qty or set_qty:
            value = order._cart_update(product_id=int(product_id),
                add_qty=add_qty, set_qty=set_qty,
                optional_product_ids=optional_product_ids)

        # options have all time the same quantity
        for option_id in optional_product_ids:
            order._cart_update(product_id=option_id,
                set_qty=value.get('quantity'),
                linked_line_id=value.get('line_id'))

        return str(order.cart_quantity)

    @http.route(['/shop/modal'], type='json', auth="public", methods=['POST'], website=True)
    def modal(self, product_id, **kw):
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
        pricelist = self.get_pricelist()
        quantity = kw['kwargs']['context']['quantity']
        if not context.get('pricelist'):
            context['pricelist'] = int(pricelist)

        website_context = kw.get('kwargs', {}).get('context', {})
        context = dict(context or {}, **website_context)
        from_currency = pool['res.users'].browse(cr, uid, uid, context=context).company_id.currency_id
        to_currency = pricelist.currency_id
        compute_currency = lambda price: pool['res.currency']._compute(cr, uid, from_currency, to_currency, price, context=context)
        product = pool['product.product'].browse(cr, uid, int(product_id), context=context)
        request.website = request.website.with_context(context)

        main_product_attr_ids = self.get_attribute_value_ids(product)
        for variant in main_product_attr_ids:
            if variant[0] == product.id:
                # We indeed need a list of lists (even with only 1 element)
                main_product_attr_ids = [variant]
                break

        return request.website._render("website_sale_options.modal", {
                'product': product,
                'compute_currency': compute_currency,
                'get_attribute_value_ids': self.get_attribute_value_ids,
                'main_product_attr_ids': main_product_attr_ids,
            })
