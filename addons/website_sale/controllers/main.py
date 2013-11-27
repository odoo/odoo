# -*- coding: utf-8 -*-
import random
import simplejson
import urllib

from openerp import SUPERUSER_ID
from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp.addons.website.models import website


class CheckoutInfo(object):
    mandatory_billing_fields = ["name", "phone", "email", "street", "city", "country_id", "zip"]
    optional_billing_fields = ["company", "state_id"]
    string_billing_fields = ["name", "phone", "email", "street", "city", "zip"]
    mandatory_shipping_fields = ["shipping_name", "shipping_phone", "shipping_street", "shipping_city", "shipping_country_id", "shipping_zip"]
    string_shipping_fields = ["shipping_name", "shipping_phone", "shipping_street", "shipping_city", "shipping_zip"]
    optional_shipping_field = ["shipping_state_id"]

    def mandatory_fields(self):
        return self.mandatory_billing_fields + self.mandatory_shipping_fields

    def optional_fields(self):
        return self.optional_billing_fields + self.optional_shipping_field

    def all_fields(self):
        return self.mandatory_fields() + self.optional_fields()

    def empty(self):
        return dict.fromkeys(self.all_fields(), '')

    def from_partner(self, partner):
        result = dict((field_name, getattr(partner, field_name)) for field_name in self.string_billing_fields if getattr(partner, field_name))
        result['state_id'] = partner.state_id and partner.state_id.id or ''
        result['country_id'] = partner.country_id and partner.country_id.id or ''
        result['company'] = partner.parent_id and partner.parent_id.name or ''
        return result

    def from_post(self, post):
        return dict((field_name, post[field_name]) for field_name in self.all_fields() if post[field_name])


class Ecommerce(http.Controller):

    _order = 'website_sequence desc, website_published desc'
    domain = [("sale_ok", "=", True)]

    def get_attribute_ids(self):
        attributes_obj = request.registry.get('product.attribute')
        attributes_ids = attributes_obj.search(request.cr, request.uid, [], context=request.context)
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

    def get_pricelist(self):
        return request.registry.get('website').get_pricelist_id(request.cr, request.uid, None, context=request.context)

    def change_pricelist(self):
        return request.registry.get('website').change_pricelist_id(request.cr, request.uid, None, context=request.context)

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
    def filter(self, **post):
        index = []
        filter = []
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

        return request.redirect("/shop/?filter=%s%s%s" % (
                simplejson.dumps(filter),
                post.get("search") and ("&search=%s" % post.get("search")) or "",
                post.get("category") and ("&category=%s" % post.get("category")) or ""
            ))

    def attributes_to_ids(self, attributes):
        obj = request.registry.get('product.attribute.product')
        domain = []
        for key_val in attributes:
            domain.append(("attribute_id", "=", key_val[0]))
            if isinstance(key_val[1], list):
                domain.append(("value", ">=", key_val[1][0]))
                domain.append(("value", "<=", key_val[1][1]))
            else:
                domain.append(("value_id", "in", key_val[1:]))
        att_ids = obj.search(request.cr, request.uid, domain, context=request.context)
        att = obj.read(request.cr, request.uid, att_ids, ["product_id"], context=request.context)
        return [r["product_id"][0] for r in att]

    @website.route([
        '/shop/',
        '/shop/page/<int:page>/',
        '/shop/category/<int:category>/',
        '/shop/category/<int:category>/page/<int:page>/'
    ], type='http', auth="public", multilang=True)
    def category(self, category=0, page=0, filter='', search='', **post):
        # TDE-NOTE: shouldn't we do somethign about product_template without variants ???
        # TDE-NOTE: is there a reason to call a method category when the route is
        # basically a shop without category_id speceified ?

        if 'promo' in post:
            self.change_pricelist(post.get('promo'))
        product_obj = request.registry.get('product.template')

        domain = list(self.domain)

        # remove product_product_consultant from ecommerce editable mode, this product never be publish
        ref = request.registry.get('ir.model.data').get_object_reference(request.cr, SUPERUSER_ID, 'product', 'product_product_consultant')
        domain.append(("id", "!=", ref[1]))

        if search:
            domain += ['|', '|', '|',
                ('name', 'ilike', "%%%s%%" % search),
                ('description', 'ilike', "%%%s%%" % search),
                ('website_description', 'ilike', "%%%s%%" % search),
                ('product_variant_ids.public_categ_id.name', 'ilike', "%%%s%%" % search)]

        if category:
            domain.append(('product_variant_ids.public_categ_id.id', 'child_of', category))

        if filter:
            filter = simplejson.loads(filter)
            if filter:
                ids = self.attributes_to_ids(filter)
                domain.append(('id', 'in', ids or [0]))

        step = 20
        product_count = product_obj.search_count(request.cr, request.uid, domain, context=request.context)
        pager = request.website.pager(url="/shop/", total=product_count, page=page, step=step, scope=7, url_args=post)

        request.context['pricelist'] = self.get_pricelist()

        product_ids = product_obj.search(request.cr, request.uid, domain, limit=step, offset=pager['offset'], order=self._order, context=request.context)
        fill_hole = product_obj.search(request.cr, request.uid, domain, limit=step, offset=pager['offset']+step, order=self._order, context=request.context)

        styles = []
        if not request.context['is_public_user']:
            style_obj = request.registry.get('website.product.style')
            style_ids = style_obj.search(request.cr, request.uid, [], context=request.context)
            styles = style_obj.browse(request.cr, request.uid, style_ids, context=request.context)

        values = {
            'Ecommerce': self,
            'product_ids': product_ids,
            'product_ids_for_holes': fill_hole,
            'search': {
                'search': search,
                'category': category,
                'filter': filter,
            },
            'pager': pager,
            'styles': styles,
            'style_in_product': lambda style, product: style.id in [s.id for s in product.website_style_ids],
        }
        return request.website.render("website_sale.products", values)

    @website.route(['/shop/product/<model("product.template"):product>/'], type='http', auth="public", multilang=True)
    def product(self, product, search='', category='', filter='', promo=None, **kwargs):

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

    @website.route(['/shop/add_product/', '/shop/category/<int:cat_id>/add_product/'], type='http', auth="user", multilang=True, methods=['POST'])
    def add_product(self, name="New Product", cat_id=0, **post):
        Product = request.registry.get('product.product')
        product_id = Product.create(request.cr, request.uid, {
            'name': name, 'public_categ_id': cat_id
        }, context=request.context)
        product = Product.browse(request.cr, request.uid, product_id, context=request.context)

        return request.redirect("/shop/product/%s/?enable_editor=1" % product.product_tmpl_id.id)

    def add_product_to_cart(self, product_id=0, order_line_id=0, number=1, set_number=-1):
        order_line_obj = request.registry.get('sale.order.line')
        order_obj = request.registry.get('sale.order')

        order = request.registry['website'].get_current_order(request.cr, request.uid, context=request.context)
        if not order:
            order = request.registry['website']._get_order(request.cr, request.uid, context=request.context)

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
        cr, uid, context = request.cr, request.uid, request.context
        prod_obj = request.registry.get('product.product')

        # must have a draft sale order with lines at this point, otherwise reset
        order = context.get('website_sale_order')
        if order and order.state != 'draft':
            request.registry['website'].sale_reset_order(cr, uid, context=context)
            return request.redirect('/shop/')

        if 'promo' in post:
            self.change_pricelist(post.get('promo'))
        else:
            self.get_pricelist()

        suggested_ids = []
        product_ids = []
        if order:
            for line in order.order_line:
                suggested_ids += [p.id for p in line.product_id and line.product_id.suggested_product_ids or []]
                product_ids.append(line.product_id.id)
        suggested_ids = list(set(suggested_ids) - set(product_ids))
        if suggested_ids:
            suggested_ids = prod_obj.search(cr, uid, [('id', 'in', suggested_ids)], context=context)

        # select 3 random products
        suggested_products = []
        while len(suggested_products) < 3 and suggested_ids:
            index = random.randrange(0, len(suggested_ids))
            suggested_products.append(suggested_ids.pop(index))

        values = {
            'int': int,
            'get_categories': self.get_categories,
            'suggested_products': prod_obj.browse(cr, uid, suggested_products, context),
        }
        return request.website.render("website_sale.mycart", values)

    @website.route(['/shop/add_cart/'], type='http', auth="public", multilang=True)
    def add_cart(self, product_id=None, order_line_id=None, remove=None, **kw):
        self.add_product_to_cart(product_id=product_id and int(product_id), order_line_id=order_line_id and int(order_line_id), number=(remove and -1 or 1))
        return request.redirect("/shop/mycart/")

    @website.route(['/shop/add_cart_json/'], type='json', auth="public")
    def add_cart_json(self, product_id=None, order_line_id=None, remove=None):
        quantity = self.add_product_to_cart(product_id=product_id, order_line_id=order_line_id, number=(remove and -1 or 1))
        order = request.registry['website'].get_current_order(request.cr, request.uid, context=request.context)
        return [quantity,
                order.get_total_quantity(),
                order.amount_total,
                request.website._render("website_sale.total", {'website_sale_order': order})]

    @website.route(['/shop/set_cart_json/'], type='json', auth="public")
    def set_cart_json(self, path=None, product_id=None, order_line_id=None, set_number=0, json=None):
        return self.add_product_to_cart(product_id=product_id, order_line_id=order_line_id, set_number=set_number)

    @website.route(['/shop/checkout/'], type='http', auth="public", multilang=True)
    def checkout(self, **post):
        cr, uid, context, registry = request.cr, request.uid, request.context, request.registry

        # must have a draft sale order with lines at this point, otherwise reset
        order = context.get('website_sale_order')
        if not order or order.state != 'draft' or not order.order_line:
            request.registry['website'].sale_reset_order(cr, uid, context=context)
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
        error = values['error']

        if not context['is_public_user']:
            partner = orm_user.browse(cr, uid, uid, context).partner_id
            partner_info = info.from_partner(partner)
            checkout.update(partner_info)
            shipping_ids = orm_partner.search(cr, uid, [("parent_id", "=", partner.id), ('type', "=", 'delivery')], context=context)
            if shipping_ids:
                values['shipping'] = "true"
                shipping_partner = orm_partner.browse(cr, uid, shipping_ids[0], context)
                checkout['shipping_name'] = getattr(shipping_partner, 'name')
                checkout['shipping_phone'] = getattr(shipping_partner, 'phone')
                checkout['shipping_street'] = getattr(shipping_partner, 'street')
                checkout['shipping_zip'] = getattr(shipping_partner, 'zip')
                checkout['shipping_city'] = getattr(shipping_partner, 'city')
                checkout['shipping_country_id'] = getattr(shipping_partner, 'country_id')
                checkout['shipping_state_id'] = getattr(shipping_partner, 'state_id')

        for field_name in info.mandatory_fields():
            if not checkout[field_name]:
                error[field_name] = 'missing'

        return request.website.render("website_sale.checkout", values)

    @website.route(['/shop/confirm_order/'], type='http', auth="public", multilang=True)
    def confirm_order(self, **post):
        cr, uid, context, registry = request.cr, request.uid, request.context, request.registry

        # must have a draft sale order with lines at this point, otherwise redirect to shop
        order = request.registry['website'].get_current_order(request.cr, request.uid, context=request.context)
        if not order or order.state != 'draft' or not order.order_line:
            request.registry['website'].sale_reset_order(cr, uid, context=context)
            return request.redirect('/shop/')
        # if transaction pending / done: redirect to confirmation
        tx = context.get('website_sale_transaction')
        if tx and tx.state != 'draft':
            return request.redirect('/shop/payment/confirmation/%s' % order.id)

        orm_parter = registry.get('res.partner')
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

        company_name = checkout['company']
        company_id = None
        if post['company']:
            company_ids = orm_parter.search(cr, SUPERUSER_ID, [("name", "ilike", company_name), ('is_company', '=', True)], context=context)
            company_id = (company_ids and company_ids[0]) or orm_parter.create(cr, SUPERUSER_ID, {'name': company_name, 'is_company': True}, context)

        billing_info = dict(checkout)
        billing_info['parent_id'] = company_id

        if not context['is_public_user']:
            partner_id = orm_user.browse(cr, uid, uid, context=context).partner_id.id
            orm_parter.write(cr, uid, [partner_id], billing_info, context=context)
        else:
            partner_id = orm_parter.create(cr, SUPERUSER_ID, billing_info, context=context)

        shipping_id = None
        if post.get('shipping_different'):
            shipping_info = {
                'phone': post['shipping_phone'],
                'zip': post['shipping_zip'],
                'street': post['shipping_street'],
                'city': post['shipping_city'],
                'name': post['shipping_name'],
                'email': post['email'],
                'type': 'delivery',
                'parent_id': partner_id,
                'country_id': post['shipping_country_id'],
                'state_id': post['shipping_state_id'],
            }
            domain = [(key, '_id' in key and '=' or 'ilike', '_id' in key and value and int(value) or False)
                for key, value in shipping_info.items() if key in info.mandatory_billing_fields + ["type", "parent_id"]]

            shipping_ids = orm_parter.search(cr, SUPERUSER_ID, domain, context=context)
            if shipping_ids:
                shipping_id = shipping_ids[0]
                orm_parter.write(cr, SUPERUSER_ID, [shipping_id], shipping_info, context)
            else:
                shipping_id = orm_parter.create(cr, SUPERUSER_ID, shipping_info, context)

        order_info = {
            'partner_id': partner_id,
            'message_follower_ids': [(4, partner_id)],
            'partner_invoice_id': partner_id,
            'partner_shipping_id': shipping_id or partner_id
        }
        order_info.update(registry.get('sale.order').onchange_partner_id(cr, SUPERUSER_ID, [], order.partner_id.id, context=context)['value'])
        order.write(order_info)

        return request.redirect("/shop/payment/")

    @website.route(['/shop/payment/'], type='http', auth="public", multilang=True)
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

        # if no sale order at this stage: back to checkout beginning
        order = context.get('website_sale_order')
        if not order or not order.state == 'draft' or not order.order_line:
            request.registry['website'].sale_reset_order(cr, uid, context=context)
            return request.redirect("/shop/")
        # alread a transaction: forward to confirmation
        tx = context.get('website_sale_transaction')
        if tx and not tx.state == 'draft':
            print 'embetatn'
            # return request.redirect('/shop/confirmation/%s' % order.id)

        partner_id = False
        shipping_partner_id = False
        if order:
            if order.partner_id.id:
                partner_id = order.partner_id.id
                shipping_partner_id = order.partner_id.id
            if order.partner_shipping_id.id:
                shipping_partner_id = order.partner_shipping_id.id

        values = {
            'partner': partner_id,
            'order': order
        }
        values.update(request.registry.get('sale.order')._get_website_data(cr, uid, order, context))

        # fetch all registered payment means
        if tx:
            payment_ids = [tx.acquirer_id.id]
        else:
            payment_ids = payment_obj.search(cr, SUPERUSER_ID, [('portal_published', '=', True)], context=context)
        values['payments'] = payment_obj.browse(cr, uid, payment_ids, context=context)
        for pay in values['payments']:
            pay._content = payment_obj.render(
                cr, uid, pay.id,
                order.name,
                order.amount_total,
                order.pricelist_id.currency_id,
                partner_id=shipping_partner_id,
                tx_custom_values={
                    'return_url': '/shop/payment/validate',
                },
                context=context)

        return request.website.render("website_sale.payment", values)

    @website.route(['/shop/payment/transaction/<int:acquirer_id>'],
                   type='http', methods=['POST'], auth="public")
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
        order = request.registry['website'].get_current_order(request.cr, request.uid, context=request.context)

        if not order or not order.order_line or acquirer_id is None:
            return request.redirect("/shop/checkout/")

        # find an already existing transaction
        tx = context.get('website_sale_transaction')
        if not tx:
            tx_id = transaction_obj.create(cr, uid, {
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
        acquirer_total_url = '%s?%s' % (acquirer_form_post_url, urllib.urlencode(post))
        return request.redirect(acquirer_total_url)

    @website.route('/shop/payment/get_status/<model("sale.order"):order>', type='json', auth="public", multilang=True)
    def payment_get_status(self, order, **post):
        cr, uid, context = request.cr, request.uid, request.context
        if not order:
            return {
                'state': 'error',
            }

        tx_ids = request.registry['payment.transaction'].search(
            cr, uid, [
                '|', ('sale_order_id', '=', order.id), ('reference', '=', order.name)
            ], context=context)
        if not tx_ids:
            return {
                'state': 'error'
            }
        tx = request.registry['payment.transaction'].browse(cr, uid, tx_ids[0], context=context)
        return {
            'state': tx.state,
        }

    @website.route('/shop/payment/validate/', type='http', auth="public", multilang=True)
    def payment_validate(self, transaction_id=None, sale_order_id=None, **post):
        """ Method that should be called by the server when receiving an update
        for a transaction. State at this point :

         - UDPATE ME
        """
        cr, uid, context = request.cr, request.uid, request.context
        email_act = None
        sale_order_obj = request.registry['sale.order']

        if transaction_id is None:
            tx = context.get('website_sale_transaction')
        else:
            tx = request.registry['payment.transaction'].browse(cr, uid, transaction_id, context=context)

        if sale_order_id is None:
            order = context.get('website_sale_order')
        else:
            order = request.registry['sale.order'].browse(cr, uid, sale_order_id, context=context)

        if tx.state == 'done':
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

        if email_act:
            create_ctx = email_act.get('context', context)
            compose_id = request.registry['mail.compose.message'].create(cr, uid, {}, context=create_ctx)
            request.registry['mail.compose.message'].send_mail(cr, uid, [compose_id], context=create_ctx)

        # clean context and session, then redirect to the confirmation page
        request.registry['website'].sale_reset_order(cr, uid, context=context)

        return request.redirect('/shop/confirmation/%s' % order.id)

    @website.route(['/shop/confirmation/<model("sale.order"):order>'], type='http', auth="public", multilang=True)
    def payment_confirmation(self, order, **post):
        """ End of checkout process controller. Confirmation is basically seing
        the status of a sale.order. State at this point :

         - should not have any context / session info: clean them
         - take a sale.order id, because we request a sale.order and are not
           session dependant anymore
        """
        cr, uid, context = request.cr, request.uid, request.context

        return request.website.render("website_sale.confirmation", {'order': order})

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
