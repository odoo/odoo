# -*- coding: utf-8 -*-

import openerp
from openerp.addons.web import http
from openerp.addons.web.http import request
from werkzeug.exceptions import NotFound
import urllib


class Ecommerce(http.Controller):

    @http.route(['/shop', '/shop/category/<cat_id>'], type='http', auth="db")
    def category(self, cat_id=0, offset=0):
        try:
            request.session.check_security()
            editable = True
            uid = request.session._uid
        except http.SessionExpiredException:
            editable = False
            uid = openerp.SUPERUSER_ID

        cat_id = cat_id and int(cat_id) or 0
        category_obj = request.registry.get('pos.category')
        product_obj = request.registry.get('product.product')
        category_ids = category_obj.search(request.cr, uid, [('parent_id', '=', False)])
        product_ids = product_obj.search(request.cr, uid, cat_id and [('pos_categ_id.id', 'child_of', cat_id)] or [(1, '=', 1)], limit=20, offset=offset)

        values = {
            'editable': editable,
            'request': request,
            'registry': request.registry,
            'cr': request.cr,
            'uid': uid,
            'current_category': cat_id,
            'categories': category_obj.browse(request.cr, uid, category_ids),
            'products': product_obj.browse(request.cr, uid, product_ids),
        }
        html = request.registry.get("ir.ui.view").render(request.cr, uid, "ecommerce.categories", values)
        return html

    @http.route(['/shop/category/<cat_id>/product/<product_id>', '/shop/product/<product_id>'], type='http', auth="db")
    def product(self, cat_id=0, product_id=0, offset=0):
        try:
            request.session.check_security()
            editable = True
            uid = request.session._uid
        except http.SessionExpiredException:
            editable = False
            uid = openerp.SUPERUSER_ID

        product_id = product_id and int(product_id) or 0
        category_obj = request.registry.get('pos.category')
        product_obj = request.registry.get('product.product')
        category_ids = category_obj.search(request.cr, uid, [('parent_id', '=', False)])

        values = {
            'editable': editable,
            'request': request,
            'registry': request.registry,
            'cr': request.cr,
            'uid': uid,
            'categories': category_obj.browse(request.cr, uid, category_ids),
            'product': product_obj.browse(request.cr, uid, product_id),
        }
        html = request.registry.get("ir.ui.view").render(request.cr, uid, "ecommerce.product", values)
        return html


# vim:expandtab:tabstop=4:softtabstop=4:shiftwidth=4:
