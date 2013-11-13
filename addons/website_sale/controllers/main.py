# -*- coding: utf-8 -*-
import random
import uuid
import simplejson

import werkzeug.exceptions

from openerp import SUPERUSER_ID
from openerp.osv import osv
from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp.addons.website.models import website

def get_order(order_id=None):
    order_obj = request.registry.get('sale.order')
    # check if order allready exists and have access
    if order_id:
        try:
            order = order_obj.browse(request.cr, request.uid, order_id, context=request.context)
            order.pricelist_id
            if order:
                return order
        except:
            return False

    fields = [k for k, v in order_obj._columns.items()]
    order_value = order_obj.default_get(request.cr, SUPERUSER_ID, fields, context=request.context)
    if request.httprequest.session.get('ecommerce_pricelist'):
        order_value['pricelist_id'] = request.httprequest.session['ecommerce_pricelist']
    order_value['partner_id'] = request.registry.get('res.users').browse(request.cr, SUPERUSER_ID, request.uid, context=request.context).partner_id.id
    order_value.update(order_obj.onchange_partner_id(request.cr, SUPERUSER_ID, [], order_value['partner_id'], context=request.context)['value'])

    # add website_session_id key for access rules
    if not request.httprequest.session.get('website_session_id'):
        request.httprequest.session['website_session_id'] = str(uuid.uuid4())

    order_value["website_session_id"] = request.httprequest.session['website_session_id']
    order_id = order_obj.create(request.cr, SUPERUSER_ID, order_value, context=request.context)
    order = order_obj.browse(request.cr, SUPERUSER_ID, order_id, context=request.context)
    request.httprequest.session['ecommerce_order_id'] = order.id

    return order_obj.browse(request.cr, request.uid, order_id,
                            context=dict(request.context, pricelist=order.pricelist_id.id))

def get_current_order():
    if request.httprequest.session.get('ecommerce_order_id'):
        order = get_order(request.httprequest.session.get('ecommerce_order_id'))
        if not order:
            request.httprequest.session['ecommerce_order_id'] = False
        return order
    else:
        return False


class Website(osv.osv):
    _inherit = "website"

    def preprocess_request(self, cr, uid, ids, request, context=None):
        request.context.update({
            'website_sale_order': get_current_order(),
        })
        return super(Website, self).preprocess_request(cr, uid, ids, request, context=None)


class Ecommerce(http.Controller):

    _order = 'website_sequence desc, website_published desc'

    def get_attribute_ids(self):
        attributes_obj = request.registry.get('product.attribute')
        attributes_ids = attributes_obj.search(request.cr, request.uid, [(1, "=", 1)], context=request.context)
        return attributes_obj.browse(request.cr, request.uid, attributes_ids, context=request.context)

    def get_categories(self):
        domain = [('parent_id', '=', False)]

        category_obj = request.registry.get('product.public.category')
        category_ids = category_obj.search(request.cr, SUPERUSER_ID, domain, context=request.context)
        categories = category_obj.browse(request.cr, SUPERUSER_ID, category_ids, context=request.context)

        product_obj = request.registry.get('product.product')
        groups = product_obj.read_group(request.cr, SUPERUSER_ID, [("sale_ok", "=", True), ('website_published', '=', True)], ['public_categ_id'], 'public_categ_id', context=request.context)
        full_category_ids = [group['public_categ_id'][0] for group in groups if group['public_categ_id']]

        for cat_id in category_obj.browse(request.cr, SUPERUSER_ID, full_category_ids, context=request.context):
            while cat_id.parent_id:
                cat_id = cat_id.parent_id
                full_category_ids.append(cat_id.id)
        full_category_ids.append(1)

        return (categories, full_category_ids)

    def get_bin_packing_products(self, product_ids, fill_hole, col_number=4):
        """
        Packing all products of the search into a table of #col_number columns in function of the product sizes
        The website_size_x, website_size_y is use for fill table (default 1x1)
        The website_style_ids datas are concatenate in a html class

        @values:

        product_ids: list of product template
        fill_hole: list of extra product template use to fill the holes
        col_number: number of columns

        @return:

        table (list of list of #col_number items)
        items: {
            'product': browse of product template,
            'x': size x,
            'y': size y,
            'class': html class
        }
        """
        product_obj = request.registry.get('product.template')
        style_obj = request.registry.get('website.product.style')
        request.context['pricelist'] = self.get_pricelist()

        # search for checking of access rules and keep order
        product_ids = product_obj.search(request.cr, request.uid, [("id", 'in', product_ids)], context=request.context)

        size_ids = {}
        style_ids = style_obj.search(request.cr, SUPERUSER_ID, [('html_class', 'like', 'size_%')], context=request.context)
        for style in style_obj.browse(request.cr, SUPERUSER_ID, style_ids, context=request.context):
            size_ids[style.id] = [int(style.html_class[-3]), int(style.html_class[-1])]

        product_list = []
        bin_packing = {}
        bin_packing[0] = {}

        for product in product_obj.browse(request.cr, SUPERUSER_ID, product_ids, context=request.context):
            index = len(product_list)

            # get size and all html classes
            x = product.website_size_x or 1
            y = product.website_size_y or 1
            html_class = " ".join([str(style_id.html_class) for style_id in product.website_style_ids])

            product_list.append({'product': product, 'x': x, 'y': y, 'class': html_class })

            # bin packing products
            insert = False
            line = 0
            while not insert:
                # if not full column get next line
                if len(bin_packing.setdefault(line, {})) >= col_number:
                    line += 1
                    continue

                col = 0
                while col < col_number:
                    if bin_packing[line].get(col, None) != None:
                        col += 1
                        continue

                    insert = True

                    # check if the box can be inserted
                    copy_line = line
                    copy_y = y
                    while copy_y > 0:
                        copy_col = col
                        copy_x = x
                        while copy_x > 0:
                            if copy_col >= col_number or bin_packing.setdefault(copy_line, {}).get(copy_col, None) != None:
                                insert = False
                                break
                            copy_col += 1
                            copy_x -= 1
                        if not insert:
                            break
                        copy_line += 1
                        copy_y -= 1

                    if not insert:
                        col += 1
                        continue

                    # insert the box
                    copy_y = y
                    while copy_y > 0:
                        copy_y -= 1
                        copy_x = x
                        while copy_x > 0:
                            copy_x -= 1
                            bin_packing[line + copy_y][col + copy_x] = False
                    bin_packing[line + copy_y][col + copy_x] = product_list[index]
                    break

                if not insert:
                    line += 1
                else:
                    break

        length = len(bin_packing)

        # browse product to fill the holes
        if fill_hole:
            fill_hole_products = []
            # search for checking of access rules and keep order
            fill_hole = [id for id in fill_hole if id in product_obj.search(request.cr, request.uid, [("id", 'in', fill_hole)], context=request.context)]
            for product in product_obj.browse(request.cr, request.uid, fill_hole, context=request.context):
                fill_hole_products.append(product)
            fill_hole_products.reverse()

        # packaging in list (from dict)
        bin_packing_list = []
        line = 0
        while line < length:
            bin_packing_list.append([])
            col = 0
            while col < col_number:
                if fill_hole and fill_hole_products and bin_packing[line].get(col) == None:
                    bin_packing[line][col] = {'product': fill_hole_products.pop(), 'x': 1, 'y': 1, 'class': "" }
                bin_packing_list[line].append(bin_packing[line].get(col))
                col += 1
            line += 1

        return bin_packing_list

    def get_products(self, product_ids):
        product_obj = request.registry.get('product.template')
        request.context['pricelist'] = self.get_pricelist()
        # search for checking of access rules and keep order
        product_ids = [id for id in product_ids if id in product_obj.search(request.cr, request.uid, [("id", 'in', product_ids)], context=request.context)]
        return product_obj.browse(request.cr, request.uid, product_ids, context=request.context)

    def has_search_filter(self, attribute_id, value_id=None):
        if request.httprequest.args.get('filter'):
            filter = simplejson.loads(request.httprequest.args['filter'])
        else:
            filter = []
        for key_val in filter:
            if key_val[0] == attribute_id and (not value_id or value_id in key_val[1:]):
                return key_val
        return False

    @website.route(['/shop/filter/'], type='http', auth="public", multilang=True)
    def filter(self, add_filter="", **post):
        index = []
        filter = []
        if add_filter:
            filter = simplejson.loads(add_filter)
            for filt in filter:
                index.append(filt[0])
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
                    filter.append([cat_id , [_min, _max] ])
                    index.append(cat_id)
            elif cat_id not in index:
                filter.append([ cat_id, int(cat[2]) ])
                index.append(cat_id)
            else:
                cat[2] = int(cat[2])
                if cat[2] not in filter[index.index(cat_id)][1:]:
                    filter[index.index(cat_id)].append( cat[2] )
            post.pop(key)

        return request.redirect("/shop/?filter=%s%s%s%s" % (
                simplejson.dumps(filter),
                add_filter and "&add_filter=%s" % add_filter or "",
                post.get("search") and "&search=%s" % post.get("search") or "",
                post.get("category") and "&category=%s" % post.get("category") or ""
            ))

    def attributes_to_ids(self, attributes):
        obj = request.registry.get('product.attribute.product')
        domain = [(1, '=', 1)]
        for key_val in attributes:
            domain += [("attribute_id", "=", key_val[0])]
            if isinstance(key_val[1], list):
                domain += [("value", ">=", key_val[1][0]), ("value", "<=", key_val[1][1])]
            else:
                domain += [("value_id", "in", key_val[1:])]
        att_ids = obj.search(request.cr, request.uid, domain, context=request.context)
        att = obj.read(request.cr, request.uid, att_ids, ["product_id"], context=request.context)
        return [r["product_id"][0] for r in att]

    @website.route(['/shop/', '/shop/page/<int:page>/'], type='http', auth="public", multilang=True)
    def category(self, category=0, filter="", page=0, **post):
        # TDE-NOTE: shouldn't we do somethign about product_template without variants ???
        # TDE-NOTE: is there a reason to call a method category when the route is
        # basically a shop without category_id speceified ?

        if 'promo' in post:
            self.change_pricelist(post.get('promo'))
        product_obj = request.registry.get('product.template')

        domain = [("sale_ok", "=", True)]

        if post.get("search"):
            domain += ['|', '|', '|',
                ('name', 'ilike', "%%%s%%" % post.get("search")),
                ('description', 'ilike', "%%%s%%" % post.get("search")),
                ('website_description', 'ilike', "%%%s%%" % post.get("search")),
                ('product_variant_ids.public_categ_id.name', 'ilike', "%%%s%%" % post.get("search"))]

        if category:
            cat_id = int(category)
            domain = [('product_variant_ids.public_categ_id.id', 'child_of', cat_id)] + domain

        if filter:
            filter = simplejson.loads(filter)
            if filter:
                ids = self.attributes_to_ids(filter)
                domain = [('id', 'in', ids or [0] )] + domain

        step = 20
        product_count = len(product_obj.search(request.cr, request.uid, domain, context=request.context))
        pager = request.website.pager(url="/shop/", total=product_count, page=page, step=step, scope=7, url_args=post)

        request.context['pricelist'] = self.get_pricelist()

        product_ids = product_obj.search(request.cr, request.uid, domain, limit=step, offset=pager['offset'], order=self._order, context=request.context)
        fill_hole = product_obj.search(request.cr, request.uid, domain, limit=step, offset=pager['offset']+step, order=self._order, context=request.context)

        styles = []
        if not request.context['is_public_user']:
            style_obj = request.registry.get('website.product.style')
            style_ids = style_obj.search(request.cr, request.uid, [(1, '=', 1)], context=request.context)
            styles = style_obj.browse(request.cr, request.uid, style_ids, context=request.context)

        values = {
            'Ecommerce': self,
            'product_ids': product_ids,
            'product_ids_for_holes': fill_hole,
            'search': {
                'search': post.get('search') or '',
                'category': category,
                'filter': filter or '',
            },
            'pager': pager,
            'styles': styles,
            'style_in_product': lambda style, product: style.id in [s.id for s in product.website_style_ids],
        }
        return request.website.render("website_sale.products", values)

    @website.route(['/shop/product/<model("product.template"):product>/'], type='http', auth="public", multilang=True)
    def product(self, product, search='', category='', filter='', promo=None):

        if promo:
            self.change_pricelist(promo)

        category_obj = request.registry.get('product.public.category')

        category_ids = category_obj.search(request.cr, request.uid, [], context=request.context)
        category_list = category_obj.name_get(request.cr, request.uid, category_ids, context=request.context)
        category_list = sorted(category_list, key=lambda category: category[1])

        if category:
            category = category_obj.browse(request.cr, request.uid, int(category), context=request.context)

        request.context['pricelist'] = self.get_pricelist()

        values = {
            'Ecommerce': self,
            'category': category,
            'category_list': category_list,
            'main_object': product,
            'product': product,
            'search': {
                'search': search,
                'category': category and str(category.id),
                'filter': filter,
            }
        }
        return request.website.render("website_sale.product", values)

    @website.route(['/shop/add_product/', '/shop/category/<int:cat_id>/add_product/'], type='http', auth="public", multilang=True)
    def add_product(self, cat_id=0, **post):
        if request.httprequest.method != 'POST':
            return werkzeug.exceptions.MethodNotAllowed(valid_methods=['POST'])

        Product = request.registry.get('product.product')
        product_id = Product.create(request.cr, request.uid, {
            'name': 'New Product', 'public_categ_id': cat_id
        }, context=request.context)
        product = Product.browse(request.cr, request.uid, product_id, context=request.context)

        return request.redirect("/shop/product/%s/?enable_editor=1" % product.product_tmpl_id.id)

    def get_pricelist(self):
        if not request.httprequest.session.get('ecommerce_pricelist'):
            self.change_pricelist(None)
        return request.httprequest.session.get('ecommerce_pricelist')

    def change_pricelist(self, code):
        request.httprequest.session.setdefault('ecommerce_pricelist', False)

        pricelist_id = False
        if code:
            pricelist_obj = request.registry.get('product.pricelist')
            pricelist_ids = pricelist_obj.search(request.cr, SUPERUSER_ID, [('code', '=', code)], context=request.context)
            if pricelist_ids:
                pricelist_id = pricelist_ids[0]

        if not pricelist_id:
            partner_id = request.registry.get('res.users').browse(request.cr, SUPERUSER_ID, request.uid, request.context).partner_id.id
            pricelist_id = request.registry['sale.order'].onchange_partner_id(request.cr, SUPERUSER_ID, [], partner_id, context=request.context)['value']['pricelist_id']

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
        order_obj = request.registry.get('sale.order')

        order = get_current_order()
        if not order:
            order = get_order()

        request.context = dict(request.context, pricelist=self.get_pricelist())

        quantity = 0

        # values initialisation
        values = {}

        domain = [('order_id', '=', order.id)]
        if order_line_id:
            domain += [('id', '=', order_line_id)]
        else:
            domain += [('product_id', '=', product_id)]

        order_line_ids = order_line_obj.search(request.cr, SUPERUSER_ID, domain, context=request.context)
        if order_line_ids:
            order_line = order_line_obj.read(request.cr, SUPERUSER_ID, order_line_ids, [], context=request.context)[0]
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
            values = order_line_obj.default_get(request.cr, SUPERUSER_ID, fields, context=request.context)
            quantity = 1

        # change and record value
        vals = order_line_obj._recalculate_product_values(request.cr, request.uid, order_line_ids, product_id, context=request.context)
        values.update(vals)

        values['product_uom_qty'] = quantity
        values['product_id'] = product_id
        values['order_id'] = order.id

        if order_line_ids:
            order_line_obj.write(request.cr, SUPERUSER_ID, order_line_ids, values, context=request.context)
            if not quantity:
                order_line_obj.unlink(request.cr, SUPERUSER_ID, order_line_ids, context=request.context)
        else:
            order_line_id = order_line_obj.create(request.cr, SUPERUSER_ID, values, context=request.context)
            order_obj.write(request.cr, SUPERUSER_ID, [order.id], {'order_line': [(4, order_line_id)]}, context=request.context)
        return quantity

    @website.route(['/shop/mycart/'], type='http', auth="public", multilang=True)
    def mycart(self, **post):
        order = get_current_order()
        prod_obj = request.registry.get('product.product')

        if 'promo' in post:
            self.change_pricelist(post.get('promo'))

        suggested_ids = []
        product_ids = []
        if order:
            for line in order.order_line:
                suggested_ids += [p.id for p in line.product_id and line.product_id.suggested_product_ids or []]
                product_ids.append(line.product_id.id)
        suggested_ids = list(set(suggested_ids) - set(product_ids))
        if suggested_ids:
            suggested_ids = prod_obj.search(request.cr, request.uid, [('id', 'in', suggested_ids)], context=request.context)

        # select 3 random products
        suggested_products = []
        while len(suggested_products) < 3 and suggested_ids:
            index = random.randrange(0, len(suggested_ids))
            suggested_products.append(suggested_ids.pop(index))

        values = {
            'int': int,
            'get_categories': self.get_categories,
            'suggested_products': prod_obj.browse(request.cr, request.uid, suggested_products, request.context),
        }
        return request.website.render("website_sale.mycart", values)

    @website.route(['/shop/<path:path>/add_cart/', '/shop/add_cart/'], type='http', auth="public", multilang=True)
    def add_cart(self, path=None, product_id=None, order_line_id=None, remove=None, **kw):
        self.add_product_to_cart(product_id=product_id and int(product_id), order_line_id=order_line_id and int(order_line_id), number=(remove and -1 or 1))
        return request.redirect("/shop/mycart/")

    @website.route(['/shop/add_cart_json/'], type='json', auth="public")
    def add_cart_json(self, product_id=None, order_line_id=None, remove=None):
        quantity = self.add_product_to_cart(product_id=product_id, order_line_id=order_line_id, number=(remove and -1 or 1))
        order = get_current_order()
        return [quantity, order.get_total_quantity(), order.amount_total, request.website.render("website_sale.total", {
                'website_sale_order': order
            }).strip()]

    @website.route(['/shop/set_cart_json/'], type='json', auth="public")
    def set_cart_json(self, path=None, product_id=None, order_line_id=None, set_number=0, json=None):
        return self.add_product_to_cart(product_id=product_id, order_line_id=order_line_id, set_number=set_number)

    @website.route(['/shop/checkout/'], type='http', auth="public", multilang=True)
    def checkout(self, **post):
        classic_fields = ["name", "phone", "email", "street", "city", "state_id", "zip"]
        rel_fields = ['country_id', 'state_id']

        order = get_current_order()

        if not order or order.state != 'draft' or not order.order_line:
            return self.mycart(**post)

        partner_obj = request.registry.get('res.partner')
        user_obj = request.registry.get('res.users')
        country_obj = request.registry.get('res.country')
        country_state_obj = request.registry.get('res.country.state')

        values = {
            'shipping': post.get("shipping"),
            'error': post.get("error") and dict.fromkeys(post.get("error").split(","), 'error') or {}
        }

        checkout = dict((field_name, '') for field_name in classic_fields + rel_fields)
        if not request.context['is_public_user']:
            partner = user_obj.browse(request.cr, request.uid, request.uid, request.context).partner_id
            checkout.update(dict((field_name, getattr(partner, field_name)) for field_name in classic_fields if getattr(partner, field_name)))
            checkout['state_id'] = partner.state_id and partner.state_id.id or ''
            checkout['country_id'] = partner.country_id and partner.country_id.id or ''
            checkout['company'] = partner.parent_id and partner.parent_id.name or ''

            shipping_ids = partner_obj.search(request.cr, request.uid, [("parent_id", "=", partner.id), ('type', "=", 'delivery')], context=request.context)
            if shipping_ids:
                for k, v in partner_obj.read(request.cr, request.uid, shipping_ids[0], request.context).items():
                    checkout['shipping_'+k] = v or ''

        values['checkout'] = checkout
        countries_ids = country_obj.search(request.cr, SUPERUSER_ID, [(1, "=", 1)], context=request.context)
        values['countries'] = country_obj.browse(request.cr, SUPERUSER_ID, countries_ids, request.context)
        states_ids = country_state_obj.search(request.cr, SUPERUSER_ID, [(1, "=", 1)], context=request.context)
        values['states'] = country_state_obj.browse(request.cr, SUPERUSER_ID, states_ids, request.context)

        return request.website.render("website_sale.checkout", values)

    @website.route(['/shop/confirm_order/'], type='http', auth="public", multilang=True)
    def confirm_order(self, **post):
        order = get_current_order()

        error = []
        partner_obj = request.registry.get('res.partner')
        user_obj = request.registry.get('res.users')

        if order.state != 'draft':
            return request.redirect("/shop/checkout/")
        if not order.order_line:
            error.append("empty_cart")
            return request.redirect("/shop/checkout/")

        # check values
        request.session['checkout'] = post
        required_field = ['phone', 'zip', 'email', 'street', 'city', 'name', 'country_id']
        for key in required_field:
            if not post.get(key):
                error.append(key)
            if post.get('shipping_different') and key != 'email' and not post.get("shipping_%s" % key):
                error.append("shipping_%s" % key)
        if error:
            return request.redirect("/shop/checkout/?error=%s&shipping=%s" % (",".join(error), post.get('shipping_different') and 'on' or ''))

        # search or create company
        company_id = None
        if post['company']:
            company_ids = partner_obj.search(request.cr, SUPERUSER_ID, [("name", "ilike", post['company']), ('is_company', '=', True)], context=request.context)
            company_id = company_ids and company_ids[0] or None
            if not company_id:
                company_id = partner_obj.create(request.cr, SUPERUSER_ID, {'name': post['company'], 'is_company': True}, request.context)

        partner_value = {
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
        if not request.context['is_public_user']:
            partner_id = user_obj.browse(request.cr, request.uid, request.uid, context=request.context).partner_id.id
            partner_obj.write(request.cr, request.uid, [partner_id], partner_value, context=request.context)
        else:
            partner_id = partner_obj.create(request.cr, SUPERUSER_ID, partner_value, context=request.context)


        shipping_id = None
        if post.get('shipping_different'):
            shipping_value = {
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

            shipping_ids = partner_obj.search(request.cr, SUPERUSER_ID, domain, context=request.context)
            if shipping_ids:
                shipping_id = shipping_ids[0]
                partner_obj.write(request.cr, SUPERUSER_ID, [shipping_id], shipping_value, request.context)
            else:
                shipping_id = partner_obj.create(request.cr, SUPERUSER_ID, shipping_value, request.context)

        order_value = {
            'partner_id': partner_id,
            'message_follower_ids': [(4, partner_id)],
            'partner_invoice_id': partner_id,
            'partner_shipping_id': shipping_id or partner_id
        }
        order_value.update(request.registry.get('sale.order').onchange_partner_id(request.cr, SUPERUSER_ID, [], order.partner_id.id, context=request.context)['value'])
        order.write(order_value)

        return request.redirect("/shop/payment/")

    @website.route(['/shop/payment/'], type='http', auth="public", multilang=True)
    def payment(self, payment_acquirer_id=None, **post):
        cr, uid, context = request.cr, request.uid, request.context
        payment_obj = request.registry.get('payment.acquirer')
        order = get_current_order()

        if not order or not order.order_line:
            return request.redirect("/shop/checkout/")

        values = {
            'partner': False,
            'payment_acquirer_id': payment_acquirer_id,
            'order': order
        }

        if payment_acquirer_id:
            values['validation'] = self.payment_validation(payment_acquirer_id)
            if values['validation'][0] == "validated" or (values['validation'][0] == "pending" and values['validation'][1] == False):
                return request.redirect("/shop/confirmation/")
            elif values['validation'][0] == "refused":
                values['payment_acquirer_id'] = None

        # fetch all registered payment means
        if not values['payment_acquirer_id']:
            payment_ids = payment_obj.search(request.cr, SUPERUSER_ID, [('portal_published', '=', True)], context=request.context)
            values['payments'] = payment_obj.browse(cr, uid, payment_ids, context=context)
            for pay in values['payments']:
                pay._content = payment_obj.render(
                    cr, uid, pay.id,
                    order.name,
                    order.amount_total,
                    order.pricelist_id.currency_id,
                    context=context)

        return request.website.render("website_sale.payment", values)

    @website.route(['/shop/payment_validation/'], type='json', auth="public", multilang=True)
    def payment_validation(self, payment_acquirer_id=None, **post):
        payment_obj = request.registry.get('payment.acquirer')
        order = get_current_order()
        return payment_obj.validate_payement(request.cr, request.uid, int(payment_acquirer_id), 
            object=order,
            reference=order.name,
            currency=order.pricelist_id.currency_id,
            amount=order.amount_total,
            context=request.context)

    @website.route(['/shop/confirmation/'], type='http', auth="public", multilang=True)
    def payment_confirmation(self, **post):
        order = get_current_order()

        if not order or not order.order_line:
            return request.redirect("/shop/")

        res = request.website.render("website_sale.confirmation", {'order': order})
        request.httprequest.session['ecommerce_order_id'] = False
        request.httprequest.session['ecommerce_pricelist'] = False
        return res

    @website.route(['/shop/change_sequence/'], type='json', auth="public")
    def change_sequence(self, id, top):
        product_obj = request.registry.get('product.template')
        if top:
            product_obj.set_sequence_top(request.cr, request.uid, [id], context=request.context)
        else:
            product_obj.set_sequence_bottom(request.cr, request.uid, [id], context=request.context)

    @website.route(['/shop/change_styles/'], type='json', auth="public")
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

        style = request.registry.get('website.product.style').browse(request.cr, request.uid, style_id, context=request.context)

        if remove:
            product.write({'website_style_ids': [(3, rid) for rid in remove]})
        if not active:
            product.write({'website_style_ids': [(4, style.id)]})

        return not active

    @website.route(['/shop/change_size/'], type='json', auth="public")
    def change_size(self, id, x, y):
        product_obj = request.registry.get('product.template')
        product = product_obj.browse(request.cr, request.uid, id, context=request.context)
        return product.write({'website_size_x': x, 'website_size_y': y})

# vim:expandtab:tabstop=4:softtabstop=4:shiftwidth=4:
