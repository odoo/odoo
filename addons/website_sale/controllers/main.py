# -*- coding: utf-8 -*-
import werkzeug

from openerp import http, tools, _
from openerp.http import request
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
    sale_order = request.context.get('sale_order')
    if sale_order:
        pricelist = sale_order.pricelist_id
    else:
        pricelist = request.env.user.sudo().partner_id.property_product_pricelist
    return pricelist


class WebsiteSale(http.Controller):

    def get_pricelist(self):
        return get_pricelist()

    def get_attribute_value_ids(self, product):
        attribute_value_ids = []
        visible_attrs = set(l.attribute_id.id
                                for l in product.attribute_line_ids
                                    if len(l.value_ids) > 1)
        if request.website.pricelist_id.id != request.context['pricelist']:
            website_currency_id = request.website.currency_id.id
            currency_id = self.get_pricelist().currency_id.id
            for p in product.product_variant_ids:
                price = website_currency_id.compute(currency_id, p.lst_price)
                attribute_value_ids.append([p.id, [v.id for v in p.attribute_value_ids if v.attribute_id.id in visible_attrs], p.price, price])
        else:
            attribute_value_ids = [[p.id, [v.id for v in p.attribute_value_ids if v.attribute_id.id in visible_attrs], p.price, p.lst_price]
                for p in product.product_variant_ids]

        return attribute_value_ids

    @http.route(['/shop',
        '/shop/page/<int:page>',
        '/shop/category/<model("product.public.category"):category>',
        '/shop/category/<model("product.public.category"):category>/page/<int:page>'
    ], type='http', auth="public", website=True)
    def shop(self, page=0, category=None, search='', **post):
        local_context = request.context
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
        if not local_context.get('pricelist'):
            pricelist = self.get_pricelist()
            local_context['pricelist'] = int(pricelist)
        else:
            pricelist = request.env['product.pricelist'].browse(local_context['pricelist'])
        url = "/shop"
        if search:
            post["search"] = search
        if category:
            category = request.env['product.public.category'].with_context(local_context).browse(int(category))
            url = "/shop/category/%s" % slug(category)
        if attrib_list:
            post['attrib'] = attrib_list

        ProductTemplate = request.env['product.template']

        parent_category_ids = []
        if category:
            parent_category_ids = [category.id]
            current_category = category
            while current_category.parent_id:
                parent_category_ids.append(current_category.parent_id.id)
                current_category = current_category.parent_id

        product_count = ProductTemplate.search_count(domain)
        pager = request.website.pager(url=url, total=product_count, page=page, step=PPG, scope=7, url_args=post)
        products = ProductTemplate.with_context(local_context).search(domain, limit=PPG, offset=pager['offset'], order='website_published desc, website_sequence desc')
        from_currency = request.env['product.price.type'].search([('field', '=', 'list_price')], limit=1)
        to_currency = pricelist.currency_id
        compute_currency = lambda price: request.env['res.currency']._compute(from_currency, to_currency, price)
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
            'styles': request.env['product.style'].search([]),
            'categories': request.env['product.public.category'].search([('parent_id', '=', False)]),
            'attributes': request.env['product.attribute'].search([]),
            'compute_currency': compute_currency,
            'keep': keep,
            'parent_category_ids': parent_category_ids,
            'style_in_product': lambda style, product: style.id in [s.id for s in product.website_style_ids],
            'attrib_encode': lambda attribs: werkzeug.url_encode([('attrib',i) for i in attribs]),
        }
        if category:
            values['main_object'] = category
        return request.website.render("website_sale.products", values)

    @http.route(['/shop/product/<model("product.template"):product>'], type='http', auth="public", website=True)
    def product(self, product, category='', search='', **kwargs):
        Category = request.env['product.public.category']

        if category:
            category = Category.browse(int(category))

        attrib_list = request.httprequest.args.getlist('attrib')
        attrib_values = [map(int,v.split("-")) for v in attrib_list if v]
        attrib_set = set([v[1] for v in attrib_values])

        keep = QueryURL('/shop', category=category and category.id, search=search, attrib=attrib_list)

        pricelist = self.get_pricelist()

        from_currency = request.env['product.price.type'].search([('field', '=', 'list_price')], limit=1)
        to_currency = pricelist.currency_id
        compute_currency = lambda price: request.env['res.currency']._compute(from_currency, to_currency, price)

        if not request.context.get('pricelist'):
            request.context['pricelist'] = pricelist.id
            product = request.env['product.template'].with_context(pricelist=pricelist.id).browse(int(product))

        values = {
            'search': search,
            'category': category,
            'pricelist': pricelist,
            'attrib_values': attrib_values,
            'compute_currency': compute_currency,
            'attrib_set': attrib_set,
            'keep': keep,
            'categories': Category.search([('parent_id', '=', False)]),
            'main_object': product,
            'product': product,
            'get_attribute_value_ids': self.get_attribute_value_ids
        }
        return request.website.render("website_sale.product", values)

    @http.route(['/shop/product/comment/<int:product_template_id>'], type='http', auth="public", website=True)
    def product_comment(self, product_template_id, **post):
        if not request.session.uid:
            return login_redirect()
        if post.get('comment'):
            request.env['product.template'].browse(product_template_id).with_context(mail_create_nosubscribe=True).message_post(
                body=post.get('comment'),
                type='comment',
                subtype='mt_comment',
                context=dict(context, mail_create_nosubscribe=True))
        return werkzeug.utils.redirect('/shop/product/%s#comments' % product_template_id)

    @http.route(['/shop/pricelist'], type='http', auth="public", website=True)
    def pricelist(self, promo, **post):
        request.website.sale_get_order(code=promo)
        return request.redirect("/shop/cart")

    @http.route(['/shop/cart'], type='http', auth="public", website=True)
    def cart(self, **post):
        order = request.website.sale_get_order()
        if order:
            from_currency = request.env['product.price.type'].search([('field', '=', 'list_price')], limit=1)
            to_currency = order.pricelist_id.currency_id
            compute_currency = lambda price: request.env['res.currency']._compute(from_currency, to_currency, price)
        else:
            compute_currency = lambda price: price

        values = {
            'website_sale_order': order,
            'compute_currency': compute_currency,
            'suggested_products': [],
        }
        if order:
            _order = order
            if not request.context.get('pricelist'):
                _order = order.with_context(pricelist=order.pricelist_id.id)
            values['suggested_products'] = _order._cart_accessories()
        return request.website.render("website_sale.cart", values)

    @http.route(['/shop/cart/update'], type='http', auth="public", methods=['POST'], website=True)
    def cart_update(self, product_id, add_qty=1, set_qty=0, **kw):
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

    @http.route([
        '/shop/orders',
        '/shop/orders/page/<int:page>',
    ], type='http', auth="user", website=True)
    def orders_followup(self, page=1, by = 5, **post):
        partner = request.env.user.partner_id
        orders = request.env['sale.order'].sudo().search([('partner_id', '=', partner.id), ('state', 'not in', ['draft', 'cancel'])])
        nbr_pages = max((len(orders) / by) + (1 if len(orders) % by > 0 else 0), 1)
        page = min(page, nbr_pages)
        pager = request.website.pager(
            url='/shop/orders', total=nbr_pages, page=page, step=1,
            scope=by, url_args=post
        )
        orders = orders[by*(page-1):by*(page-1)+by]

        order_invoice_lines = {}
        for o in orders:
            invoiced_lines = request.env['account.invoice.line'].sudo().search([('invoice_id', 'in', o.invoice_ids.ids)])
            order_invoice_lines[o.id] = {il.product_id.id: il.invoice_id for il in invoiced_lines}

        return request.website.render("website_sale.orders_followup", {
            'orders': orders,
            'order_invoice_lines': order_invoice_lines,
            'pager': pager,
        })

    #------------------------------------------------------
    # Checkout
    #------------------------------------------------------

    def checkout_redirection(self, order):
        # must have a draft sale order with lines at this point, otherwise reset
        if not order or order.state != 'draft':
            request.session['sale_order_id'] = None
            request.session['sale_transaction_id'] = None
            return request.redirect('/shop')

        # if transaction pending / done: redirect to confirmation
        tx = request.context.get('website_sale_transaction')
        if tx and tx.state != 'draft':
            return request.redirect('/shop/payment/confirmation/%s' % order.id)

    def checkout_values(self, data=None):
        Partner = request.env['res.partner'].sudo()

        partner = request.env.user.partner_id

        order = None

        shipping_id = data and data.get('shipping_id') or None
        shipping_ids = []
        checkout = {}
        if not data:
            if request.uid != request.website.user_id.id:
                checkout.update(self.checkout_parse("billing", partner))
                shippings = Partner.sudo().search([("parent_id", "=", partner.id), ('type', "=", 'delivery')])
                shipping_ids = (shippings - partner).ids
            else:
                order = request.website.sale_get_order(force_create=1)
                if order.partner_id:
                    user = request.env['res.users'].sudo().with_context(active_test=False).search([("partner_id", "=", order.partner_id.id)])
                    if not user or request.website.user_id.id not in user.ids:
                        checkout.update(self.checkout_parse("billing", order.partner_id))
        else:
            checkout = self.checkout_parse('billing', data)
            try:
                shipping_id = int(shipping_id)
            except (ValueError, TypeError):
                pass
            if shipping_id == -1:
                checkout.update(self.checkout_parse('shipping', data))

        if shipping_id is None:
            if not order:
                order = request.website.sale_get_order()
            if order and order.partner_shipping_id:
                shipping_id = order.partner_shipping_id.id

        if shipping_id == partner.id:
            shipping_id = 0
        elif shipping_id > 0 and shipping_id not in shipping_ids:
            shipping_ids.append(shipping_id)
        elif shipping_id is None and shipping_ids:
            shipping_id = shipping_ids[0]

        shippings = []
        if shipping_ids:
            shippings = shipping_ids and Partner.with_context(show_address=1).browse(list(shipping_ids))
        if shipping_id > 0:
            shipping = Partner.with_context(show_address=1).browse(shipping_id)
            checkout.update(self.checkout_parse("shipping", shipping))

        checkout['shipping_id'] = shipping_id

        # Default search by user country
        if not checkout.get('country_id'):
            country_code = request.session['geoip'].get('country_code')
            if country_code:
                country = request.env['res.country'].search([('code', '=', country_code)], limit=1)
                if country:
                    checkout['country_id'] = country.id

        values = {
            'countries': request.env['res.country'].sudo().search([]),
            'states': request.env['res.country.state'].sudo().search([]),
            'checkout': checkout,
            'shipping_id': partner.id != shipping_id and shipping_id or 0,
            'shippings': shippings,
            'error': {},
            'has_check_vat': hasattr(request.env['res.partner'], 'check_vat'),
            'only_services': order and order.only_services or False
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

        error = dict()
        error_message = []

        # Validation
        for field_name in self.mandatory_billing_fields:
            if not data.get(field_name):
                error[field_name] = 'missing'

        # email validation
        if data.get('email') and not tools.single_email_re.match(data.get('email')):
            error["email"] = 'error'
            error_message.append(_('Invalid Email! Please enter a valid email address.'))

        # vat validation
        if data.get("vat") and hasattr(request.env["res.partner"], "check_vat"):
            if request.website.company_id.vat_check_vies:
                # force full VIES online check
                check_func = request.env["res.partner"].vies_vat_check
            else:
                # quick and partial off-line checksum validation
                check_func = request.env["res.partner"].simple_vat_check
            vat_country, vat_number = request.env["res.partner"]._split_vat(data.get("vat"))
            if not check_func(vat_country, vat_number): # simple_vat_check
                error["vat"] = 'error'

        if data.get("shipping_id") == -1:
            for field_name in self.mandatory_shipping_fields:
                field_name = 'shipping_' + field_name
                if not data.get(field_name):
                    error[field_name] = 'missing'

        # error message for empty required fields
        if [err for err in error.values() if err == 'missing']:
            error_message.append(_('Some required fields are empty.'))

        return error, error_message

    def checkout_form_save(self, checkout):
        order = request.website.sale_get_order(force_create=1)

        Partner = request.env['res.partner'].sudo()
        partner_lang = request.lang if request.lang in request.website.mapped('language_ids.code') else None

        billing_info = {}
        if partner_lang:
            billing_info['lang'] = partner_lang
        billing_info.update(self.checkout_parse('billing', checkout, True))

        # set partner
        partner = None
        if request.uid != request.website.user_id.id:
            partner = request.env.user.sudo().partner_id
        elif order.partner_id:
            user = request.env['res.users'].sudo().with_context(active_test=False).search(
                [("partner_id", "=", order.partner_id.id)])
            if not user or request.website.user_id.id not in user.ids:
                partner = order.partner_id

        # save partner informations
        if partner and request.website.partner_id.id != partner.id:
            partner.sudo().write(billing_info)
        else:
            # create partner
            billing_info['team_id'] = request.env.ref('website.salesteam_website_sales').id
            partner = Partner.create(billing_info)

        # create a new shipping partner
        if checkout.get('shipping_id') == -1:
            shipping_info = {}
            if partner_lang:
                shipping_info['lang'] = partner_lang
            shipping_info.update(self.checkout_parse('shipping', checkout, True))
            shipping_info['type'] = 'delivery'
            shipping_info['parent_id'] = partner.id
            checkout['shipping_id'] = Partner.create(shipping_info)

        order_info = {
            'partner_id': partner.id,
            'message_follower_ids': [(4, partner.id), (3, request.website.partner_id.id)],
            'partner_invoice_id': partner.id,
        }
        SaleOrder = request.env['sale.order'].sudo()
        order_info.update(SaleOrder.onchange_partner_id(partner.id)['value'])
        address_change = SaleOrder.onchange_delivery_id(order.company_id.id, partner.id,
                                                        checkout.get('shipping_id'), None)['value']
        order_info.update(address_change)
        if address_change.get('fiscal_position'):
            fiscal_update = order.sudo().onchange_fiscal_position([], address_change['fiscal_position'],
                                                               [(4, l.id) for l in order.order_line])['value']
            order_info.update(fiscal_update)

        order_info.pop('user_id')
        order_info.update(partner_shipping_id=checkout.get('shipping_id') or partner.id)

        order.sudo().write(order_info)

    @http.route(['/shop/checkout'], type='http', auth="public", website=True)
    def checkout(self, **post):

        order = request.website.sale_get_order(force_create=1)

        redirection = self.checkout_redirection(order)
        if redirection:
            return redirection

        values = self.checkout_values()

        return request.website.render("website_sale.checkout", values)

    @http.route(['/shop/confirm_order'], type='http', auth="public", website=True)
    def confirm_order(self, **post):

        order = request.website.sale_get_order()
        if not order:
            return request.redirect("/shop")

        redirection = self.checkout_redirection(order)
        if redirection:
            return redirection

        values = self.checkout_values(post)

        values["error"], values["error_message"] = self.checkout_form_validate(values["checkout"])
        if values["error"]:
            return request.website.render("website_sale.checkout", values)

        self.checkout_form_save(values["checkout"])

        request.session['sale_last_order_id'] = order.id

        request.website.sale_get_order(update_pricelist=True)

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
        Payment = request.env['payment.acquirer'].sudo()
        SaleOrder = request.env['sale.order']

        order = request.website.sale_get_order()

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
            'website_sale_order': order
        }
        values['errors'] = order._get_errors()
        values.update(order._get_website_data())

        # fetch all registered payment means
        # if tx:
        #     acquirer_ids = [tx.acquirer_id.id]
        # else:
        if not values['errors']:
            values['acquirers'] = Payment.search([('website_published', '=', True), ('company_id', '=', order.company_id.id)])
            values['buttons'] = {acquirer.id: acquirer.with_context(submit_class='btn btn-primary', submit_txt=_('Pay Now')).render(
                order.name,
                order.amount_total,
                order.pricelist_id.currency_id.id,
                partner_id=shipping_partner_id,
                tx_values={
                    'return_url': '/shop/payment/validate',
                },
                )[0] for acquirer in values['acquirers']}
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
        Transaction = request.env['payment.transaction']
        order = request.website.sale_get_order()

        if not order or not order.order_line or acquirer_id is None:
            return request.redirect("/shop/checkout")

        assert order.partner_id.id != request.website.partner_id.id

        # find an already existing transaction
        tx = request.website.sale_get_transaction()
        if tx:
            if tx.state == 'draft':  # button cliked but no more info -> rewrite on tx or create a new one ?
                tx.acquirer_id = acquirer_id
        else:
            tx = Transaction.sudo().create({
                'acquirer_id': acquirer_id,
                'type': 'form',
                'amount': order.amount_total,
                'currency_id': order.pricelist_id.currency_id.id,
                'partner_id': order.partner_id.id,
                'partner_country_id': order.partner_id.country_id.id,
                'reference': order.name,
                'sale_order_id': order.id,
            })
            request.session['sale_transaction_id'] = tx.id

        # update quotation
        order.sudo().write({
            'payment_acquirer_id': acquirer_id,
            'payment_tx_id': request.session['sale_transaction_id']
        })

        # confirm the quotation
        if tx.acquirer_id.auto_confirm == 'at_pay_now':
            order.sudo().action_button_confirm()

        return tx.id

    @http.route('/shop/payment/get_status/<int:sale_order_id>', type='json', auth="public", website=True)
    def payment_get_status(self, sale_order_id, **post):

        order = request.env['sale.order'].sudo().browse(sale_order_id)
        assert order.id == request.session.get('sale_last_order_id')

        values = {}
        flag = False
        if not order:
            values.update({'not_order': True, 'state': 'error'})
        else:
            tx = request.env['payment.transaction'].sudo().search(
                [
                    '|', ('sale_order_id', '=', order.id), ('reference', '=', order.name)
                ], limit=1)

            if not tx:
                if order.amount_total:
                    values.update({'tx_ids': False, 'state': 'error'})
                else:
                    values.update({'tx_ids': False, 'state': 'done', 'validation': None})
            else:
                state = tx.state
                flag = True if state == 'pending' and tx.acquirer_id.validation == 'automatic' else False
                values.update({
                    'tx_ids': True,
                    'state': state,
                    'validation': tx.acquirer_id.validation,
                    'tx_post_msg': tx.acquirer_id.post_msg or None
                })

        return {'recall': flag, 'message': request.website._render("website_sale.order_state_message", values)}

    @http.route('/shop/payment/validate', type='http', auth="public", website=True)
    def payment_validate(self, transaction_id=None, sale_order_id=None, **post):
        """ Method that should be called by the server when receiving an update
        for a transaction. State at this point :

         - UDPATE ME
        """
        email_act = None
        SaleOrder = request.env['sale.order']

        if transaction_id is None:
            tx = request.website.sale_get_transaction()
        else:
            tx = request.env['payment.transaction'].browse(transaction_id)

        if sale_order_id is None:
            order = request.website.sale_get_order()
        else:
            order = request.env['sale.order'].sudo().browse(sale_order_id)
            assert order.id == request.session.get('sale_last_order_id')

        if not order or (order.amount_total and not tx):
            return request.redirect('/shop')

        if (not order.amount_total and not tx) or tx.state in ['pending', 'done']:
            if (not order.amount_total and not tx):
                # Orders are confirmed by payment transactions, but there is none for free orders,
                # (e.g. free events), so confirm immediately
                order.action_button_confirm()
            # send by email
            email_act = order.action_quotation_send()
        elif tx and tx.state == 'cancel':
            # cancel the quotation
            order.action_cancel()

        # send the email
        if email_act and email_act.get('context'):
            composer_values = {}
            email_ctx = email_act['context']
            template_values = [
                email_ctx.get('default_template_id'),
                email_ctx.get('default_composition_mode'),
                email_ctx.get('default_model'),
                email_ctx.get('default_res_id'),
            ]
            composer_values.update({})
            if not composer_values.get('email_from') and request.env.user.id == request.website.user_id.id:
                composer_values['email_from'] = request.website.user_id.company_id.email
            for key in ['attachment_ids', 'partner_ids']:
                if composer_values.get(key):
                    composer_values[key] = [(6, 0, composer_values[key])]
            composer = request.env['mail.compose.message'].sudo().create(composer_values)
            composer.send_mail()

        # clean context and session, then redirect to the confirmation page
        request.website.sale_reset()

        return request.redirect('/shop/confirmation')

    @http.route(['/shop/confirmation'], type='http', auth="public", website=True)
    def payment_confirmation(self, **post):
        """ End of checkout process controller. Confirmation is basically seing
        the status of a sale.order. State at this point :

         - should not have any context / session info: clean them
         - take a sale.order id, because we request a sale.order and are not
           session dependant anymore
        """

        sale_order_id = request.session.get('sale_last_order_id')
        if sale_order_id:
            order = request.env['sale.order'].sudo().browse(sale_order_id)
        else:
            return request.redirect('/shop')

        return request.website.render("website_sale.confirmation", {'order': order})

    @http.route(['/shop/print'], type='http', auth="public", website=True)
    def print_saleorder(self):
        sale_order_id = request.session.get('sale_last_order_id')
        if sale_order_id:
            order = request.env['sale.order'].sudo().browse(sale_order_id)
            pdf = request.env['report'].sudo().get_pdf(order, 'sale.report_saleorder', data=None)
            pdfhttpheaders = [('Content-Type', 'application/pdf'), ('Content-Length', len(pdf))]
            return request.make_response(pdf, headers=pdfhttpheaders)
        else:
            return request.redirect('/shop')

    #------------------------------------------------------
    # Edit
    #------------------------------------------------------

    @http.route(['/shop/add_product'], type='http', auth="user", methods=['POST'], website=True)
    def add_product(self, name=None, category=0, **post):
        if not name:
            name = _("New Product")
        product = request.env['product.product'].create({'name': name, 'public_categ_ids': category})

        return request.redirect("/shop/product/%s?enable_editor=1" % slug(product.product_tmpl_id))

    @http.route(['/shop/change_styles'], type='json', auth="public")
    def change_styles(self, id, style_id):
        product = request.env['product.template'].browse(id)

        remove = []
        active = False
        for style in product.website_style_ids:
            if style.id == style_id:
                remove.append(style.id)
                active = True
                break

        style = request.env['product.style'].browse(style_id)

        if remove:
            product.write({'website_style_ids': [(3, rid) for rid in remove]})
        if not active:
            product.write({'website_style_ids': [(4, style.id)]})

        return not active

    @http.route(['/shop/change_sequence'], type='json', auth="public")
    def change_sequence(self, id, sequence):
        template = request.env['product.template'].browse(id)
        if sequence == "top":
            template.set_sequence_top()
        elif sequence == "bottom":
            template.set_sequence_bottom()
        elif sequence == "up":
            template.set_sequence_up()
        elif sequence == "down":
            template.set_sequence_down()

    @http.route(['/shop/change_size'], type='json', auth="public")
    def change_size(self, id, x, y):
        product = request.env['product.template'].browse(id)
        return product.write({'website_size_x': x, 'website_size_y': y})

    def order_lines_2_google_api(self, order_lines):
        """ Transforms a list of order lines into a dict for google analytics """
        return [{
                'id': line.order_id and line.order_id.id,
                'name': line.product_id.categ_id and line.product_id.categ_id.name or '-',
                'sku': line.product_id.id,
                'quantity': line.product_uom_qty,
                'price': line.price_unit,
            } for line in order_lines]

    @http.route(['/shop/tracking_last_order'], type='json', auth="public")
    def tracking_cart(self, **post):
        """ return data about order in JSON needed for google analytics"""
        ret = {}
        sale_order_id = request.session.get('sale_last_order_id')
        if sale_order_id:
            order = request.env['sale.order'].sudo().browse(sale_order_id)
            ret['transaction'] = {
                'id': sale_order_id,
                'affiliation': order.company_id.name,
                'revenue': order.amount_total,
                'currency': order.currency_id.name
            }
            ret['lines'] = self.order_lines_2_google_api(order.order_line)
        return ret
