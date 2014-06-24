# -*- coding: utf-8 -*-

from openerp import SUPERUSER_ID
from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp.addons.website.models.website import slug
from openerp.addons.website_sale.controllers.main import QueryURL
from openerp.addons.website_sale.controllers.main import website_sale

class website_sale_options(website_sale):

    def product(self, product, category='', search='', **kwargs):
        r = super(website_sale_options, self)

        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
        template_obj = pool['product.template']

        optional_product_ids = []
        for p in product.optional_product_ids:
            ctx = dict(context, active_id=p.id)
            optional_product_ids.append(template_obj.browse(cr, uid, p.id, context=ctx))

        r.qcontext['optional_product_ids'] = optional_product_ids
        return r

    def cart_update(self, product_id, add_qty=1, set_qty=0, goto_shop=None, **kw):
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
        order = request.website.sale_get_order(force_create=1)
        prod_obj = pool['product.product']

        optional_product_ids = []
        for k, v in kw.items():
            if "optional-product-" in k and int(kw.get(k.replace("product", "quantity"))):
                optional_product_ids.append(int(v))
        if add_qty or set_qty:
            line_id, quantity = order._cart_update(product_id=int(product_id),
                add_qty=int(add_qty), set_qty=int(set_qty),
                optional_product_ids=optional_product_ids)
        # options have all time the same quantity
        for option_id in optional_product_ids:
            order._cart_update(product_id=option_id, set_qty=value.get('quantity'), linked_line_id=value.get('line_id'))

        if goto_shop:
            return request.redirect("/shop/product/%s" % slug(prod_obj.browse(cr, uid, product_id).product_tmpl_id))
        else:
            return request.redirect("/shop/cart")
