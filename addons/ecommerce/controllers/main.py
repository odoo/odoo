# -*- coding: utf-8 -*-

import openerp
import simplejson
from openerp.addons.web import http
from openerp.addons.web.http import request
from werkzeug.exceptions import NotFound
import urllib


class Ecommerce(http.Controller):

    def get_cr_uid(self):
        cr = request.cr
        try:
            request.session.check_security()
            uid = request.session._uid
        except http.SessionExpiredException:
            uid = openerp.SUPERUSER_ID

        partner_id = request.session.variables.get('ecommerce_partner_id', False)
        if not partner_id and uid != 1:
            partner_id = request.registry.get('res.users').browse(cr, uid, uid).partner_id.id
            request.session.variables['ecommerce_partner_id'] = partner_id

        return (cr, uid, partner_id)

    def get_values(self):
        cr, uid, partner_id = self.get_cr_uid()
        order_obj = request.registry.get('sale.order')
        category_obj = request.registry.get('pos.category')
        context = {}

        order_id = request.session.variables.get('ecommerce')
        # check if order allready exists
        try:
            order_obj.browse(cr, uid, order_id).pricelist_id
        except:
            order_id = None

        if not order_id:
            fields = [k for k, v in order_obj._columns.items()]
            order_value = order_obj.default_get(cr, uid, fields, context=context)
            order_value['partner_id'] = partner_id or request.registry.get('res.users').browse(cr, uid, uid).partner_id.id
            order_value.update(order_obj.onchange_partner_id(cr, uid, [], uid, context=context)['value'])
            order_id = order_obj.create(cr, uid, order_value, context=context)
            request.session.variables['ecommerce'] = order_id

        category_ids = category_obj.search(cr, uid, [('parent_id', '=', False)])

        values = {
            'temp': 0,
            'request': request,
            'registry': request.registry,
            'cr': cr,
            'uid': uid,
            'order': order_obj.browse(cr, uid, order_id),
            'categories': category_obj.browse(cr, uid, category_ids),
        }
        return values

    @http.route(['/shop', '/shop/category/<cat_id>'], type='http', auth="db")
    def category(self, cat_id=0, offset=0):
        values = self.get_values()
        cr, uid, partner_id = self.get_cr_uid()

        cat_id = cat_id and int(cat_id) or 0
        category_obj = request.registry.get('pos.category')
        product_obj = request.registry.get('product.product')
        category_ids = category_obj.search(cr, uid, [('parent_id', '=', False)])
        product_ids = product_obj.search(cr, uid, cat_id and [('pos_categ_id.id', 'child_of', cat_id)] or [(1, '=', 1)], limit=20, offset=offset)

        values.update({
            'current_category': cat_id,
            'categories': category_obj.browse(cr, uid, category_ids),
            'products': product_obj.browse(cr, uid, product_ids),
        })
        html = request.registry.get("ir.ui.view").render(cr, uid, "ecommerce.page", values)
        return html

    @http.route(['/shop/product/<product_id>'], type='http', auth="db")
    def product(self, cat_id=0, product_id=0, offset=0):
        values = self.get_values()
        cr, uid, partner_id = self.get_cr_uid()

        product_id = product_id and int(product_id) or 0
        product_obj = request.registry.get('product.product')

        values.update({
            'product': product_obj.browse(cr, uid, product_id),
        })
        html = request.registry.get("ir.ui.view").render(cr, uid, "ecommerce.product", values)
        return html

    @http.route(['/shop/my_cart'], type='http', auth="db")
    def my_cart(self, offset=0):
        cr, uid, partner_id = self.get_cr_uid()
        html = request.registry.get("ir.ui.view").render(cr, uid, "ecommerce.my_cart", self.get_values())
        return html

    @http.route(['/shop/add_cart'], type='http', auth="db")
    def add_cart(self, product_id=0, remove=False):
        cr, uid, partner_id = self.get_cr_uid()
        values = self.get_values()
        context = {}

        order_obj = request.registry.get('sale.order')
        order_line_obj = request.registry.get('sale.order.line')

        product_id = product_id and int(product_id) or 0
        order = values['order']

        quantity = 0

        # values initialisation
        order_line_ids = order_line_obj.search(cr, uid, [('order_id', '=', order.id), ('product_id', '=', product_id)], context=context)
        values = {}
        if order_line_ids:
            order_line = order_line_obj.read(cr, uid, order_line_ids, [], context=context)[0]
            quantity = order_line['product_uom_qty'] + (remove and -1 or 1)
            if quantity <= 0:
                order_line_obj.unlink(cr, uid, order_line_ids, context=context)
        else:
            fields = [k for k, v in order_line_obj._columns.items()]
            values = order_line_obj.default_get(cr, uid, fields, context=context)
            quantity = 1
        values['product_uom_qty'] = quantity
        values['product_id'] = product_id
        values['order_id'] = order.id

        # change and record value
        if quantity:
            pricelist_id = order.pricelist_id and order.pricelist_id.id or False
            values.update(order_line_obj.product_id_change(cr, uid, [], pricelist_id, product_id, partner_id=partner_id, context=context)['value'])
            if order_line_ids:
                order_line_obj.write(cr, uid, order_line_ids, values, context=context)
            else:
                order_line_id = order_line_obj.create(cr, uid, values, context=context)
                order.write({'order_line': [(4, order_line_id)]}, context=context)

        html = request.registry.get("ir.ui.view").render(cr, uid, "ecommerce.total", self.get_values())

        return simplejson.dumps({"quantity": quantity, "totalHTML": html})

    @http.route(['/shop/remove_cart'], type='http', auth="db")
    def remove_cart(self, product_id=0):
        return self.add_cart(product_id=product_id, remove=True)

    @http.route(['/shop/confirm_cart'], type='http', auth="db")
    def confirm_cart(self, *arg, **post):
        cr, uid, partner_id = self.get_cr_uid()
        values = self.get_values()
        if post:
            print post

        {'city': u'regfs', 'name': u'Demo User', 'zip': u'5432534', 'street2': u'', 'country_id': u'gfgfdg', 'phone': u'4523545', 'state': u'fgdgsfgdf', 'street': u'fdsfdsffdsfqsdf 54', 'email': u'demo@example.com'}

        values['partner'] = partner_id and request.registry.get('res.users').browse(cr, uid, partner_id) or False

        html = request.registry.get("ir.ui.view").render(cr, uid, "ecommerce.customer", values)
        return html

# vim:expandtab:tabstop=4:softtabstop=4:shiftwidth=4:
