# -*- coding: utf-8 -*-
import werkzeug

from openerp import SUPERUSER_ID
from openerp import http
from openerp.http import request
from openerp.tools.translate import _
from openerp.addons.website.models.website import slug
from openerp.addons.web.controllers.main import login_redirect

PPG = 20 # Products Per Page
PPR = 4  # Products Per Row

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
            if index>=PPG:
                x = y = 1

            pos = minpos
            while not self._check_place(pos%PPR, pos/PPR, x, y):
                pos += 1
            # if 21st products (index 20) and the last line is full (PPR products in it), break
            # (pos + 1.0) / PPR is the line where the product would be inserted
            # maxy is the number of existing lines
            # + 1.0 is because pos begins at 0, thus pos 20 is actually the 21st block
            # and to force python to not round the division operation
            if index >= PPG and ((pos + 1.0) / PPR) > maxy:
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

        # TODO keep with input type hidden


class QueryURL(object):
    def __init__(self, path='', **args):
        self.path = path
        self.args = args

    def __call__(self, path=None, **kw):
        if not path:
            path = self.path
        for k,v in self.args.items():
            kw.setdefault(k,v)
        l = []
        for k,v in kw.items():
            if v:
                if isinstance(v, list) or isinstance(v, set):
                    l.append(werkzeug.url_encode([(k,i) for i in v]))
                else:
                    l.append(werkzeug.url_encode([(k,v)]))
        if l:
            path += '?' + '&'.join(l)
        return path


def get_pricelist():
    cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
    sale_order = context.get('sale_order')
    if sale_order:
        pricelist = sale_order.pricelist_id
    else:
        partner = pool['res.users'].browse(cr, SUPERUSER_ID, uid, context=context).partner_id
        pricelist = partner.property_product_pricelist
    return pricelist

class website_sale(http.Controller):

    def get_pricelist(self):
        return get_pricelist()

    def get_attribute_value_ids(self, product):
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
        currency_obj = pool['res.currency']
        attribute_value_ids = []
        if request.website.pricelist_id.id != context['pricelist']:
            website_currency_id = request.website.currency_id.id
            currency_id = self.get_pricelist().currency_id.id
            for p in product.product_variant_ids:
                price = currency_obj.compute(cr, uid, website_currency_id, currency_id, p.lst_price)
                attribute_value_ids.append([p.id, [v.id for v in p.attribute_value_ids if len(v.attribute_id.value_ids) > 1], p.price, price])
        else:
            attribute_value_ids = [[p.id, [v.id for v in p.attribute_value_ids if len(v.attribute_id.value_ids) > 1], p.price, p.lst_price]
                for p in product.product_variant_ids]

        return attribute_value_ids

    @http.route(['/shop',
        '/shop/page/<int:page>',
        '/shop/category/<model("product.public.category"):category>',
        '/shop/category/<model("product.public.category"):category>/page/<int:page>'
    ], type='http', auth="public", website=True)
    def shop(self, page=0, category=None, search='', **post):
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry

        domain = request.website.sale_product_domain()
        if search:
            for srch in search.split(" "):
                domain += ['|', '|', '|', ('name', 'ilike', srch), ('description', 'ilike', srch),
                    ('description_sale', 'ilike', srch), ('product_variant_ids.default_code', 'ilike', srch)]
        if category:
            domain += [('public_categ_ids', 'child_of', int(category))]

        attrib_list = request.httprequest.args.getlist('attrib')
        attrib_values = [map(int,v.split("-")) for v in attrib_list if v]
        attrib_set = set([v[1] for v in attrib_values])

        if attrib_values:
            attrib = None
            ids = []
            for value in attrib_values:
                if not attrib:
                    attrib = value[0]
                    ids.append(value[1])
                elif value[0] == attrib:
                    ids.append(value[1])
                else:
                    domain += [('attribute_line_ids.value_ids', 'in', ids)]
                    attrib = value[0]
                    ids = [value[1]]
            if attrib:
                domain += [('attribute_line_ids.value_ids', 'in', ids)]

        keep = QueryURL('/shop', category=category and int(category), search=search, attrib=attrib_list)

        if not context.get('pricelist'):
            pricelist = self.get_pricelist()
            context['pricelist'] = int(pricelist)
        else:
            pricelist = pool.get('product.pricelist').browse(cr, uid, context['pricelist'], context)

        product_obj = pool.get('product.template')

        url = "/shop"
        product_count = product_obj.search_count(cr, uid, domain, context=context)
        if search:
            post["search"] = search
        if category:
            category = pool['product.public.category'].browse(cr, uid, int(category), context=context)
            url = "/shop/category/%s" % slug(category)
        pager = request.website.pager(url=url, total=product_count, page=page, step=PPG, scope=7, url_args=post)
        product_ids = product_obj.search(cr, uid, domain, limit=PPG, offset=pager['offset'], order='website_published desc, website_sequence desc', context=context)
        products = product_obj.browse(cr, uid, product_ids, context=context)

        style_obj = pool['product.style']
        style_ids = style_obj.search(cr, uid, [], context=context)
        styles = style_obj.browse(cr, uid, style_ids, context=context)

        category_obj = pool['product.public.category']
        category_ids = category_obj.search(cr, uid, [('parent_id', '=', False)], context=context)
        categs = category_obj.browse(cr, uid, category_ids, context=context)

        attributes_obj = request.registry['product.attribute']
        attributes_ids = attributes_obj.search(cr, uid, [], context=context)
        attributes = attributes_obj.browse(cr, uid, attributes_ids, context=context)

        from_currency = pool.get('product.price.type')._get_field_currency(cr, uid, 'list_price', context)
        to_currency = pricelist.currency_id
        compute_currency = lambda price: pool['res.currency']._compute(cr, uid, from_currency, to_currency, price, context=context)

        values = {
            'search': search,
            'category': category,
            'attrib_values': attrib_values,
            'attrib_set': attrib_set,
            'pager': pager,
            'pricelist': pricelist,
            'products': products,
            'bins': table_compute().process(products),
            'rows': PPR,
            'styles': styles,
            'categories': categs,
            'attributes': attributes,
            'compute_currency': compute_currency,
            'keep': keep,
            'style_in_product': lambda style, product: style.id in [s.id for s in product.website_style_ids],
            'attrib_encode': lambda attribs: werkzeug.url_encode([('attrib',i) for i in attribs]),
        }
        return request.website.render("website_sale.products", values)

    @http.route(['/shop/product/<model("product.template"):product>'], type='http', auth="public", website=True)
    def product(self, product, category='', search='', **kwargs):
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
        category_obj = pool['product.public.category']
        template_obj = pool['product.template']

        context.update(active_id=product.id)

        if category:
            category = category_obj.browse(cr, uid, int(category), context=context)

        attrib_list = request.httprequest.args.getlist('attrib')
        attrib_values = [map(int,v.split("-")) for v in attrib_list if v]
        attrib_set = set([v[1] for v in attrib_values])

        keep = QueryURL('/shop', category=category and category.id, search=search, attrib=attrib_list)

        category_ids = category_obj.search(cr, uid, [], context=context)
        category_list = category_obj.name_get(cr, uid, category_ids, context=context)
        category_list = sorted(category_list, key=lambda category: category[1])

        pricelist = self.get_pricelist()

        from_currency = pool.get('product.price.type')._get_field_currency(cr, uid, 'list_price', context)
        to_currency = pricelist.currency_id
        compute_currency = lambda price: pool['res.currency']._compute(cr, uid, from_currency, to_currency, price, context=context)

        if not context.get('pricelist'):
            context['pricelist'] = int(self.get_pricelist())
            product = template_obj.browse(cr, uid, int(product), context=context)

        values = {
            'search': search,
            'category': category,
            'pricelist': pricelist,
            'attrib_values': attrib_values,
            'compute_currency': compute_currency,
            'attrib_set': attrib_set,
            'keep': keep,
            'category_list': category_list,
            'main_object': product,
            'product': product,
            'get_attribute_value_ids': self.get_attribute_value_ids
        }
        return request.website.render("website_sale.product", values)

    @http.route(['/shop/product/comment/<int:product_template_id>'], type='http', auth="public", methods=['POST'], website=True)
    def product_comment(self, product_template_id, **post):
        if not request.session.uid:
            return login_redirect()
        cr, uid, context = request.cr, request.uid, request.context
        if post.get('comment'):
            request.registry['product.template'].message_post(
                cr, uid, product_template_id,
                body=post.get('comment'),
                type='comment',
                subtype='mt_comment',
                context=dict(context, mail_create_nosubscribe=True))
        return werkzeug.utils.redirect(request.httprequest.referrer + "#comments")

    @http.route(['/shop/pricelist'], type='http', auth="public", website=True)
    def pricelist(self, promo, **post):
        cr, uid, context = request.cr, request.uid, request.context
        request.website.sale_get_order(code=promo, context=context)
        return request.redirect("/shop/cart")

    @http.route(['/shop/cart'], type='http', auth="public", website=True)
    def cart(self, **post):
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
        order = request.website.sale_get_order()
        if order:
            from_currency = pool.get('product.price.type')._get_field_currency(cr, uid, 'list_price', context)
            to_currency = order.pricelist_id.currency_id
            compute_currency = lambda price: pool['res.currency']._compute(cr, uid, from_currency, to_currency, price, context=context)
        else:
            compute_currency = lambda price: price

        values = {
            'order': order,
            'compute_currency': compute_currency,
            'suggested_products': [],
        }
        if order:
            _order = order
            if not context.get('pricelist'):
                _order = order.with_context(pricelist=order.pricelist_id.id)
            values['suggested_products'] = _order._cart_accessories()

        return request.website.render("website_sale.cart", values)

    @http.route(['/shop/cart/update'], type='http', auth="public", methods=['POST'], website=True)
    def cart_update(self, product_id, add_qty=1, set_qty=0, **kw):
        cr, uid, context = request.cr, request.uid, request.context
        request.website.sale_get_order(force_create=1)._cart_update(product_id=int(product_id), add_qty=float(add_qty), set_qty=float(set_qty))
        return request.redirect("/shop/cart")

    @http.route(['/shop/cart/update_json'], type='json', auth="public", methods=['POST'], website=True)
    def cart_update_json(self, product_id, line_id, add_qty=None, set_qty=None, display=True):
        order = request.website.sale_get_order(force_create=1)
        value = order._cart_update(product_id=product_id, line_id=line_id, add_qty=add_qty, set_qty=set_qty)
        if not display:
            return None
        value['cart_quantity'] = order.cart_quantity
        value['website_sale.total'] = request.website._render("website_sale.total", {
                'website_sale_order': request.website.sale_get_order()
            })
        return value

    #------------------------------------------------------
    # Checkout
    #------------------------------------------------------

    def checkout_redirection(self, order):
        cr, uid, context, registry = request.cr, request.uid, request.context, request.registry

        # must have a draft sale order with lines at this point, otherwise reset
        if not order or order.state != 'draft':
            request.session['sale_order_id'] = None
            request.session['sale_transaction_id'] = None
            return request.redirect('/shop')

        # if transaction pending / done: redirect to confirmation
        tx = context.get('website_sale_transaction')
        if tx and tx.state != 'draft':
            return request.redirect('/shop/payment/confirmation/%s' % order.id)

    def checkout_values(self, data=None):
        cr, uid, context, registry = request.cr, request.uid, request.context, request.registry
        orm_partner = registry.get('res.partner')
        orm_user = registry.get('res.users')
        orm_country = registry.get('res.country')
        state_orm = registry.get('res.country.state')

        country_ids = orm_country.search(cr, SUPERUSER_ID, [], context=context)
        countries = orm_country.browse(cr, SUPERUSER_ID, country_ids, context)
        states_ids = state_orm.search(cr, SUPERUSER_ID, [], context=context)
        states = state_orm.browse(cr, SUPERUSER_ID, states_ids, context)
        partner = orm_user.browse(cr, SUPERUSER_ID, request.uid, context).partner_id

        order = None

        shipping_id = None
        shipping_ids = []
        checkout = {}
        if not data:
            if request.uid != request.website.user_id.id:
                checkout.update( self.checkout_parse("billing", partner) )
                shipping_ids = orm_partner.search(cr, SUPERUSER_ID, [("parent_id", "=", partner.id), ('type', "=", 'delivery')], context=context)
            else:
                order = request.website.sale_get_order(force_create=1, context=context)
                if order.partner_id:
                    domain = [("partner_id", "=", order.partner_id.id)]
                    user_ids = request.registry['res.users'].search(cr, SUPERUSER_ID, domain, context=dict(context or {}, active_test=False))
                    if not user_ids or request.website.user_id.id not in user_ids:
                        checkout.update( self.checkout_parse("billing", order.partner_id) )
        else:
            checkout = self.checkout_parse('billing', data)
            try: 
                shipping_id = int(data["shipping_id"])
            except ValueError:
                pass
            if shipping_id == -1:
                checkout.update(self.checkout_parse('shipping', data))

        if shipping_id is None:
            if not order:
                order = request.website.sale_get_order(context=context)
            if order and order.partner_shipping_id:
                shipping_id = order.partner_shipping_id.id

        shipping_ids = list(set(shipping_ids) - set([partner.id]))

        if shipping_id == partner.id:
            shipping_id = 0
        elif shipping_id > 0 and shipping_id not in shipping_ids:
            shipping_ids.append(shipping_id)
        elif shipping_id is None and shipping_ids:
            shipping_id = shipping_ids[0]

        ctx = dict(context, show_address=1)
        shippings = []
        if shipping_ids:
            shippings = shipping_ids and orm_partner.browse(cr, SUPERUSER_ID, list(shipping_ids), ctx) or []
        if shipping_id > 0:
            shipping = orm_partner.browse(cr, SUPERUSER_ID, shipping_id, ctx)
            checkout.update( self.checkout_parse("shipping", shipping) )

        checkout['shipping_id'] = shipping_id

        # Default search by user country
        if not checkout.get('country_id'):
            country_code = request.session['geoip'].get('country_code')
            if country_code:
                country_ids = request.registry.get('res.country').search(cr, uid, [('code', '=', country_code)], context=context)
                if country_ids:
                    checkout['country_id'] = country_ids[0]

        values = {
            'countries': countries,
            'states': states,
            'checkout': checkout,
            'shipping_id': partner.id != shipping_id and shipping_id or 0,
            'shippings': shippings,
            'error': {},
            'has_check_vat': hasattr(registry['res.partner'], 'check_vat')
        }

        return values

    mandatory_billing_fields = ["name", "phone", "email", "street2", "city", "country_id"]
    optional_billing_fields = ["street", "state_id", "vat", "vat_subjected", "zip"]
    mandatory_shipping_fields = ["name", "phone", "street", "city", "country_id"]
    optional_shipping_fields = ["state_id", "zip"]

    def checkout_parse(self, address_type, data, remove_prefix=False):
        """ data is a dict OR a partner browse record
        """
        # set mandatory and optional fields
        assert address_type in ('billing', 'shipping')
        if address_type == 'billing':
            all_fields = self.mandatory_billing_fields + self.optional_billing_fields
            prefix = ''
        else:
            all_fields = self.mandatory_shipping_fields + self.optional_shipping_fields
            prefix = 'shipping_'

        # set data
        if isinstance(data, dict):
            query = dict((prefix + field_name, data[prefix + field_name])
                for field_name in all_fields if data.get(prefix + field_name))
        else:
            query = dict((prefix + field_name, getattr(data, field_name))
                for field_name in all_fields if getattr(data, field_name))
            if address_type == 'billing' and data.parent_id:
                query[prefix + 'street'] = data.parent_id.name

        if query.get(prefix + 'state_id'):
            query[prefix + 'state_id'] = int(query[prefix + 'state_id'])
        if query.get(prefix + 'country_id'):
            query[prefix + 'country_id'] = int(query[prefix + 'country_id'])

        if query.get(prefix + 'vat'):
            query[prefix + 'vat_subjected'] = True

        if not remove_prefix:
            return query

        return dict((field_name, data[prefix + field_name]) for field_name in all_fields if data.get(prefix + field_name))

    def checkout_form_validate(self, data):
        cr, uid, context, registry = request.cr, request.uid, request.context, request.registry

        # Validation
        error = dict()
        for field_name in self.mandatory_billing_fields:
            if not data.get(field_name):
                error[field_name] = 'missing'

        if data.get("vat") and hasattr(registry["res.partner"], "check_vat"):
            if request.website.company_id.vat_check_vies:
                # force full VIES online check
                check_func = registry["res.partner"].vies_vat_check
            else:
                # quick and partial off-line checksum validation
                check_func = registry["res.partner"].simple_vat_check
            vat_country, vat_number = registry["res.partner"]._split_vat(data.get("vat"))
            if not check_func(cr, uid, vat_country, vat_number, context=None): # simple_vat_check
                error["vat"] = 'error'

        if data.get("shipping_id") == -1:
            for field_name in self.mandatory_shipping_fields:
                field_name = 'shipping_' + field_name
                if not data.get(field_name):
                    error[field_name] = 'missing'

        return error

    def checkout_form_save(self, checkout):
        cr, uid, context, registry = request.cr, request.uid, request.context, request.registry

        order = request.website.sale_get_order(force_create=1, context=context)

        orm_partner = registry.get('res.partner')
        orm_user = registry.get('res.users')
        order_obj = request.registry.get('sale.order')

        partner_lang = request.lang if request.lang in [lang.code for lang in request.website.language_ids] else None

        billing_info = {}
        if partner_lang:
            billing_info['lang'] = partner_lang
        billing_info.update(self.checkout_parse('billing', checkout, True))

        # set partner_id
        partner_id = None
        if request.uid != request.website.user_id.id:
            partner_id = orm_user.browse(cr, SUPERUSER_ID, uid, context=context).partner_id.id
        elif order.partner_id:
            user_ids = request.registry['res.users'].search(cr, SUPERUSER_ID,
                [("partner_id", "=", order.partner_id.id)], context=dict(context or {}, active_test=False))
            if not user_ids or request.website.user_id.id not in user_ids:
                partner_id = order.partner_id.id

        # save partner informations
        if partner_id and request.website.partner_id.id != partner_id:
            orm_partner.write(cr, SUPERUSER_ID, [partner_id], billing_info, context=context)
        else:
            # create partner
            partner_id = orm_partner.create(cr, SUPERUSER_ID, billing_info, context=context)

        # create a new shipping partner
        if checkout.get('shipping_id') == -1:
            shipping_info = {}
            if partner_lang:
                shipping_info['lang'] = partner_lang
            shipping_info.update(self.checkout_parse('shipping', checkout, True))
            shipping_info['type'] = 'delivery'
            shipping_info['parent_id'] = partner_id
            checkout['shipping_id'] = orm_partner.create(cr, SUPERUSER_ID, shipping_info, context)

        order_info = {
            'partner_id': partner_id,
            'message_follower_ids': [(4, partner_id), (3, request.website.partner_id.id)],
            'partner_invoice_id': partner_id,
        }
        order_info.update(order_obj.onchange_partner_id(cr, SUPERUSER_ID, [], partner_id, context=context)['value'])
        address_change = order_obj.onchange_delivery_id(cr, SUPERUSER_ID, [], order.company_id.id, partner_id,
                                                        checkout.get('shipping_id'), None, context=context)['value']
        order_info.update(address_change)
        if address_change.get('fiscal_position'):
            fiscal_update = order_obj.onchange_fiscal_position(cr, SUPERUSER_ID, [], address_change['fiscal_position'],
                                                               [(4, l.id) for l in order.order_line], context=None)['value']
            order_info.update(fiscal_update)

        order_info.pop('user_id')
        order_info.update(partner_shipping_id=checkout.get('shipping_id') or partner_id)

        order_obj.write(cr, SUPERUSER_ID, [order.id], order_info, context=context)

    @http.route(['/shop/checkout'], type='http', auth="public", website=True)
    def checkout(self, **post):
        cr, uid, context = request.cr, request.uid, request.context

        order = request.website.sale_get_order(force_create=1, context=context)

        redirection = self.checkout_redirection(order)
        if redirection:
            return redirection

        values = self.checkout_values()

        return request.website.render("website_sale.checkout", values)

    @http.route(['/shop/confirm_order'], type='http', auth="public", website=True)
    def confirm_order(self, **post):
        cr, uid, context, registry = request.cr, request.uid, request.context, request.registry

        order = request.website.sale_get_order(context=context)
        if not order:
            return request.redirect("/shop")

        redirection = self.checkout_redirection(order)
        if redirection:
            return redirection

        values = self.checkout_values(post)

        values["error"] = self.checkout_form_validate(values["checkout"])
        if values["error"]:
            return request.website.render("website_sale.checkout", values)

        self.checkout_form_save(values["checkout"])

        request.session['sale_last_order_id'] = order.id

        request.website.sale_get_order(update_pricelist=True, context=context)

        return request.redirect("/shop/payment")

    #------------------------------------------------------
    # Payment
    #------------------------------------------------------

    @http.route(['/shop/payment'], type='http', auth="public", website=True)
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
        sale_order_obj = request.registry.get('sale.order')

        order = request.website.sale_get_order(context=context)

        redirection = self.checkout_redirection(order)
        if redirection:
            return redirection

        shipping_partner_id = False
        if order:
            if order.partner_shipping_id.id:
                shipping_partner_id = order.partner_shipping_id.id
            else:
                shipping_partner_id = order.partner_invoice_id.id

        values = {
            'order': request.registry['sale.order'].browse(cr, SUPERUSER_ID, order.id, context=context)
        }
        values['errors'] = sale_order_obj._get_errors(cr, uid, order, context=context)
        values.update(sale_order_obj._get_website_data(cr, uid, order, context))

        # fetch all registered payment means
        # if tx:
        #     acquirer_ids = [tx.acquirer_id.id]
        # else:
        if not values['errors']:
            acquirer_ids = payment_obj.search(cr, SUPERUSER_ID, [('website_published', '=', True), ('company_id', '=', order.company_id.id)], context=context)
            values['acquirers'] = list(payment_obj.browse(cr, uid, acquirer_ids, context=context))
            render_ctx = dict(context, submit_class='btn btn-primary', submit_txt=_('Pay Now'))
            for acquirer in values['acquirers']:
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

    @http.route(['/shop/payment/transaction/<int:acquirer_id>'], type='json', auth="public", website=True)
    def payment_transaction(self, acquirer_id):
        """ Json method that creates a payment.transaction, used to create a
        transaction when the user clicks on 'pay now' button. After having
        created the transaction, the event continues and the user is redirected
        to the acquirer website.

        :param int acquirer_id: id of a payment.acquirer record. If not set the
                                user is redirected to the checkout page
        """
        cr, uid, context = request.cr, request.uid, request.context
        transaction_obj = request.registry.get('payment.transaction')
        order = request.website.sale_get_order(context=context)

        if not order or not order.order_line or acquirer_id is None:
            return request.redirect("/shop/checkout")

        assert order.partner_id.id != request.website.partner_id.id

        # find an already existing transaction
        tx = request.website.sale_get_transaction()
        if tx:
            if tx.state == 'draft':  # button cliked but no more info -> rewrite on tx or create a new one ?
                tx.write({
                    'acquirer_id': acquirer_id,
                })
            tx_id = tx.id
        else:
            tx_id = transaction_obj.create(cr, SUPERUSER_ID, {
                'acquirer_id': acquirer_id,
                'type': 'form',
                'amount': order.amount_total,
                'currency_id': order.pricelist_id.currency_id.id,
                'partner_id': order.partner_id.id,
                'partner_country_id': order.partner_id.country_id.id,
                'reference': order.name,
                'sale_order_id': order.id,
            }, context=context)
            request.session['sale_transaction_id'] = tx_id

        # update quotation
        request.registry['sale.order'].write(
            cr, SUPERUSER_ID, [order.id], {
                'payment_acquirer_id': acquirer_id,
                'payment_tx_id': request.session['sale_transaction_id']
            }, context=context)

        return tx_id

    @http.route('/shop/payment/get_status/<int:sale_order_id>', type='json', auth="public", website=True)
    def payment_get_status(self, sale_order_id, **post):
        cr, uid, context = request.cr, request.uid, request.context

        order = request.registry['sale.order'].browse(cr, SUPERUSER_ID, sale_order_id, context=context)
        assert order.id == request.session.get('sale_last_order_id')

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
                if tx.acquirer_id.post_msg:
                    message += tx.acquirer_id.post_msg
            else:
                message = '<p>%s</p>' % _('Your transaction is waiting confirmation.')
            validation = tx.acquirer_id.validation

        return {
            'state': state,
            'message': message,
            'validation': validation
        }

    @http.route('/shop/payment/validate', type='http', auth="public", website=True)
    def payment_validate(self, transaction_id=None, sale_order_id=None, **post):
        """ Method that should be called by the server when receiving an update
        for a transaction. State at this point :

         - UDPATE ME
        """
        cr, uid, context = request.cr, request.uid, request.context
        email_act = None
        sale_order_obj = request.registry['sale.order']

        if transaction_id is None:
            tx = request.website.sale_get_transaction()
        else:
            tx = request.registry['payment.transaction'].browse(cr, uid, transaction_id, context=context)

        if sale_order_id is None:
            order = request.website.sale_get_order(context=context)
        else:
            order = request.registry['sale.order'].browse(cr, SUPERUSER_ID, sale_order_id, context=context)
            assert order.id == request.session.get('sale_last_order_id')

        if not order or (order.amount_total and not tx):
            return request.redirect('/shop')

        if (not order.amount_total and not tx) or tx.state in ['pending', 'done']:
            if (not order.amount_total and not tx):
                # Orders are confirmed by payment transactions, but there is none for free orders,
                # (e.g. free events), so confirm immediately
                order.action_button_confirm()
            # send by email
            email_act = sale_order_obj.action_quotation_send(cr, SUPERUSER_ID, [order.id], context=request.context)
        elif tx and tx.state == 'cancel':
            # cancel the quotation
            sale_order_obj.action_cancel(cr, SUPERUSER_ID, [order.id], context=request.context)

        # send the email
        if email_act and email_act.get('context'):
            composer_values = {}
            email_ctx = email_act['context']
            public_id = request.website.user_id.id
            if uid == public_id:
                composer_values['email_from'] = request.website.user_id.company_id.email
            composer_id = request.registry['mail.compose.message'].create(cr, SUPERUSER_ID, composer_values, context=email_ctx)
            request.registry['mail.compose.message'].send_mail(cr, SUPERUSER_ID, [composer_id], context=email_ctx)

        # clean context and session, then redirect to the confirmation page
        request.website.sale_reset(context=context)

        return request.redirect('/shop/confirmation')

    @http.route(['/shop/confirmation'], type='http', auth="public", website=True)
    def payment_confirmation(self, **post):
        """ End of checkout process controller. Confirmation is basically seing
        the status of a sale.order. State at this point :

         - should not have any context / session info: clean them
         - take a sale.order id, because we request a sale.order and are not
           session dependant anymore
        """
        cr, uid, context = request.cr, request.uid, request.context

        sale_order_id = request.session.get('sale_last_order_id')
        if sale_order_id:
            order = request.registry['sale.order'].browse(cr, SUPERUSER_ID, sale_order_id, context=context)
        else:
            return request.redirect('/shop')

        return request.website.render("website_sale.confirmation", {'order': order})

    #------------------------------------------------------
    # Edit
    #------------------------------------------------------

    @http.route(['/shop/add_product'], type='http', auth="user", methods=['POST'], website=True)
    def add_product(self, name=None, category=0, **post):
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
        if not name:
            name = _("New Product")
        product_obj = request.registry.get('product.product')
        product_id = product_obj.create(cr, uid, { 'name': name, 'public_categ_ids': category }, context=context)
        product = product_obj.browse(cr, uid, product_id, context=context)

        return request.redirect("/shop/product/%s?enable_editor=1" % slug(product.product_tmpl_id))

    @http.route(['/shop/change_styles'], type='json', auth="public")
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

    @http.route(['/shop/change_sequence'], type='json', auth="public")
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

    @http.route(['/shop/change_size'], type='json', auth="public")
    def change_size(self, id, x, y):
        product_obj = request.registry.get('product.template')
        product = product_obj.browse(request.cr, request.uid, id, context=request.context)
        return product.write({'website_size_x': x, 'website_size_y': y})

    def order_lines_2_google_api(self, order_lines):
        """ Transforms a list of order lines into a dict for google analytics """
        ret = []
        for line in order_lines:
            ret.append({
                'id': line.order_id and line.order_id.id,
                'name': line.product_id.categ_id and line.product_id.categ_id.name or '-',
                'sku': line.product_id.id,
                'quantity': line.product_uom_qty,
                'price': line.price_unit,
            })
        return ret

    @http.route(['/shop/tracking_last_order'], type='json', auth="public")
    def tracking_cart(self, **post):
        """ return data about order in JSON needed for google analytics"""
        cr, uid, context = request.cr, request.uid, request.context
        ret = {}
        sale_order_id = request.session.get('sale_last_order_id')
        if sale_order_id:
            order = request.registry['sale.order'].browse(cr, SUPERUSER_ID, sale_order_id, context=context)
            ret['transaction'] = {
                'id': sale_order_id,
                'affiliation': order.company_id.name,
                'revenue': order.amount_total,
                'currency': order.currency_id.name
            }
            ret['lines'] = self.order_lines_2_google_api(order.order_line)
        return ret

# vim:expandtab:tabstop=4:softtabstop=4:shiftwidth=4:
