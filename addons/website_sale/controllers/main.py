# -*- coding: utf-8 -*-

from openerp import SUPERUSER_ID
from openerp.osv import osv
from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp.addons.website import website
import random
import werkzeug
import simplejson

def get_order(order_id=None):
    order_obj = request.registry.get('sale.order')
    # check if order allready exists
    context = {}
    if order_id:
        try:
            order = order_obj.browse(request.cr, SUPERUSER_ID, order_id)
            order.pricelist_id
        except:
            order_id = None
    if not order_id:
        fields = [k for k, v in order_obj._columns.items()]
        order_value = order_obj.default_get(request.cr, SUPERUSER_ID, fields)
        if request.httprequest.session.get('ecommerce_pricelist'):
            order_value['pricelist_id'] = request.httprequest.session['ecommerce_pricelist']
        order_value['partner_id'] = request.registry.get('res.users').browse(request.cr, SUPERUSER_ID, request.uid).partner_id.id
        order_value.update(order_obj.onchange_partner_id(request.cr, SUPERUSER_ID, [], order_value['partner_id'], context={})['value'])
        order_id = order_obj.create(request.cr, SUPERUSER_ID, order_value)
        order = order_obj.browse(request.cr, SUPERUSER_ID, order_id)
        request.httprequest.session['ecommerce_order_id'] = order.id

    context = {
        'pricelist': order.pricelist_id.id,
    }
    return order_obj.browse(request.cr, SUPERUSER_ID, order_id, context=context)

def get_current_order():
    if request.httprequest.session.get('ecommerce_order_id'):
        return get_order(request.httprequest.session.get('ecommerce_order_id'))
    else:
        return False

class Website(osv.osv):
    _inherit = "website"
    def get_webcontext(self, values={}, **kw):
        values.update({
            'order': get_current_order(),
            # 'website_sale_get_current_order': get_current_order, # TODO: replace 'order' key in templates
        })
        return super(Website, self).get_webcontext(values, **kw)

class Ecommerce(http.Controller):

    def get_categories(self):
        category_obj = request.registry.get('product.public.category')
        category_ids = category_obj.search(request.cr, SUPERUSER_ID, [('parent_id', '=', False)], context=request.context)
        categories = category_obj.browse(request.cr, SUPERUSER_ID, category_ids, context=request.context)
        return categories

    @website.route(['/shop/', '/shop/category/<cat_id>/', '/shop/category/<cat_id>/page/<int:page>/', '/shop/page/<int:page>/'], type='http', auth="public")
    def category(self, cat_id=0, page=0, **post):

        if 'promo' in post:
            self.change_pricelist(post.get('promo'))
            
        website = request.registry['website']
        product_obj = request.registry.get('product.template')

        domain = [("sale_ok", "=", True)]
        if SUPERUSER_ID != request.uid:
            domain += [('website_published', '=', True)]

        if post.get("search"):
            domain += ['|', '|', '|',
                ('name', 'ilike', "%%%s%%" % post.get("search")), 
                ('description', 'ilike', "%%%s%%" % post.get("search")),
                ('website_description', 'ilike', "%%%s%%" % post.get("search")),
                ('product_variant_ids.public_categ_id.name', 'ilike', "%%%s%%" % post.get("search"))]
        if cat_id:
            cat_id = int(cat_id)
            domain += [('product_variant_ids.public_categ_id.id', 'child_of', cat_id)] + domain

        step = 20
        product_count = len(product_obj.search(request.cr, request.uid, domain))
        pager = website.pager(url="/shop/category/%s/" % cat_id, total=product_count, page=page, step=step, scope=7, url_args=post)

        product_ids = product_obj.search(request.cr, request.uid, domain, limit=step, offset=pager['offset'])

        context = {'pricelist': self.get_pricelist()}

        values = {
            'categories': self.get_categories(),
            'category_id': cat_id,
            'products': product_obj.browse(request.cr, SUPERUSER_ID, product_ids, context=context),
            'search': post.get("search"),
            'pager': pager,
        }
        return request.webcontext.render("website_sale.products", values)

    @website.route(['/shop/product/<product_id>/'], type='http', auth="public")
    def product(self, cat_id=0, product_id=0, **post):

        if 'promo' in post:
            self.change_pricelist(post.get('promo'))

        product_id = product_id and int(product_id) or 0
        product_obj = request.registry.get('product.template')
        category_obj = request.registry.get('product.public.category')

        context = {'pricelist': self.get_pricelist()}

        category_list = category_obj.name_get(request.cr, request.uid, category_obj.search(request.cr, request.uid, [(1,'=',1)]))
        category_list = sorted(category_list, key=lambda category: category[1])

        product = product_obj.browse(request.cr, request.uid, product_id, context=context)
        values = {
            'category_id': post.get('category_id') and int(post.get('category_id')) or None,
            'search': post.get("search"),
            'categories': self.get_categories(),
            'category_list': category_list,
            'product': product,
        }
        return request.webcontext.render("website_sale.product", values)

    @website.route(['/shop/add_product/'], type='http', auth="public")
    def add_product(self, **post):
        product_id = request.registry.get('product.product').create(request.cr, request.uid, {'name': 'New Product'})
        return werkzeug.utils.redirect("/shop/product/%s/" % product_id)

    @website.route(['/shop/change_category/<product_id>/'], type='http', auth="public")
    def edit_product(self, product_id=0, **post):
        request.registry.get('product.template').write(request.cr, request.uid, [int(product_id)], {'public_categ_id': int(post.get('public_categ_id', 0))})
        return "1"

    def get_pricelist(self):
        if not request.httprequest.session.get('ecommerce_pricelist'):
            self.change_pricelist(None)
        return request.httprequest.session.get('ecommerce_pricelist')

    def change_pricelist(self, code):
        request.httprequest.session.setdefault('ecommerce_pricelist', False)

        pricelist_id = False
        if code:
            pricelist_obj = request.registry.get('product.pricelist')
            pricelist_ids = pricelist_obj.search(request.cr, SUPERUSER_ID, [('code', '=', code)])
            if pricelist_ids:
                pricelist_id = pricelist_ids[0]

        if not pricelist_id:
            partner_id = request.registry.get('res.users').browse(request.cr, SUPERUSER_ID, request.uid).partner_id.id
            pricelist_id = request.registry['sale.order'].onchange_partner_id(request.cr, SUPERUSER_ID, [], partner_id, context={})['value']['pricelist_id']
        
        request.httprequest.session['ecommerce_pricelist'] = pricelist_id

        order = get_current_order()
        if order:
            values = {'pricelist_id': pricelist_id}
            values.update(order.onchange_pricelist_id(pricelist_id, None)['value'])
            order.write(values)
            for line in order.order_line:
                self.add_product_to_cart(order_line_id=line.id, number=0)

    def add_product_to_cart(self, product_id=0, order_line_id=0, number=1, set_number=-1):
        order_line_obj = request.registry.get('sale.order.line')

        product_id = product_id and int(product_id) or 0

        order = get_current_order()
        if not order:
            order = get_order()

        context = {'pricelist': self.get_pricelist()}

        quantity = 0

        # values initialisation
        values = {}

        domain = [('order_id', '=', order.id)]
        if order_line_id:
            domain += [('id', '=', order_line_id)]
        else:
            domain += [('product_id', '=', product_id)]

        order_line_ids = order_line_obj.search(request.cr, SUPERUSER_ID, domain, context=context)
        if order_line_ids:
            order_line = order_line_obj.read(request.cr, SUPERUSER_ID, order_line_ids, [], context=context)[0]
            if not product_id:
                product_id = order_line['product_id'][0]
            if set_number >= 0:
                quantity = set_number
            else:
                quantity = order_line['product_uom_qty'] + number
            if quantity < 0:
                quantity = 0
        else:
            fields = [k for k, v in order_line_obj._columns.items()]
            values = order_line_obj.default_get(request.cr, SUPERUSER_ID, fields, context=context)
            quantity = 1

        # change and record value
        vals = order_line_obj._recalculate_product_values(request.cr, request.uid, order_line_ids, product_id, context=context)
        values.update(vals)

        values['product_uom_qty'] = quantity
        values['product_id'] = product_id
        values['order_id'] = order.id

        if order_line_ids:
            order_line_obj.write(request.cr, SUPERUSER_ID, order_line_ids, values, context=context)
            if not quantity:
                order_line_obj.unlink(request.cr, SUPERUSER_ID, order_line_ids, context=context)
        else:
            order_line_id = order_line_obj.create(request.cr, SUPERUSER_ID, values, context=context)
            order.write({'order_line': [(4, order_line_id)]}, context=context)

        return [quantity, order.get_total_quantity()]

    @website.route(['/shop/mycart/'], type='http', auth="public")
    def mycart(self, **post):
        order = get_current_order()
        prod_obj = request.registry.get('product.product')

        if 'promo' in post:
            self.change_pricelist(post.get('promo'))

        suggested_ids = []
        if order:
            for line in order.order_line:
                suggested_ids += [p.id for p in line.product_id and line.product_id.suggested_product_ids or [] for line in order.order_line]
        suggested_ids = prod_obj.search(request.cr, request.uid, [('id', 'in', suggested_ids)])
        # select 3 random products
        suggested_products = []
        while len(suggested_products) < 3 and suggested_ids:
            index = random.randrange(0, len(suggested_ids))
            suggested_products.append(suggested_ids.pop(index))

        values = {
            'categories': self.get_categories(),
            'suggested_products': prod_obj.browse(request.cr, request.uid, suggested_products),
        }
        return request.webcontext.render("website_sale.mycart", values)

    @website.route(['/shop/<path:path>/add_cart/', '/shop/add_cart/'], type='http', auth="public")
    def add_cart(self, path=None, product_id=None, order_line_id=None, remove=None, json=None):
        quantity = self.add_product_to_cart(product_id=product_id, order_line_id=order_line_id, number=(remove and -1 or 1))
        if json:
            return simplejson.dumps(quantity)
        if path:
            return werkzeug.utils.redirect("/shop/%s/" % path)
        else:
            return werkzeug.utils.redirect("/shop/")

    @website.route(['/shop/remove_cart/', '/shop/<path:path>/remove_cart/'], type='http', auth="public")
    def remove_cart(self, path=None, product_id=None, order_line_id=None, json=None):
        return self.add_cart(product_id=product_id, order_line_id=order_line_id, path=path, remove=True, json=json)

    @website.route(['/shop/set_cart/', '/shop/<path:path>/set_cart/'], type='http', auth="public")
    def set_cart(self, path=None, product_id=None, order_line_id=None, set_number=0, json=None):
        quantity = self.add_product_to_cart(product_id=product_id, order_line_id=order_line_id, set_number=set_number)
        if json:
            return simplejson.dumps(quantity)
        if path:
            return werkzeug.utils.redirect("/shop/%s/" % path)
        else:
            return werkzeug.utils.redirect("/shop/")

    @website.route(['/shop/checkout/'], type='http', auth="public")
    def checkout(self, **post):
        order = get_current_order()

        if order.state != 'draft' or not order.order_line:
            return self.mycart(**post)

        partner_obj = request.registry.get('res.partner')
        user_obj = request.registry.get('res.users')
        country_obj = request.registry.get('res.country')
        country_state_obj = request.registry.get('res.country.state')

        values = {
            'shipping': post.get("shipping"),
            'error': post.get("error") and dict.fromkeys(post.get("error").split(","), 'error') or {}
        }

        checkout = {}
        if not request.webcontext.is_public_user:
            partner = user_obj.browse(request.cr, request.uid, request.uid).partner_id
            partner_id = partner.id
            fields = ["name", "phone", "fax", "company", "email", "street", "city", "state_id", "zip", "country_id"]
            checkout = user_obj.read(request.cr, SUPERUSER_ID, [partner_id], fields)[0]
            checkout['company'] = partner.parent_id and partner.parent_id.name or ''

            shipping_ids = partner_obj.search(request.cr, request.uid, [("parent_id", "=", partner_id), ('type', "=", 'delivery')])
            if shipping_ids:
                for k,v in partner_obj.read(request.cr, request.uid, shipping_ids[0]).items():
                    checkout['shipping_'+k] = v or ''

        checkout.update(request.session.setdefault('checkout', {}))
        for k,v in checkout.items():
            checkout[k] = v or ''
        values['checkout'] = checkout

        values['countries'] = country_obj.browse(request.cr, SUPERUSER_ID, country_obj.search(request.cr, SUPERUSER_ID, [(1, "=", 1)]))
        values['states'] = country_state_obj.browse(request.cr, SUPERUSER_ID, country_state_obj.search(request.cr, SUPERUSER_ID, [(1, "=", 1)]))

        return request.webcontext.render("website_sale.checkout", values)

    @website.route(['/shop/confirm_order/'], type='http', auth="public")
    def confirm_order(self, **post):
        order = get_current_order()

        error = []
        partner_obj = request.registry.get('res.partner')
        user_obj = request.registry.get('res.users')

        if order.state != 'draft':
            return werkzeug.utils.redirect("/shop/checkout/")
        if not order.order_line:
            error.append("empty_cart")
            return werkzeug.utils.redirect("/shop/checkout/")

        # check values
        request.session['checkout'] = post
        required_field = ['phone', 'zip', 'email', 'street', 'city', 'name', 'country_id']
        for key in required_field:
            if not post.get(key):
                error.append(key)
            if post.get('shipping_different') and key != 'email' and not post.get("shipping_%s" % key):
                error.append("shipping_%s" % key)
        if error:
            return werkzeug.utils.redirect("/shop/checkout/?error=%s&shipping=%s" % (",".join(error), post.get('shipping_different') and 'on' or ''))

        # search or create company
        company_id = None
        if post['company']:
            company_ids = partner_obj.search(request.cr, SUPERUSER_ID, [("name", "ilike", post['company']), ('is_company', '=', True)])
            company_id = company_ids and company_ids[0] or None
            if not company_id:
                company_id = partner_obj.create(request.cr, SUPERUSER_ID, {'name': post['company'], 'is_company': True})

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
        if not request.webcontext.is_public_user:
            partner_id = user_obj.browse(request.cr, request.uid, request.uid).partner_id.id
            partner_obj.write(request.cr, request.uid, [partner_id], partner_value)
        else:
            partner_id = partner_obj.create(request.cr, SUPERUSER_ID, partner_value)

        shipping_id = None
        if post.get('shipping_different'):
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
            domain = [(key, '_id' in key and '=' or 'ilike', '_id' in key and value and int(value) or False)
                for key, value in shipping_value.items() if key in required_field + ["type", "parent_id"]]

            shipping_ids = partner_obj.search(request.cr, SUPERUSER_ID, domain)
            if shipping_ids:
                shipping_id = shipping_ids[0]
                partner_obj.write(request.cr, SUPERUSER_ID, [shipping_id], shipping_value)
            else:
                shipping_id = partner_obj.create(request.cr, SUPERUSER_ID, shipping_value)

        order_value = {
            'partner_id': partner_id,
            'partner_invoice_id': partner_id,
            'partner_shipping_id': shipping_id or partner_id
        }
        order_value.update(request.registry.get('sale.order').onchange_partner_id(request.cr, SUPERUSER_ID, [], order.partner_id.id, context={})['value'])
        order.write(order_value)

        return werkzeug.utils.redirect("/shop/payment/")

    @website.route(['/shop/payment/'], type='http', auth="public")
    def payment(self, **post):
        order = get_current_order()

        if not order or not order.order_line:
            return self.mycart(**post)

        values = {
            'partner': False,
            'order': order
        }

        payment_obj = request.registry.get('portal.payment.acquirer')
        payment_ids = payment_obj.search(request.cr, SUPERUSER_ID, [('visible', '=', True)])
        values['payments'] = payment_obj.browse(request.cr, SUPERUSER_ID, payment_ids)
        for payment in values['payments']:
            content = payment_obj.render(request.cr, SUPERUSER_ID, payment.id, order, order.name, order.pricelist_id.currency_id, order.amount_total)
            payment._content = content

        return request.webcontext.render("website_sale.payment", values)

    @website.route(['/shop/payment_validate/'], type='http', auth="public")
    def payment_validate(self, **post):
        request.httprequest.session['ecommerce_order_id'] = False
        request.httprequest.session['ecommerce_pricelist'] = False
        return werkzeug.utils.redirect("/shop/")

# vim:expandtab:tabstop=4:softtabstop=4:shiftwidth=4:
