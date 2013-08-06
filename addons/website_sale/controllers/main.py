# -*- coding: utf-8 -*-

import math
import openerp
import simplejson
from openerp.osv import osv
from openerp.addons.web import http
from openerp.addons.web.http import request

def get_order(order_id=None):
    order_obj = request.registry.get('sale.order')
    # check if order allready exists
    if order_id:
        try:
            order_obj.browse(request.cr, openerp.SUPERUSER_ID, order_id).pricelist_id
        except:
            order_id = None
    if not order_id:
        fields = [k for k, v in order_obj._columns.items()]
        order_value = order_obj.default_get(request.cr, openerp.SUPERUSER_ID, fields)
        order_value['partner_id'] = request.registry.get('res.users').browse(request.cr, openerp.SUPERUSER_ID, request.uid).partner_id.id
        order_value.update(order_obj.onchange_partner_id(request.cr, openerp.SUPERUSER_ID, [], request.uid, context={})['value'])
        order_id = order_obj.create(request.cr, openerp.SUPERUSER_ID, order_value)
    return order_obj.browse(request.cr, openerp.SUPERUSER_ID, order_id)

def get_current_order():
    order = get_order(request.httprequest.session.get('ecommerce_order_id'))
    request.httprequest.session['ecommerce_order_id'] = order.id
    return order

def get_categories():
    category_obj = request.registry.get('pos.category')
    category_ids = category_obj.search(request.cr, openerp.SUPERUSER_ID, [('parent_id', '=', False)])
    return category_obj.browse(request.cr, openerp.SUPERUSER_ID, category_ids)


class website(osv.osv):
    _inherit = "website"
    def get_rendering_context(self, additional_values=None):
        values = {
            'website_sale_get_categories': get_categories,
            'order': get_current_order(),
            # 'website_sale_get_current_order': get_current_order, # TODO: replace 'order' key in templates
        }
        if additional_values:
            values.update(additional_values)
        return super(website, self).get_rendering_context(values)

class Ecommerce(http.Controller):

    def get_categories(self):
        category_obj = request.registry.get('pos.category')
        category_ids = category_obj.search(request.cr, openerp.SUPERUSER_ID, [('parent_id', '=', False)])
        categories = category_obj.browse(request.cr, openerp.SUPERUSER_ID, category_ids)
        print categories
        return categories

    def get_current_order(self):
        order = self.get_order(request.httprequest.session.get('ecommerce_order_id'))
        request.httprequest.session['ecommerce_order_id'] = order.id
        return order

    def get_order(self, order_id=None):

        order_obj = request.registry.get('sale.order')
        # check if order allready exists
        if order_id:
            try:
                order_obj.browse(request.cr, openerp.SUPERUSER_ID, order_id).pricelist_id
            except:
                order_id = None
        if not order_id:
            fields = [k for k, v in order_obj._columns.items()]
            order_value = order_obj.default_get(request.cr, openerp.SUPERUSER_ID, fields)
            order_value['partner_id'] = request.registry.get('res.users').browse(request.cr, openerp.SUPERUSER_ID, request.uid).partner_id.id
            order_value.update(order_obj.onchange_partner_id(request.cr, openerp.SUPERUSER_ID, [], request.uid, context={})['value'])
            order_id = order_obj.create(request.cr, openerp.SUPERUSER_ID, order_value)
        return order_obj.browse(request.cr, openerp.SUPERUSER_ID, order_id)

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
        product_obj = request.registry.get('product.product')

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

        # search to apply access rules
        product_ids = product_obj.search(request.cr, request.uid, [("id", "in", product_ids)])
        return product_obj.browse(request.cr, request.uid, product_ids)

    @http.route(['/shop', '/shop/category/<cat_id>', '/shop/category/<cat_id>/page/<page>', '/shop/page/<page>'], type='http', auth="public")
    def category(self, cat_id=0, page=0, **post):

        website = request.registry['website']
        product_obj = request.registry.get('product.product')

        domain = [("sale_ok", "=", True)]
        if openerp.SUPERUSER_ID != request.uid:
            domain += [('website_published', '=', True)]

        if cat_id:
            cat_id = int(cat_id)
            domain = [('pos_categ_id.id', 'child_of', cat_id)] + domain

        product_count = len(product_obj.search(request.cr, request.uid, domain))
        page_count = int(math.ceil(product_count / 20.0))

        #if post.get("search"):
         #   domain += ['|', '|', ('name', 'ilike', "%%%s%%" % post.get("search")), ('description', 'ilike', "%%%s%%" % post.get("search")), ('pos_categ_id.name', 'ilike', "%%%s%%" % post.get("search"))]

        page = max(1,min(int(page),page_count))
        offset = (page-1) * 20

        if page_count <= 5 or page <= 3:
            pmin = 1
            pmax = min(page_count,5)
        elif page >= page_count - 2:
            pmin = page_count - 4
            pmax = page_count
        else:
            pmin = page - 2
            pmax = page + 2

        pages = range(pmin, pmax+1)

        product_ids = product_obj.search(request.cr, request.uid, domain, limit=20, offset=offset)

        values = website.get_rendering_context({
            'current_category': cat_id,
            'products': product_obj.browse(request.cr, request.uid, product_ids),
            'search': post.get("search"),
            'page_count': page_count,
            'pages': pages,
            'page': page,
        })
        return website.render("website_sale.products", values)

    @http.route(['/shop/product/<product_id>'], type='http', auth="public")
    def product(self, cat_id=0, product_id=0):
        website = request.registry['website']
        order = get_current_order()

        product_id = product_id and int(product_id) or 0
        product_obj = request.registry.get('product.product')

        line = [line for line in order.order_line if line.product_id.id == product_id]
        quantity = line and int(line[0].product_uom_qty) or 0

        values = website.get_rendering_context({
            'product': product_obj.browse(request.cr, request.uid, product_id),
            'quantity': quantity,
            'recommended_products': self.recommended_product([product_id]),
        })
        return website.render("website_sale.product", values)

    @http.route(['/shop/mycart'], type='http', auth="public")
    def mycart(self, **post):
        website = request.registry['website']
        order = get_current_order()

        if post.get('code'):
            pricelist_obj = request.registry.get('product.pricelist')
            pricelist_ids = pricelist_obj.search(request.cr, openerp.SUPERUSER_ID, [('code', '=', post.get('code'))])
            if pricelist_ids:
                order.write({'pricelist_id': pricelist_ids[0]})

        my_pids = [line.product_id.id for line in order.order_line]
        values = website.get_rendering_context({
            "recommended_products": self.recommended_product(my_pids)
        })

        return website.render("website_sale.mycart", values)

    @http.route(['/shop/add_cart'], type='http', auth="public")
    def add_cart(self, product_id=0, remove=False):
        website = request.registry['website']
        values = website.get_rendering_context()
        context = {}

        order_line_obj = request.registry.get('sale.order.line')
        user_obj = request.registry.get('res.users')

        product_id = product_id and int(product_id) or 0
        order = get_current_order()

        quantity = 0

        # values initialisation
        order_line_ids = order_line_obj.search(request.cr, openerp.SUPERUSER_ID, [('order_id', '=', order.id), ('product_id', '=', product_id)], context=context)
        if order_line_ids:
            order_line = order_line_obj.read(request.cr, openerp.SUPERUSER_ID, order_line_ids, [], context=context)[0]
            quantity = order_line['product_uom_qty'] + (remove and -1 or 1)
            if quantity <= 0:
                order_line_obj.unlink(request.cr, openerp.SUPERUSER_ID, order_line_ids, context=context)
        else:
            fields = [k for k, v in order_line_obj._columns.items()]
            values = order_line_obj.default_get(request.cr, openerp.SUPERUSER_ID, fields, context=context)
            quantity = 1
        values['product_uom_qty'] = quantity
        values['product_id'] = product_id
        values['order_id'] = order.id

        # change and record value
        if quantity:
            pricelist_id = order.pricelist_id and order.pricelist_id.id or False
            values.update(order_line_obj.product_id_change(request.cr, openerp.SUPERUSER_ID, [], pricelist_id, product_id,
                partner_id=user_obj.browse(request.cr, openerp.SUPERUSER_ID, request.uid).partner_id.id,
                context=context)['value'])
            if order_line_ids:
                order_line_obj.write(request.cr, openerp.SUPERUSER_ID, order_line_ids, values, context=context)
            else:
                order_line_id = order_line_obj.create(request.cr, openerp.SUPERUSER_ID, values, context=context)
                order.write({'order_line': [(4, order_line_id)]}, context=context)

        html = website.render("website_sale.total", values)
        return simplejson.dumps({"quantity": quantity, "totalHTML": html})

    @http.route(['/shop/remove_cart'], type='http', auth="public")
    def remove_cart(self, product_id=0):
        return self.add_cart(product_id=product_id, remove=True)

    @http.route(['/shop/checkout'], type='http', auth="public")
    def checkout(self, **post):
        website = request.registry['website']
        values = website.get_rendering_context({
            'partner': False
        })
        order = get_current_order()

        if order.state != 'draft':
            return self.confirmed(**post)
        if not order.order_line:
            return self.mycart(**post)

        partner_obj = request.registry.get('res.partner')
        user_obj = request.registry.get('res.users')
        country_obj = request.registry.get('res.country')
        country_state_obj = request.registry.get('res.country.state')
        payment_obj = request.registry.get('portal.payment.acquirer')

        if request.uid != website.get_public_uid():
            values['partner'] = user_obj.browse(request.cr, request.uid, request.uid).partner_id
            shipping_ids = partner_obj.search(request.cr, request.uid, [("parent_id", "=", values['partner'].id), ('type', "=", 'delivery')])
            values['shipping'] = None
            if shipping_ids:
                values['shipping'] = partner_obj.browse(request.cr, request.uid, shipping_ids[0])

        values['countries'] = country_obj.browse(request.cr, openerp.SUPERUSER_ID, country_obj.search(request.cr, openerp.SUPERUSER_ID, [(1, "=", 1)]))
        values['states'] = country_state_obj.browse(request.cr, openerp.SUPERUSER_ID, country_state_obj.search(request.cr, openerp.SUPERUSER_ID, [(1, "=", 1)]))

        payment_ids = payment_obj.search(request.cr, openerp.SUPERUSER_ID, [('visible', '=', True)])
        values['payments'] = payment_obj.browse(request.cr, openerp.SUPERUSER_ID, payment_ids)
        for payment in values['payments']:
            content = payment_obj.render(request.cr, openerp.SUPERUSER_ID, payment.id, order, order.name, order.pricelist_id.currency_id, order.amount_total)
            payment._content = content

        return website.render("website_sale.checkout", values)

    @http.route(['/shop/confirm_order'], type='http', auth="public")
    def confirm_order(self, **post):
        website = request.registry['website']
        order = get_current_order()

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
            company_ids = partner_obj.search(request.cr, openerp.SUPERUSER_ID, [("name", "ilike", post['company']), ('is_company', '=', True)])
            company_id = company_ids and company_ids[0] or None
            if not company_id:
                company_id = partner_obj.create(request.cr, openerp.SUPERUSER_ID, {'name': post['company'], 'is_company': True})

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
        if request.uid != website.get_public_uid():
            partner_id = user_obj.browse(request.cr, request.uid, request.uid).partner_id.id
            partner_obj.write(request.cr, request.uid, [partner_id], partner_value)
        else:
            partner_id = partner_obj.create(request.cr, openerp.SUPERUSER_ID, partner_value)

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
            shipping_ids = partner_obj.search(request.cr, openerp.SUPERUSER_ID, domain)
            if shipping_ids:
                shipping_id = shipping_ids[0]
                partner_obj.write(request.cr, openerp.SUPERUSER_ID, [shipping_id], shipping_value)
            else:
                shipping_id = partner_obj.create(request.cr, openerp.SUPERUSER_ID, shipping_value)

        order_value = {
            'state': 'progress',
            'partner_id': partner_id,
            'partner_invoice_id': partner_id,
            'partner_shipping_id': shipping_id or partner_id
        }
        order_value.update(request.registry.get('sale.order').onchange_partner_id(request.cr, openerp.SUPERUSER_ID, [], request.uid, context={})['value'])
        order.write(order_value)

        json['validation'] = True
        return simplejson.dumps(json)

    @http.route(['/shop/confirmed'], type='http', auth="public")
    def confirmed(self, **post):
        website = request.registry['website']

        if request.httprequest.session.get('ecommerce_order_id'):
            order = get_current_order()
            if order.state != 'draft':
                request.httprequest.session['ecommerce_order_id_old'] = order.id
                request.httprequest.session['ecommerce_order_id'] = None

        order_old = get_order(request.httprequest.session.get('ecommerce_order_id_old'))
        if not order_old.order_line:
            return self.mycart(**post)

        values = website.get_rendering_context({
            'temp': 0,
            'order': order_old,
        })
        return website.render("website_sale.confirmed", values)

    @http.route(['/shop/publish'], type='http', auth="public")
    def publish(self, **post):
        product_id = int(post['id'])
        product_obj = request.registry['product.product']

        product = product_obj.browse(request.cr, request.uid, product_id)
        product_obj.write(request.cr, request.uid, [product_id], {'website_published': not product.website_published})
        product = product_obj.browse(request.cr, request.uid, product_id)

        return product.website_published and "1" or "0"

# vim:expandtab:tabstop=4:softtabstop=4:shiftwidth=4:
