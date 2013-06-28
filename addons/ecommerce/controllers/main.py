# -*- coding: utf-8 -*-

import openerp
from openerp.addons.web import http
from openerp.addons.web.http import request
from werkzeug.exceptions import NotFound
import urllib


def get_html_head():
    head = ['<link href="https://www.openerp.com/saas_master/static/site_new/fonts/lato/stylesheet.css" rel="stylesheet" type="text/css">']
    return "\n        ".join(head)


class Ecommerce(http.Controller):

    def to_url(self, paths):
        url = ""
        for path in paths:
            if isinstance(path, (int, long)):
                path = "%s" % path
            url = "%s/%s" % (url, urllib.quote_plus(path.encode('utf-8')))
        return url

    def path_category(self, category_browse):
        paths = []
        cat = category_browse
        while cat.parent_id:
            cat = cat.parent_id
            paths.append(cat.name)
        paths.append('shop')
        paths.reverse()
        return paths

    def render_product(self, cr, uid, product_id):
        product_obj = request.registry.get('product.product')
        product = product_obj.read(cr, uid, product_id, [])
        if not product:
            raise NotFound()
        content = request.registry.get("ir.ui.view").render(cr, uid, 'ecommerce.product', product)
        return content

    # select main category or sub categories
    def render_product_list(self, cr, uid, category_id=None, search="", offset=0):
        product_obj = request.registry.get('product.product')
        product_ids = product_obj.search(cr, uid, category_id and [('pos_categ_id.id', 'child_of', category_id)] or [(1, '=', 1)], limit=20, offset=offset)

        products = []
        for prod in product_obj.browse(cr, uid, product_ids):
            paths = self.path_category(prod.pos_categ_id)
            paths += [prod.pos_categ_id.name, prod.id, prod.name]
            product = prod.read(['image_small', 'image_medium', 'list_price', 'description_sale', 'name'])[0]
            product['url'] = self.to_url(paths)
            products.append(product)

        return request.registry.get("ir.ui.view").render(cr, uid, 'ecommerce.product_list', {'products': products, 'search': search})

    def render_category_list(self, cr, uid, category_id=None):
        category_obj = request.registry.get('pos.category')
        category_ids = category_obj.search(cr, uid, [('parent_id', '=', False)])

        def get_category_data(category):
            paths = self.path_category(category)
            paths.append(category.name)
            child_ids = []
            for child in category.child_id:
                child_ids.append(get_category_data(child))
            return {
                'name': category.name,
                'url': self.to_url(paths),
                'selected': category['id'] == category_id,
                'child_ids': child_ids,
                }

        categories = []
        for category in category_obj.browse(cr, uid, category_ids):
            categories.append(get_category_data(category))

        return request.registry.get("ir.ui.view").render(cr, uid, 'ecommerce.categories', {'categories': categories})

    @http.route(['/shop', '/shop/', '/shop/<path:path>'], type='http', auth="db")
    def shop(self, path=None, offset=0):
        category_obj = request.registry.get('pos.category')

        cr = request.cr
        uid = request.session._uid
        paths = [urllib.unquote_plus(path) for path in path and path.strip('/').split('/') or []]

        product_id = None
        category_id = None
        if paths:
            if len(paths) >= 2 and paths[-2].isdigit():
                product_id = int(paths[-2])
            if product_id:
                category = len(paths) >= 3 and paths[-3] or None
            else:
                category = paths[-1]
            if category:
                category_id = category_obj.search(cr, uid, [('name', 'ilike', category)])[0]

        content = request.registry.get("ir.ui.view").render(cr, uid, 'ecommerce.product_container', {})

        products = product_id and \
            self.render_product(cr, uid, product_id) or \
            self.render_product_list(cr, uid, category_id, "trucmuch", offset=offset)
        content = content.replace('<div class="placeholder_product"/>', products)

        categories = self.render_category_list(cr, uid, category_id)
        content = content.replace('<div class="placeholder_category"/>', categories)

        html = open(openerp.addons.get_module_resource('ecommerce', 'views', 'homepage.html'), 'rb').read().decode('utf8')
        html = html.replace('<!--placeholder_container-->', content)
        html = html.replace('<!--editable-->', get_html_head())

        return html


# vim:expandtab:tabstop=4:softtabstop=4:shiftwidth=4:
