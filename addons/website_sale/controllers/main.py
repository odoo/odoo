# -*- coding: utf-8 -*-

import simplejson
from openerp.addons.web import http
from openerp.addons.website import website
from openerp.addons.web.http import request


class Ecommerce(http.Controller):

    def get_categories(self):
        category_obj = request.registry.get('pos.category')
        category_ids = category_obj.search(request.cr, request.uid, [('parent_id', '=', False)])
        return category_obj.browse(request.cr, request.uid, category_ids)

    def get_current_order(self):
        order = self.get_order(request.httprequest.session.get('ecommerce_order'))
        request.httprequest.session['ecommerce_order'] = order.id
        return order

    def get_order(self, order_id=None):

        order_obj = request.registry.get('sale.order')
        # check if order allready exists
        if order_id:
            try:
                order_obj.browse(request.cr, request.uid, order_id).pricelist_id
            except:
                order_id = None
        if not order_id:
            fields = [k for k, v in order_obj._columns.items()]
            order_value = order_obj.default_get(request.cr, request.uid, fields)
            order_value['partner_id'] = partner_id or request.registry.get('res.users').browse(request.cr, request.uid, request.uid).partner_id.id
            order_value.update(order_obj.onchange_partner_id(request.cr, request.uid, [], request.uid, context={})['value'])
            order_id = order_obj.create(request.cr, request.uid, order_value)
        return order_obj.browse(request.cr, request.uid, order_id)

    def render(self, template, values={}):
        _values = {
            'order': self.get_current_order(),
            'categories': self.get_categories(),
        }
        _values.update(values)
        return website.render(template, _values)

    def recommended_product(self, my_pids):
        if not my_pids:
            return []
        
        my_pids = str(my_pids)[1:-1]
        product_ids = []
        query = """
            SELECT      sol.product_id
            FROM        sale_order_line as my
            LEFT JOIN   sale_order_line as sol
            ON          sol.order_id = my.order_id
            WHERE       my.product_id in (%s)
            AND         sol.product_id not in (%s)
            GROUP BY    sol.product_id
            ORDER BY    COUNT(sol.order_id) DESC
            LIMIT 8
        """ % (my_pids, my_pids)
        request.cr.execute(query)
        for p in request.cr.fetchall():
            product_ids.append(p[0])
        return request.registry.get('product.product').browse(request.cr, request.uid, product_ids)

    @http.route(['/shop', '/shop/category/<cat_id>'], type='http', auth="admin")
    def category(self, cat_id=0, offset=0, **post):

        domain = []
        if post.get("search"):
            domain += ['|', '|', ('name', 'ilike', "%%%s%%" % post.get("search")), ('desrequest.cription', 'ilike', "%%%s%%" % post.get("search")), ('pos_categ_id.name', 'ilike', "%%%s%%" % post.get("search"))]
        if cat_id:
            cat_id = cat_id and int(cat_id) or 0
            domain = [('pos_categ_id.id', 'child_of', cat_id)] + domain

        product_obj = request.registry.get('product.product')
        product_ids = product_obj.search(request.cr, request.uid, domain or [(1, '=', 1)], limit=20, offset=offset)

        values = {
            'current_category': cat_id,
            'products': product_obj.browse(request.cr, request.uid, product_ids),
            'search': post.get("search"),
        }
        html = self.render("website_sale.products", values)
        return html

    @http.route(['/shop/product/<product_id>'], type='http', auth="admin")
    def product(self, cat_id=0, product_id=0):
        order = self.get_current_order()

        product_id = product_id and int(product_id) or 0
        product_obj = request.registry.get('product.product')

        line = [line for line in order.order_line if line.product_id.id == product_id]
        quantity = line and int(line[0].product_uom_qty) or 0

        values = {
            'product': product_obj.browse(request.cr, request.uid, product_id),
            'quantity': quantity,
            'recommended_products': self.recommended_product([product_id]),
        }
        html = self.render("website_sale.product", values)
        return html

    @http.route(['/shop/mycart'], type='http', auth="admin")
    def mycart(self, **post):
        order = self.get_current_order()

        if post.get('code'):
            pricelist_obj = request.registry.get('product.pricelist')
            pricelist_ids = pricelist_obj.search(request.cr, request.uid, [('code', '=', post.get('code'))])
            if pricelist_ids:
                order.write({'pricelist_id': pricelist_ids[0]})

        my_pids = [line.product_id.id for line in order.order_line]
        values= {"recommended_products": self.recommended_product(my_pids)}

        html = self.render("website_sale.mycart", values)
        return html

    @http.route(['/shop/add_cart'], type='http', auth="admin")
    def add_cart(self, product_id=0, remove=False):
        
        context = {}

        order_obj = request.registry.get('sale.order')
        order_line_obj = request.registry.get('sale.order.line')
        user_obj = request.registry.get('res.users')

        product_id = product_id and int(product_id) or 0
        order = self.get_current_order()

        quantity = 0

        # values initialisation
        order_line_ids = order_line_obj.search(request.cr, request.uid, [('order_id', '=', order.id), ('product_id', '=', product_id)], context=context)
        values = {}
        if order_line_ids:
            order_line = order_line_obj.read(request.cr, request.uid, order_line_ids, [], context=context)[0]
            quantity = order_line['product_uom_qty'] + (remove and -1 or 1)
            if quantity <= 0:
                order_line_obj.unlink(request.cr, request.uid, order_line_ids, context=context)
        else:
            fields = [k for k, v in order_line_obj._columns.items()]
            values = order_line_obj.default_get(request.cr, request.uid, fields, context=context)
            quantity = 1
        values['product_uom_qty'] = quantity
        values['product_id'] = product_id
        values['order_id'] = order.id

        # change and record value
        if quantity:
            pricelist_id = order.pricelist_id and order.pricelist_id.id or False
            values.update(order_line_obj.product_id_change(request.cr, request.uid, [], pricelist_id, product_id,
                partner_id=user_obj.browse(request.cr, request.uid, request.uid).partner_id.id,
                context=context)['value'])
            if order_line_ids:
                order_line_obj.write(request.cr, request.uid, order_line_ids, values, context=context)
            else:
                order_line_id = order_line_obj.create(request.cr, request.uid, values, context=context)
                order.write({'order_line': [(4, order_line_id)]}, context=context)

        html = self.render("website_sale.total", self.get_values())

        return simplejson.dumps({"quantity": quantity, "totalHTML": html})

    @http.route(['/shop/remove_cart'], type='http', auth="admin")
    def remove_cart(self, product_id=0):
        return self.add_cart(product_id=product_id, remove=True)

    @http.route(['/shop/checkout'], type='http', auth="admin")
    def checkout(self, **post):
        order = self.get_current_order()

        if order.state != 'draft':
            return self.confirmed(**post)
        if not order.order_line:
            return self.mycart(**post)

        partner_obj = request.registry.get('res.partner')
        user_obj = request.registry.get('res.users')
        country_obj = request.registry.get('res.country')
        country_state_obj = request.registry.get('res.country.state')
        payment_obj = request.registry.get('portal.payment.acquirer')

        values = {'partner': False}

        if request.uid != request.public_uid:
            values['partner'] = partner_obj.browse(request.cr, request.uid, partner_id)
            shipping_ids = partner_obj.search(request.cr, request.uid, [("parent_id", "=", partner_id), ('type', "=", 'delivery')])
            values['shipping'] = None
            if shipping_ids:
                values['shipping'] = partner_obj.browse(request.cr, request.uid, shipping_ids[0])

        values['countries'] = country_obj.browse(request.cr, request.uid, country_obj.search(request.cr, request.uid, [(1, "=", 1)]))
        values['states'] = country_state_obj.browse(request.cr, request.uid, country_state_obj.search(request.cr, request.uid, [(1, "=", 1)]))

        payment_ids = payment_obj.search(request.cr, request.uid, [('visible', '=', True)])
        values['payments'] = payment_obj.browse(request.cr, request.uid, payment_ids)
        for payment in values['payments']:
            content = payment_obj.render(request.cr, request.uid, payment.id, order, order.name, order.pricelist_id.currency_id, order.amount_total)
            payment._content = content

        return self.render("website_sale.checkout", values)

    @http.route(['/shop/confirm_order'], type='http', auth="admin")
    def confirm_order(self, **post):
        order = self.get_current_order()
        
        json = {'error': [], 'validation': False}
        partner_obj = request.registry.get('res.partner')
        user_obj = request.registry.get('res.users')

        if order.state != 'draft':
            json['validation'] = True
            return json
        if not order.order_line:
            json['error'].append("empty_cart")
            return json

        # check values
        required_field = ['phone', 'zip', 'email', 'street', 'city', 'name', 'country_id']
        for key in required_field:
            if not post.get(key):
                json['error'].append(key)
            if 'shipping_name' in post and key != 'email' and not post.get("shipping_%s" % key):
                json['error'].append("shipping_%s" % key)
        if json['error']:
            return simplejson.dumps(json)

        # search or create company
        company_id = None
        if post['company']:
            company_ids = partner_obj.search(request.cr, request.uid, [("name", "ilike", post['company']), ('is_company', '=', True)])
            company_id = company_ids and company_ids[0] or None
            if not company_id:
                company_id = partner_obj.create(request.cr, request.uid, {'name': post['company'], 'is_company': True})

        partner_value = {
            'fax': post['fax'],
            'phone': post['phone'],
            'zip': post['zip'],
            'email': post['email'],
            'street': post['street'],
            'city': post['city'],
            'name': post['name'],
            'parent_id': company_id,
            'country_id': post['country_id'],
            'state_id': post['state_id'],
        }
        if request.uid != request.public_uid:
            partner_id = user_obj.browse(request.cr, request.uid, request.uid).partner_id.id
            partner_obj.write(request.cr, request.uid, [partner_id], partner_value)
        else:
            partner_id = partner_obj.create(request.cr, 1, partner_value)

        shipping_id = None
        if 'shipping_name' in post:
            shipping_value = {
                'fax': post['shipping_fax'],
                'phone': post['shipping_phone'],
                'zip': post['shipping_zip'],
                'street': post['shipping_street'],
                'city': post['shipping_city'],
                'name': post['shipping_name'],
                'type': 'delivery',
                'parent_id': partner_id,
                'country_id': post['shipping_country_id'],
                'state_id': post['shipping_state_id'],
            }
            domain = [(key, '_id' in key and '=' or 'ilike', '_id' in key and int(value) or value)
                for key, value in shipping_value.items() if key in required_field + ["type", "parent_id"]]
            shipping_ids = partner_obj.search(request.cr, request.uid, domain)
            if shipping_ids:
                shipping_id = shipping_ids[0]
                partner_obj.write(request.cr, request.uid, [shipping_id], shipping_value)
            else:
                shipping_id = partner_obj.create(request.cr, request.uid, shipping_value)

        order_value = {
            'state': 'progress',
            'partner_id': partner_id,
            'partner_invoice_id': partner_id,
            'partner_shipping_id': shipping_id or partner_id
        }
        order_value.update(request.registry.get('sale.order').onchange_partner_id(request.cr, request.uid, [], request.uid, context={})['value'])
        order.write(order_value)

        json['validation'] = True
        return simplejson.dumps(json)

    @http.route(['/shop/confirmed'], type='http', auth="admin")
    def confirmed(self, **post):

        if request.httprequest.session.get('ecommerce_order'):
            order = self.get_current_order()
            if order.state != 'draft':
                request.httprequest.session['ecommerce_order_old'] = order.id
                request.httprequest.session['ecommerce_order'] = None

        order_old = self.get_order(request.httprequest.session.get('ecommerce_order_old'))
        if not order_old.order_line:
            return self.mycart(**post)

        values = {
            'temp': 0,
            'order': order_old,
            'categories': self.get_categories(),
        }
        return self.render("website_sale.confirmed", values)

# vim:expandtab:tabstop=4:softtabstop=4:shiftwidth=4:
