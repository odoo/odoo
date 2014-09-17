# -*- coding: utf-8 -*-
import random
import simplejson
import werkzeug

from openerp import SUPERUSER_ID
from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp.tools.translate import _
from openerp.addons.website.models.website import slug

PPG = 20                        # Products Per Page
PPR = 4                         # Products Per Row


class CheckoutInfo(object):
    mandatory_billing_fields = ["name", "phone", "email", "street", "city", "country_id", "zip"]
    optional_billing_fields = ["company", "state_id"]
    string_billing_fields = ["name", "phone", "email", "street", "city", "zip"]

    mandatory_shipping_fields = ["shipping_name", "shipping_phone", "shipping_street", "shipping_city", "shipping_country_id", "shipping_zip"]
    optional_shipping_field = ["shipping_state_id"]
    string_shipping_fields = ["shipping_name", "shipping_phone", "shipping_street", "shipping_city", "shipping_zip"]

    def mandatory_fields(self):
        return self.mandatory_billing_fields + self.mandatory_shipping_fields

    def optional_fields(self):
        return self.optional_billing_fields + self.optional_shipping_field

    def all_fields(self):
        return self.mandatory_fields() + self.optional_fields()

    def empty(self):
        return dict.fromkeys(self.all_fields(), '')

    def from_partner(self, partner, address_type='billing'):
        assert address_type in ('billing', 'shipping')
        if address_type == 'billing':
            prefix = ''
        else:
            prefix = 'shipping_'
        result = dict((prefix + field_name, getattr(partner, field_name)) for field_name in self.string_billing_fields if getattr(partner, field_name))
        result[prefix + 'state_id'] = partner.state_id and partner.state_id.id or ''
        result[prefix + 'country_id'] = partner.country_id and partner.country_id.id or ''
        result[prefix + 'company'] = partner.commercial_partner_id and partner.commercial_partner_id.is_company and partner.commercial_partner_id.name or ''
        return result

    def from_post(self, post):
        return dict((field_name, post[field_name]) for field_name in self.all_fields() if post[field_name])


#
# Compute grid of products according to their sizes
#
class table_compute(object):
    def __init__(self):
        self.table = {}

    def _check_place(self, posx, posy, sizex, sizey):
        res = True
        for y in range(sizey):
            for x in range(sizex):
                if posx+x>=PPR:
                    res = False
                    break
                row = self.table.setdefault(posy+y, {})
                if row.setdefault(posx+x) is not None:
                    res = False
                    break
            for x in range(PPR):
                self.table[posy+y].setdefault(x, None)
        return res

    def process(self, products):
        # Compute products positions on the grid
        minpos = 0
        index = 0
        maxy = 0
        for p in products:
            x = min(max(p.website_size_x, 1), PPR)
            y = min(max(p.website_size_y, 1), PPR)
            if index>PPG:
                x = y = 1

            pos = minpos
            while not self._check_place(pos%PPR, pos/PPR, x, y):
                pos += 1

            if index>PPG and (pos/PPR)>maxy:
                break

            if x==1 and y==1:   # simple heuristic for CPU optimization
                minpos = pos/PPR

            for y2 in range(y):
                for x2 in range(x):
                    self.table[(pos/PPR)+y2][(pos%PPR)+x2] = False
            self.table[pos/PPR][pos%PPR] = {
                'product': p, 'x':x, 'y': y,
                'class': " ".join(map(lambda x: x.html_class or '', p.website_style_ids))
            }
            if index<=PPG:
                maxy=max(maxy,y+(pos/PPR))
            index += 1

        # Format table according to HTML needs
        rows = self.table.items()
        rows.sort()
        rows = map(lambda x: x[1], rows)
        for col in range(len(rows)):
            cols = rows[col].items()
            cols.sort()
            x += len(cols)
            rows[col] = [c for c in map(lambda x: x[1], cols) if c != False]

        return rows


class Ecommerce(http.Controller):

    _order = 'website_published desc, website_sequence desc'

    def get_attribute_ids(self):
        attributes_obj = request.registry['product.attribute']
        attributes_ids = attributes_obj.search(request.cr, request.uid, [], context=request.context)
        return attributes_obj.browse(request.cr, request.uid, attributes_ids, context=request.context)

    def get_pricelist(self):
        """ Shortcut to get the pricelist from the website model """
        return request.registry['website'].ecommerce_get_pricelist_id(request.cr, request.uid, None, context=request.context)

    def get_order(self):
        """ Shortcut to get the current ecommerce quotation from the website model """
        return request.registry['website'].ecommerce_get_current_order(request.cr, request.uid, context=request.context)

    def get_products(self, product_ids):
        product_obj = request.registry.get('product.template')
        request.context['pricelist'] = self.get_pricelist()
        # search for checking of access rules and keep order
        product_ids = [id for id in product_ids if id in product_obj.search(request.cr, request.uid, [("id", 'in', product_ids)], context=request.context)]
        return product_obj.browse(request.cr, request.uid, product_ids, context=request.context)

    def has_search_filter(self, attribute_id, value_id=None):
        if request.httprequest.args.get('filters'):
            filters = simplejson.loads(request.httprequest.args['filters'])
        else:
            filters = []
        for key_val in filters:
            if key_val[0] == attribute_id and (not value_id or value_id in key_val[1:]):
                return key_val
        return False

    @http.route(['/shop/filters/'], type='http', auth="public", methods=['POST'], website=True, multilang=True)
    def filters(self, category=None, **post):
        index = []
        filters = []
        for key, val in post.items():
            cat = key.split("-")
            if len(cat) < 3 or cat[2] in ('max','minmem','maxmem'):
                continue
            cat_id = int(cat[1])
            if cat[2] == 'min':
                minmem = float(post.pop("att-%s-minmem" % cat[1]))
                maxmem = float(post.pop("att-%s-maxmem" % cat[1]))
                _max = int(post.pop("att-%s-max" % cat[1]))
                _min = int(val)
                if (minmem != _min or maxmem != _max) and cat_id not in index:
                    filters.append([cat_id , [_min, _max] ])
                    index.append(cat_id)
            elif cat_id not in index:
                filters.append([ cat_id, int(cat[2]) ])
                index.append(cat_id)
            else:
                cat[2] = int(cat[2])
                if cat[2] not in filters[index.index(cat_id)][1:]:
                    filters[index.index(cat_id)].append( cat[2] )
            post.pop(key)

        url = "/shop/"
        if category:
            category_obj = request.registry.get('product.public.category')
            url = "%scategory/%s/" % (url, slug(category_obj.browse(request.cr, request.uid, int(category), context=request.context)))
        if filters:
            url = "%s?filters=%s" % (url, simplejson.dumps(filters))
        if post.get("search"):
            url = "%s%ssearch=%s" % (url, filters and "&" or "?", post.get("search"))

        return request.redirect(url)

    def attributes_to_ids(self, cr, uid, attributes):
        req = """
                SELECT  product_tmpl_id as id, count(*) as nb_match
                FROM    product_attribute_line
                WHERE   1!=1
            """
        nb = 0
        for key_val in attributes:
            attribute_id = key_val[0]
            if isinstance(key_val[1], list):
                req += " OR ( attribute_id = %s AND value >= %s AND value <= %s)" % \
                        (attribute_id, key_val[1][0], key_val[1][1])
                nb += 1
            else:
                for value_id in key_val[1:]:
                    req += " OR ( attribute_id = %s AND value_id = %s)" % \
                        (attribute_id, value_id)
                    nb += 1

        req += " GROUP BY product_tmpl_id"
        cr.execute(req)
        result = cr.fetchall()
        return [id for id, nb_match in result if nb_match >= nb]

    @http.route(['/shop/pricelist'], type='http', auth="public", website=True, multilang=True)
    def shop_promo(self, promo=None, **post):
        request.registry['website']._ecommerce_change_pricelist(request.cr, request.uid, code=promo, context=request.context)
        return request.redirect("/shop/mycart/")

    @http.route([
        '/shop/',
        '/shop/page/<int:page>/',
        '/shop/category/<model("product.public.category"):category>/',
        '/shop/category/<model("product.public.category"):category>/page/<int:page>/'
    ], type='http', auth="public", website=True, multilang=True)
    def shop(self, category=None, page=0, filters='', search='', **post):
        cr, uid, context = request.cr, request.uid, request.context
        product_obj = request.registry.get('product.template')
        base_domain = request.registry.get('website').ecommerce_get_product_domain()
        domain = list(base_domain)
        if search:
            domain += ['|',
                ('name', 'ilike', search),
                ('description', 'ilike', search)]
        if category:
            domain.append(('product_variant_ids.public_categ_id', 'child_of', int(category)))
            if isinstance(category, (int,str,unicode)):
                category = request.registry.get('product.public.category').browse(cr, uid, int(category), context=context)
        if filters:
            filters = simplejson.loads(filters)
            if filters:
                ids = self.attributes_to_ids(cr, uid, filters)
                domain.append(('id', 'in', ids or [0]))

        url = "/shop/"
        product_count = product_obj.search_count(cr, uid, domain, context=context)
        if search:
            post["search"] = search
        if filters:
            post["filters"] = filters
        if category:
            url = "/shop/category/%s/" % slug(category)
        pager = request.website.pager(url=url, total=product_count, page=page, step=PPG, scope=7, url_args=post)

        request.context['pricelist'] = self.get_pricelist()

        pids = product_obj.search(cr, uid, domain, limit=PPG+10, offset=pager['offset'], order=self._order, context=context)
        products = product_obj.browse(cr, uid, pids, context=context)

        styles = []
        try:
            style_obj = request.registry.get('product.style')
            style_ids = style_obj.search(request.cr, request.uid, [], context=request.context)
            styles = style_obj.browse(request.cr, request.uid, style_ids, context=request.context)
        except:
            pass

        category_obj = request.registry.get('product.public.category')
        category_ids = [product['public_categ_id'][0] for product in product_obj.read_group(cr, uid, base_domain, ['public_categ_id'], ['public_categ_id'], context=context) if product['public_categ_id']]
        categories = category_obj.browse(cr, uid, category_ids, context=context)
        all_categories = set(categories)
        for cat in categories:
            parent = cat.parent_id
            while parent:
                all_categories.add(parent)
                parent = parent.parent_id
        categories = list(all_categories)
        categories.sort(key=lambda x: x.sequence)

        values = {
            'products': products,
            'bins': table_compute().process(products),
            'rows': PPR,
            'range': range,
            'search': {
                'search': search,
                'category': category and int(category),
                'filters': filters,
            },
            'pager': pager,
            'styles': styles,
            'category': category,
            'categories': filter(lambda x: not x.parent_id, categories),
            'all_categories': categories,
            'Ecommerce': self,   # TODO fp: Should be removed
            'style_in_product': lambda style, product: style.id in [s.id for s in product.website_style_ids],
        }
        return request.website.render("website_sale.products", values)

    @http.route(['/shop/product/<model("product.template"):product>/'], type='http', auth="public", website=True, multilang=True)
    def product(self, product, search='', category='', filters='', **kwargs):
        if category:
            category_obj = request.registry.get('product.public.category')
            category = category_obj.browse(request.cr, request.uid, int(category), context=request.context)

        request.context['pricelist'] = self.get_pricelist()

        values = {
            'Ecommerce': self,
            'main_object': product,
            'product': product,
            'category': category,
            'search': {
                'search': search,
                'category': category and int(category),
                'filters': filters,
            }
        }
        return request.website.render("website_sale.product", values)

    @http.route(['/shop/product/<int:product_template_id>/comment'], type='http', auth="public", methods=['POST'], website=True)
    def product_comment(self, product_template_id, **post):
        cr, uid, context = request.cr, request.uid, request.context
        if post.get('comment'):
            request.registry['product.template'].message_post(
                cr, uid, product_template_id,
                body=post.get('comment'),
                type='comment',
                subtype='mt_comment',
                context=dict(context, mail_create_nosubcribe=True))
        return werkzeug.utils.redirect(request.httprequest.referrer + "#comments")

    @http.route(['/shop/add_product/'], type='http', auth="user", methods=['POST'], website=True, multilang=True)
    def add_product(self, name=None, category=0, **post):
        if not name:
            name = _("New Product")
        Product = request.registry.get('product.product')
        product_id = Product.create(request.cr, request.uid, {
            'name': name, 'public_categ_id': category
        }, context=request.context)
        product = Product.browse(request.cr, request.uid, product_id, context=request.context)

        return request.redirect("/shop/product/%s/?enable_editor=1" % product.product_tmpl_id.id)

    @http.route(['/shop/mycart/'], type='http', auth="public", website=True, multilang=True)
    def mycart(self, **post):
        cr, uid, context = request.cr, request.uid, request.context
        prod_obj = request.registry.get('product.product')

        # must have a draft sale order with lines at this point, otherwise reset
        order = self.get_order()
        if order and order.state != 'draft':
            request.registry['website'].ecommerce_reset(cr, uid, context=context)
            return request.redirect('/shop/')

        self.get_pricelist()

        suggested_ids = []
        product_ids = []
        if order:
            for line in order.order_line:
                suggested_ids += [p.id for p in line.product_id and line.product_id.accessory_product_ids or []]
                product_ids.append(line.product_id.id)
        suggested_ids = list(set(suggested_ids) - set(product_ids))
        if suggested_ids:
            suggested_ids = prod_obj.search(cr, uid, [('id', 'in', suggested_ids)], context=context)

        # select 3 random products
        suggested_products = []
        while len(suggested_products) < 3 and suggested_ids:
            index = random.randrange(0, len(suggested_ids))
            suggested_products.append(suggested_ids.pop(index))

        context = dict(context or {}, pricelist=request.registry['website'].ecommerce_get_pricelist_id(cr, uid, None, context=context))

        values = {
            'int': int,
            'suggested_products': prod_obj.browse(cr, uid, suggested_products, context),
        }
        return request.website.render("website_sale.mycart", values)

    @http.route(['/shop/add_cart/'], type='http', auth="public", methods=['POST'], website=True, multilang=True)
    def add_cart(self, product_id, remove=None, **kw):
        request.registry['website']._ecommerce_add_product_to_cart(request.cr, request.uid,
            product_id=int(product_id),
            number=float(kw.get('number',1)),
            set_number=float(kw.get('set_number',-1)),
            context=request.context)
        return request.redirect("/shop/mycart/")

    @http.route(['/shop/change_cart/<int:order_line_id>/'], type='http', auth="public", website=True, multilang=True)
    def add_cart_order_line(self, order_line_id=None, remove=None, **kw):
        request.registry['website']._ecommerce_add_product_to_cart(request.cr, request.uid,
            order_line_id=order_line_id, number=(remove and -1 or 1),
            context=request.context)
        return request.redirect("/shop/mycart/")

    @http.route(['/shop/add_cart_json/'], type='json', auth="public", website=True, multilang=True)
    def add_cart_json(self, product_id=None, order_line_id=None, remove=None):
        quantity = request.registry['website']._ecommerce_add_product_to_cart(request.cr, request.uid,
            product_id=product_id, order_line_id=order_line_id, number=(remove and -1 or 1),
            context=request.context)
        order = self.get_order()
        return [quantity,
                order.get_number_of_products(),
                order.amount_total,
                request.website._render("website_sale.total", {'website_sale_order': order})]

    @http.route(['/shop/set_cart_json/'], type='json', auth="public", website=True, multilang=True)
    def set_cart_json(self, path=None, product_id=None, order_line_id=None, set_number=0, json=None):
        quantity = request.registry['website']._ecommerce_add_product_to_cart(request.cr, request.uid,
            product_id=product_id, order_line_id=order_line_id, set_number=set_number,
            context=request.context)
        order = self.get_order()
        return [quantity,
                order.get_number_of_products(),
                order.amount_total,
                request.website._render("website_sale.total", {'website_sale_order': order})]
    
    @http.route(['/shop/checkout/'], type='http', auth="public", website=True, multilang=True)
    def checkout(self, **post):
        cr, uid, context, registry = request.cr, request.uid, request.context, request.registry

        # must have a draft sale order with lines at this point, otherwise reset
        order = self.get_order()
        if not order or order.state != 'draft' or not order.order_line:
            request.registry['website'].ecommerce_reset(cr, uid, context=context)
            return request.redirect('/shop/')
        # if transaction pending / done: redirect to confirmation
        tx = context.get('website_sale_transaction')
        if tx and tx.state != 'draft':
            return request.redirect('/shop/payment/confirmation/%s' % order.id)

        self.get_pricelist()

        orm_partner = registry.get('res.partner')
        orm_user = registry.get('res.users')
        orm_country = registry.get('res.country')
        country_ids = orm_country.search(cr, SUPERUSER_ID, [], context=context)
        countries = orm_country.browse(cr, SUPERUSER_ID, country_ids, context)
        state_orm = registry.get('res.country.state')
        states_ids = state_orm.search(cr, SUPERUSER_ID, [], context=context)
        states = state_orm.browse(cr, SUPERUSER_ID, states_ids, context)

        info = CheckoutInfo()
        values = {
            'countries': countries,
            'states': states,
            'checkout': info.empty(),
            'shipping': post.get("shipping_different"),
            'error': {},
        }
        checkout = values['checkout']

        partner = None
        public_id = request.registry['website'].get_public_user(cr, uid, context)
        if request.uid != public_id:
            partner = orm_user.browse(cr, uid, uid, context).partner_id
        elif order.partner_id:
            public_partner = orm_user.browse(cr, SUPERUSER_ID, public_id, context=context).partner_id.id
            if public_partner != order.partner_id.id:
                partner = orm_partner.browse(cr, SUPERUSER_ID, order.partner_id.id, context)

        if partner:
            partner_info = info.from_partner(partner)
            checkout.update(partner_info)
            shipping_ids = orm_partner.search(cr, SUPERUSER_ID, [("parent_id", "=", partner.id), ('type', "=", 'delivery')], limit=1, context=context)
            if shipping_ids:
                values['shipping'] = "true"
                shipping_partner = orm_partner.browse(cr, SUPERUSER_ID, shipping_ids[0], context)
                checkout.update(info.from_partner(shipping_partner, address_type='shipping'))

        return request.website.render("website_sale.checkout", values)

    @http.route(['/shop/confirm_order/'], type='http', auth="public", website=True, multilang=True)
    def confirm_order(self, **post):
        cr, uid, context, registry = request.cr, request.uid, request.context, request.registry
        order_line_obj = request.registry.get('sale.order')

        # must have a draft sale order with lines at this point, otherwise redirect to shop
        order = self.get_order()
        if not order or order.state != 'draft' or not order.order_line:
            request.registry['website'].ecommerce_reset(cr, uid, context=context)
            return request.redirect('/shop/')
        # if transaction pending / done: redirect to confirmation
        tx = context.get('website_sale_transaction')
        if tx and tx.state != 'draft':
            return request.redirect('/shop/payment/confirmation/%s' % order.id)

        orm_partner = registry.get('res.partner')
        orm_user = registry.get('res.users')
        orm_country = registry.get('res.country')
        country_ids = orm_country.search(cr, SUPERUSER_ID, [], context=context)
        countries = orm_country.browse(cr, SUPERUSER_ID, country_ids, context)
        orm_state = registry.get('res.country.state')
        states_ids = orm_state.search(cr, SUPERUSER_ID, [], context=context)
        states = orm_state.browse(cr, SUPERUSER_ID, states_ids, context)

        info = CheckoutInfo()
        values = {
            'countries': countries,
            'states': states,
            'checkout': info.empty(),
            'shipping': post.get("shipping_different"),
            'error': {},
        }
        checkout = values['checkout']
        checkout.update(post)
        error = values['error']

        for field_name in info.mandatory_billing_fields:
            if not checkout[field_name]:
                error[field_name] = 'missing'
        if post.get("shipping_different"):
            for field_name in info.mandatory_shipping_fields:
                if not checkout[field_name]:
                    error[field_name] = 'missing'
        if error:
            return request.website.render("website_sale.checkout", values)

        billing_info = dict((k, v) for k,v in checkout.items() if "shipping_" not in k and k != "company")

        partner_id = None
        public_id = request.registry['website'].get_public_user(cr, uid, context)
        if request.uid != public_id:
            partner_id = orm_user.browse(cr, SUPERUSER_ID, uid, context=context).partner_id.id
        elif order.partner_id:
            public_partner = orm_user.browse(cr, SUPERUSER_ID, public_id, context=context).partner_id.id
            if public_partner != order.partner_id.id:
                partner_id = order.partner_id.id

        if partner_id:
            orm_partner.write(cr, SUPERUSER_ID, [partner_id], billing_info, context=context)
        else:
            partner_id = orm_partner.create(cr, SUPERUSER_ID, billing_info, context=context)

        shipping_id = None
        if post.get('shipping_different'):
            shipping_info = {
                'phone': post['shipping_phone'],
                'zip': post['shipping_zip'],
                'street': checkout['company'],
                'street2': post['shipping_street'],
                'city': post['shipping_city'],
                'name': post['shipping_name'],
                'email': post['email'],
                'type': 'delivery',
                'parent_id': partner_id,
                'country_id': post['shipping_country_id'],
                'state_id': post['shipping_state_id'],
            }
            domain = [(key, '_id' in key and '=' or 'ilike', '_id' in key and value and int(value) or value)
                      for key, value in shipping_info.items() if key in info.mandatory_billing_fields + ["type", "parent_id"]]

            shipping_ids = orm_partner.search(cr, SUPERUSER_ID, domain, context=context)
            if shipping_ids:
                shipping_id = shipping_ids[0]
                orm_partner.write(cr, SUPERUSER_ID, [shipping_id], shipping_info, context)
            else:
                shipping_id = orm_partner.create(cr, SUPERUSER_ID, shipping_info, context)

        order_info = {
            'partner_id': partner_id,
            'message_follower_ids': [(4, partner_id)],
            'partner_invoice_id': partner_id,
            'partner_shipping_id': shipping_id or partner_id
        }
        order_info.update(registry.get('sale.order').onchange_partner_id(cr, SUPERUSER_ID, [], partner_id, context=context)['value'])
        order_info.pop('user_id')

        order_line_obj.write(cr, SUPERUSER_ID, [order.id], order_info, context=context)

        return request.redirect("/shop/payment/")

    @http.route(['/shop/payment/'], type='http', auth="public", website=True, multilang=True)
    def payment(self, **post):
        """ Payment step. This page proposes several payment means based on available
        payment.acquirer. State at this point :

         - a draft sale order with lines; otherwise, clean context / session and
           back to the shop
         - no transaction in context / session, or only a draft one, if the customer
           did go to a payment.acquirer website but closed the tab without
           paying / canceling
        """
        cr, uid, context = request.cr, request.uid, request.context
        payment_obj = request.registry.get('payment.acquirer')
        sale_order_obj = request.registry['sale.order']

        # if no sale order at this stage: back to checkout beginning
        order = self.get_order()
        if not order or order.state != 'draft' or not order.order_line:
            request.registry['website'].ecommerce_reset(cr, uid, context=context)
            return request.redirect("/shop/")
        # alread a transaction: forward to confirmation
        tx = context.get('website_sale_transaction')
        if tx and tx.state != 'draft':
            return request.redirect('/shop/confirmation/%s' % order.id)

        shipping_partner_id = False
        if order:
            if order.partner_shipping_id.id:
                shipping_partner_id = order.partner_shipping_id.id
            else:
                shipping_partner_id = order.partner_invoice_id.id

        values = {}
        values['website_sale_order'] = values['order'] = sale_order_obj.browse(cr, SUPERUSER_ID, order.id, context=context)
        values['errors'] = sale_order_obj._get_errors(cr, uid, order, context=context)
        values.update(sale_order_obj._get_website_data(cr, uid, order, context=context))

        if not values['errors']:
            # fetch all registered payment means
            if tx:
                acquirer_ids = [tx.acquirer_id.id]
            else:
                acquirer_ids = payment_obj.search(cr, SUPERUSER_ID, [('website_published', '=', True), '|', ('company_id', '=', order.company_id.id), ('company_id', '=', False)], context=context)
            values['acquirers'] = payment_obj.browse(cr, uid, acquirer_ids, context=context)
            render_ctx = dict(context, submit_class='btn btn-primary', submit_txt='Pay Now')
            for acquirer in values['acquirers']:
                render_ctx['tx_url'] = '/shop/payment/transaction/%s' % acquirer.id
                acquirer.button = payment_obj.render(
                    cr, SUPERUSER_ID, acquirer.id,
                    order.name,
                    order.amount_total,
                    order.pricelist_id.currency_id.id,
                    partner_id=shipping_partner_id,
                    tx_values={
                        'return_url': '/shop/payment/validate',
                    },
                    context=render_ctx)

        return request.website.render("website_sale.payment", values)

    @http.route(['/shop/payment/transaction/<int:acquirer_id>'],
                   type='http', methods=['POST'], auth="public", website=True)
    def payment_transaction(self, acquirer_id, **post):
        """ Hook method that creates a payment.transaction and redirect to the
        acquirer, using post values to re-create the post action.

        :param int acquirer_id: id of a payment.acquirer record. If not set the
                                user is redirected to the checkout page
        :param dict post: should coutain all post data for the acquirer
        """
        # @TDEFIXME: don't know why we received those data, but should not be send to the acquirer
        post.pop('submit.x', None)
        post.pop('submit.y', None)
        cr, uid, context = request.cr, request.uid, request.context
        payment_obj = request.registry.get('payment.acquirer')
        transaction_obj = request.registry.get('payment.transaction')
        order = self.get_order()

        if not order or not order.order_line or acquirer_id is None:
            return request.redirect("/shop/checkout/")

        # find an already existing transaction
        tx = context.get('website_sale_transaction')
        if not tx:
            tx_id = transaction_obj.create(cr, SUPERUSER_ID, {
                'acquirer_id': acquirer_id,
                'type': 'form',
                'amount': order.amount_total,
                'currency_id': order.pricelist_id.currency_id.id,
                'partner_id': order.partner_id.id,
                'reference': order.name,
                'sale_order_id': order.id,
            }, context=context)
            request.httprequest.session['website_sale_transaction_id'] = tx_id
        elif tx and tx.state == 'draft':  # button cliked but no more info -> rewrite on tx or create a new one ?
            tx.write({
                'acquirer_id': acquirer_id,
            })

        acquirer_form_post_url = payment_obj.get_form_action_url(cr, uid, acquirer_id, context=context)
        acquirer_total_url = '%s?%s' % (acquirer_form_post_url, werkzeug.url_encode(post))
        request.registry['sale.order'].action_button_confirm(cr, SUPERUSER_ID, [order.id], context=request.context)
        return request.redirect(acquirer_total_url)

    @http.route('/shop/payment/get_status/<int:sale_order_id>', type='json', auth="public", website=True, multilang=True)
    def payment_get_status(self, sale_order_id, **post):
        cr, uid, context = request.cr, request.uid, request.context

        order = request.registry['sale.order'].browse(cr, SUPERUSER_ID, sale_order_id, context=context)
        assert order.website_session_id == request.httprequest.session['website_session_id']

        if not order:
            return {
                'state': 'error',
                'message': '<p>%s</p>' % _('There seems to be an error with your request.'),
            }

        tx_ids = request.registry['payment.transaction'].search(
            cr, SUPERUSER_ID, [
                '|', ('sale_order_id', '=', order.id), ('reference', '=', order.name)
            ], context=context)

        if not tx_ids:
            if order.amount_total:
                return {
                    'state': 'error',
                    'message': '<p>%s</p>' % _('There seems to be an error with your request.'),
                }
            else:
                state = 'done'
                message = ""
                validation = None
        else:
            tx = request.registry['payment.transaction'].browse(cr, SUPERUSER_ID, tx_ids[0], context=context)
            state = tx.state
            if state == 'done':
                message = '<p>%s</p>' % _('Your payment has been received.')
            elif state == 'cancel':
                message = '<p>%s</p>' % _('The payment seems to have been canceled.')
            elif state == 'pending' and tx.acquirer_id.validation == 'manual':
                message = '<p>%s</p>' % _('Your transaction is waiting confirmation.')
                message += tx.acquirer_id.post_msg
            else:
                message = '<p>%s</p>' % _('Your transaction is waiting confirmation.')
            validation = tx.acquirer_id.validation

        return {
            'state': state,
            'message': message,
            'validation': validation
        }

    @http.route('/shop/payment/validate/', type='http', auth="public", website=True, multilang=True)
    def payment_validate(self, transaction_id=None, sale_order_id=None, **post):
        """ Method that should be called by the server when receiving an update
        for a transaction. State at this point :

         - UDPATE ME
        """
        cr, uid, context = request.cr, request.uid, request.context
        sale_order_obj = request.registry['sale.order']
        email_act = None

        if transaction_id is None:
            tx = context.get('website_sale_transaction')
        else:
            tx = request.registry['payment.transaction'].browse(cr, uid, transaction_id, context=context)

        if sale_order_id is None:
            order = self.get_order()
        else:
            order = request.registry['sale.order'].browse(cr, SUPERUSER_ID, sale_order_id, context=context)
            assert order.website_session_id == request.httprequest.session['website_session_id']

        if not order:
            return request.redirect('/shop/')
        elif order.amount_total and not tx:
            return request.redirect('/shop/mycart')

        if not order.amount_total or tx.state == 'done':
            # confirm the quotation
            sale_order_obj.action_button_confirm(cr, SUPERUSER_ID, [order.id], context=request.context)
            # send by email
            email_act = sale_order_obj.action_quotation_send(cr, SUPERUSER_ID, [order.id], context=request.context)
        elif tx.state == 'pending':
            # send by email
            email_act = sale_order_obj.action_quotation_send(cr, SUPERUSER_ID, [order.id], context=request.context)
        elif tx.state == 'cancel':
            # cancel the quotation
            sale_order_obj.action_cancel(cr, SUPERUSER_ID, [order.id], context=request.context)

        # send the email
        if email_act and email_act.get('context'):
            composer_values = {}
            email_ctx = email_act['context']
            public_id = request.registry['website'].get_public_user(cr, uid, context)
            if uid == public_id:
                composer_values['email_from'] = request.registry['res.users'].browse(cr, SUPERUSER_ID, public_id, context=context).company_id.email
            composer_id = request.registry['mail.compose.message'].create(cr, SUPERUSER_ID, composer_values, context=email_ctx)
            request.registry['mail.compose.message'].send_mail(cr, SUPERUSER_ID, [composer_id], context=email_ctx)

        # clean context and session, then redirect to the confirmation page
        request.registry['website'].ecommerce_reset(cr, uid, context=context)

        return request.redirect('/shop/confirmation/%s' % order.id)

    @http.route(['/shop/confirmation/<int:sale_order_id>'], type='http', auth="public", website=True, multilang=True)
    def payment_confirmation(self, sale_order_id, **post):
        """ End of checkout process controller. Confirmation is basically seing
        the status of a sale.order. State at this point :

         - should not have any context / session info: clean them
         - take a sale.order id, because we request a sale.order and are not
           session dependant anymore
        """
        cr, uid, context = request.cr, request.uid, request.context

        order = request.registry['sale.order'].browse(cr, SUPERUSER_ID, sale_order_id, context=context)
        assert order.website_session_id == request.httprequest.session['website_session_id']

        request.registry['website']._ecommerce_change_pricelist(cr, uid, None, context=context or {})

        return request.website.render("website_sale.confirmation", {'order': order})

    @http.route(['/shop/change_sequence/'], type='json', auth="public")
    def change_sequence(self, id, sequence):
        product_obj = request.registry.get('product.template')
        if sequence == "top":
            product_obj.set_sequence_top(request.cr, request.uid, [id], context=request.context)
        elif sequence == "bottom":
            product_obj.set_sequence_bottom(request.cr, request.uid, [id], context=request.context)
        elif sequence == "up":
            product_obj.set_sequence_up(request.cr, request.uid, [id], context=request.context)
        elif sequence == "down":
            product_obj.set_sequence_down(request.cr, request.uid, [id], context=request.context)

    @http.route(['/shop/change_styles/'], type='json', auth="public")
    def change_styles(self, id, style_id):
        product_obj = request.registry.get('product.template')
        product = product_obj.browse(request.cr, request.uid, id, context=request.context)

        remove = []
        active = False
        for style in product.website_style_ids:
            if style.id == style_id:
                remove.append(style.id)
                active = True
                break

        style = request.registry.get('product.style').browse(request.cr, request.uid, style_id, context=request.context)

        if remove:
            product.write({'website_style_ids': [(3, rid) for rid in remove]})
        if not active:
            product.write({'website_style_ids': [(4, style.id)]})

        return not active

    @http.route(['/shop/change_size/'], type='json', auth="public")
    def change_size(self, id, x, y):
        product_obj = request.registry.get('product.template')
        product = product_obj.browse(request.cr, request.uid, id, context=request.context)
        return product.write({'website_size_x': x, 'website_size_y': y})

# vim:expandtab:tabstop=4:softtabstop=4:shiftwidth=4:
