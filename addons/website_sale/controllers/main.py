# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import werkzeug

from odoo import http, tools, _
from odoo.http import request
from odoo.addons.website.models.website import slug

PPG = 20  # Products Per Page
PPR = 4   # Products Per Row

class TableCompute(object):

    def __init__(self):
        self.table = {}

    def _check_place(self, posx, posy, sizex, sizey):
        res = True
        for y in range(sizey):
            for x in range(sizex):
                if posx + x >= PPR:
                    res = False
                    break
                row = self.table.setdefault(posy + y, {})
                if row.setdefault(posx + x) is not None:
                    res = False
                    break
            for x in range(PPR):
                self.table[posy + y].setdefault(x, None)
        return res

    def process(self, products, ppg=PPG):
        # Compute products positions on the grid
        minpos = 0
        index = 0
        maxy = 0
        for p in products:
            x = min(max(p.website_size_x, 1), PPR)
            y = min(max(p.website_size_y, 1), PPR)
            if index >= ppg:
                x = y = 1

            pos = minpos
            while not self._check_place(pos % PPR, pos / PPR, x, y):
                pos += 1
            # if 21st products (index 20) and the last line is full (PPR products in it), break
            # (pos + 1.0) / PPR is the line where the product would be inserted
            # maxy is the number of existing lines
            # + 1.0 is because pos begins at 0, thus pos 20 is actually the 21st block
            # and to force python to not round the division operation
            if index >= ppg and ((pos + 1.0) / PPR) > maxy:
                break

            if x == 1 and y == 1:   # simple heuristic for CPU optimization
                minpos = pos / PPR

            for y2 in range(y):
                for x2 in range(x):
                    self.table[(pos / PPR) + y2][(pos % PPR) + x2] = False
            self.table[pos / PPR][pos % PPR] = {
                'product': p, 'x': x, 'y': y,
                'class': " ".join(map(lambda x: x.html_class or '', p.website_style_ids))
            }
            if index <= ppg:
                maxy = max(maxy, y + (pos / PPR))
            index += 1

        # Format table according to HTML needs
        rows = self.table.items()
        rows.sort()
        rows = map(lambda x: x[1], rows)
        for col in range(len(rows)):
            cols = rows[col].items()
            cols.sort()
            x += len(cols)
            rows[col] = [c for c in map(lambda x: x[1], cols) if c]

        return rows

        # TODO keep with input type hidden


class QueryURL(object):
    def __init__(self, path='', **args):
        self.path = path
        self.args = args

    def __call__(self, path=None, **kw):
        if not path:
            path = self.path
        for k, v in self.args.items():
            kw.setdefault(k, v)
        l = []
        for k, v in kw.items():
            if v:
                if isinstance(v, list) or isinstance(v, set):
                    l.append(werkzeug.url_encode([(k, i) for i in v]))
                else:
                    l.append(werkzeug.url_encode([(k, v)]))
        if l:
            path += '?' + '&'.join(l)
        return path


class WebsiteSale(http.Controller):
    def get_attribute_value_ids(self, product):
        """ list of selectable attributes of a product

        :return: list of product variant description
           (variant id, [visible attribute ids], variant price, variant sale price)
        """
        # product attributes with at least two choices
        visible_attrs_ids = product.attribute_line_ids.filtered(lambda l: len(l.value_ids) > 1).mapped('attribute_id').ids
        to_currency = request.website.get_current_pricelist().currency_id
        attribute_value_ids = []
        for variant in product.product_variant_ids:
            if to_currency != product.currency_id:
                price = variant.currency_id.compute(variant.lst_price, to_currency)
            else:
                price = variant.lst_price
            visible_attribute_ids = [v.id for v in variant.attribute_value_ids if v.attribute_id.id in visible_attrs_ids]
            attribute_value_ids.append([variant.id, visible_attribute_ids, variant.price, price])
        return attribute_value_ids

    def _get_search_order(self, post):
        # OrderBy will be parsed in orm and so no direct sql injection
        # id is added to be sure that order is a unique sort key
        return 'website_published desc,%s , id desc' % post.get('order', 'website_sequence desc')

    @http.route(['/shop/change_pricelist/<model("product.pricelist"):pl_id>'], type='http', auth="public", website=True)
    def pricelist_change(self, pl_id, **post):
        if request.website.is_pricelist_available(pl_id.id):
            request.session['website_sale_current_pl'] = pl_id.id
            request.website.sale_get_order(force_pricelist=pl_id.id)
        return request.redirect(request.httprequest.referrer or '/shop')

    def _get_search_domain(self, search, category, attrib_values):
        domain = request.website.sale_product_domain()
        if search:
            for srch in search.split(" "):
                domain += [
                    '|', '|', '|', ('name', 'ilike', srch), ('description', 'ilike', srch),
                    ('description_sale', 'ilike', srch), ('product_variant_ids.default_code', 'ilike', srch)]

        if category:
            domain += [('public_categ_ids', 'child_of', int(category))]

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

        return domain

    @http.route([
        '/shop',
        '/shop/page/<int:page>',
        '/shop/category/<model("product.public.category"):category>',
        '/shop/category/<model("product.public.category"):category>/page/<int:page>'
    ], type='http', auth="public", website=True)
    def shop(self, page=0, category=None, search='', ppg=False, **post):
        if ppg:
            try:
                ppg = int(ppg)
            except ValueError:
                ppg = PPG
            post["ppg"] = ppg
        else:
            ppg = PPG

        attrib_list = request.httprequest.args.getlist('attrib')
        attrib_values = [map(int, v.split("-")) for v in attrib_list if v]
        attributes_ids = set([v[0] for v in attrib_values])
        attrib_set = set([v[1] for v in attrib_values])

        domain = self._get_search_domain(search, category, attrib_values)

        keep = QueryURL('/shop', category=category and int(category), search=search, attrib=attrib_list)

        pricelist_context = dict(request.env.context)
        if not pricelist_context.get('pricelist'):
            pricelist = request.website.get_current_pricelist()
            pricelist_context['pricelist'] = pricelist.id
        else:
            pricelist = request.env['product.pricelist'].browse(pricelist_context['pricelist'])
        url = "/shop"
        if search:
            post["search"] = search
        if category:
            category = request.env['product.public.category'].browse(int(category))
            url = "/shop/category/%s" % slug(category)
        if attrib_list:
            post['attrib'] = attrib_list

        categs = request.env['product.public.category'].search([('parent_id', '=', False)])
        Product = request.env['product.template']

        parent_category_ids = []
        if category:
            parent_category_ids = [category.id]
            current_category = category
            while current_category.parent_id:
                parent_category_ids.append(current_category.parent_id.id)
                current_category = current_category.parent_id

        product_count = Product.search_count(domain)
        pager = request.website.pager(url=url, total=product_count, page=page, step=ppg, scope=7, url_args=post)
        products = Product.with_context(pricelist_context).search(domain, limit=ppg, offset=pager['offset'], order=self._get_search_order(post))

        ProductAttribute = request.env['product.attribute']
        if products:
            attributes = ProductAttribute.search([('attribute_line_ids.product_tmpl_id', 'in', products.ids)])
        else:
            attributes = ProductAttribute.browse(attributes_ids)

        from_currency = request.env.user.company_id.currency_id
        to_currency = pricelist.currency_id
        compute_currency = lambda price: from_currency.compute(price, to_currency)

        values = {
            'search': search,
            'category': category,
            'attrib_values': attrib_values,
            'attrib_set': attrib_set,
            'pager': pager,
            'pricelist': pricelist,
            'products': products,
            'bins': TableCompute().process(products, ppg),
            'rows': PPR,
            'categories': categs,
            'attributes': attributes,
            'compute_currency': compute_currency,
            'keep': keep,
            'parent_category_ids': parent_category_ids,
        }
        if category:
            values['main_object'] = category
        return request.website.render("website_sale.products", values)

    @http.route(['/shop/product/<model("product.template"):product>'], type='http', auth="public", website=True)
    def product(self, product, category='', search='', **kwargs):
        product_context = dict(request.env.context, active_id=product.id)
        ProductCategory = request.env['product.public.category']
        Rating = request.env['rating.rating']

        if category:
            category = ProductCategory.browse(int(category)).exists()

        attrib_list = request.httprequest.args.getlist('attrib')
        attrib_values = [map(int, v.split("-")) for v in attrib_list if v]
        attrib_set = set([v[1] for v in attrib_values])

        keep = QueryURL('/shop', category=category and category.id, search=search, attrib=attrib_list)

        categs = ProductCategory.search([('parent_id', '=', False)])

        pricelist = request.website.get_current_pricelist()

        from_currency = request.env.user.company_id.currency_id
        to_currency = pricelist.currency_id
        compute_currency = lambda price: from_currency.compute(price, to_currency)

        # get the rating attached to a mail.message, and the rating stats of the product
        ratings = Rating.search([('message_id', 'in', product.website_message_ids.ids)])
        rating_message_values = dict([(record.message_id.id, record.rating) for record in ratings])
        rating_product = product.rating_get_stats([('website_published', '=', True)])

        if not product_context.get('pricelist'):
            product_context['pricelist'] = pricelist.id
            product = product.with_context(product_context)

        values = {
            'search': search,
            'category': category,
            'pricelist': pricelist,
            'attrib_values': attrib_values,
            'compute_currency': compute_currency,
            'attrib_set': attrib_set,
            'keep': keep,
            'categories': categs,
            'main_object': product,
            'product': product,
            'get_attribute_value_ids': self.get_attribute_value_ids,
            'rating_message_values': rating_message_values,
            'rating_product': rating_product
        }
        return request.website.render("website_sale.product", values)

    @http.route(['/shop/pricelist'], type='http', auth="public", website=True)
    def pricelist(self, promo, **post):
        pricelist = request.env['product.pricelist'].sudo().search([('code', '=', promo)], limit=1)
        if pricelist and not request.website.is_pricelist_available(pricelist.id):
            return request.redirect("/shop/cart?code_not_available=1")

        request.website.sale_get_order(code=promo)
        return request.redirect("/shop/cart")

    @http.route(['/shop/cart'], type='http', auth="public", website=True)
    def cart(self, **post):
        order = request.website.sale_get_order()
        if order:
            from_currency = order.company_id.currency_id
            to_currency = order.pricelist_id.currency_id
            compute_currency = lambda price: from_currency.compute(price, to_currency)
        else:
            compute_currency = lambda price: price

        values = {
            'website_sale_order': order,
            'compute_currency': compute_currency,
            'suggested_products': [],
        }
        if order:
            _order = order
            if not request.env.context.get('pricelist'):
                _order = order.with_context(pricelist=order.pricelist_id.id)
            values['suggested_products'] = _order._cart_accessories()

        if post.get('type') == 'popover':
            return request.website.render("website_sale.cart_popover", values)

        if post.get('code_not_available'):
            values['code_not_available'] = post.get('code_not_available')

        return request.website.render("website_sale.cart", values)

    @http.route(['/shop/cart/update'], type='http', auth="public", methods=['POST'], website=True)
    def cart_update(self, product_id, add_qty=1, set_qty=0, **kw):
        request.website.sale_get_order(force_create=1)._cart_update(product_id=int(product_id), add_qty=float(add_qty), set_qty=float(set_qty))
        return request.redirect("/shop/cart")

    @http.route(['/shop/cart/update_json'], type='json', auth="public", methods=['POST'], website=True)
    def cart_update_json(self, product_id, line_id=None, add_qty=None, set_qty=None, display=True):
        order = request.website.sale_get_order(force_create=1)
        if order.state != 'draft':
            request.website.sale_reset()
            return {}

        value = order._cart_update(product_id=product_id, line_id=line_id, add_qty=add_qty, set_qty=set_qty)
        if not order.cart_quantity:
            request.website.sale_reset()
            return {}
        if not display:
            return None

        order = request.website.sale_get_order()
        value['cart_quantity'] = order.cart_quantity
        from_currency = order.company_id.currency_id
        to_currency = order.pricelist_id.currency_id
        value['website_sale.cart_lines'] = request.website._render("website_sale.cart_lines", {
                'website_sale_order': order,
                'compute_currency': lambda price: from_currency.compute(price, to_currency),
                'suggested_products': order.with_context(pricelist=order.pricelist_id.id)._cart_accessories()
            })
        return value

    # ------------------------------------------------------
    # Checkout
    # ------------------------------------------------------

    def checkout_redirection(self, order):

        # must have a draft sale order with lines at this point, otherwise reset
        if not order or order.state != 'draft':
            request.session['sale_order_id'] = None
            request.session['sale_transaction_id'] = None
            return request.redirect('/shop')

        # if transaction pending / done: redirect to confirmation
        tx = request.env.context.get('website_sale_transaction')
        if tx and tx.state != 'draft':
            return request.redirect('/shop/payment/confirmation/%s' % order.id)

    def checkout_values(self, data=None):
        countries = request.env['res.country'].sudo().search([])
        states = request.env['res.country.state'].sudo().search([])
        partner = request.env.user.partner_id

        order = None

        shipping_id = data and data.get('shipping_id') or None
        shippings = request.env['res.partner']
        checkout = {}
        if not data:
            if request.env.uid != request.website.user_id.id:
                checkout.update(self.checkout_parse("billing", partner))
                shippings |= request.env['res.partner'].sudo().search([("parent_id", "=", partner.id), ('type', "=", 'delivery')])
            else:
                order = request.website.sale_get_order(force_create=1)
                if order.partner_id:
                    domain = [("partner_id", "=", order.partner_id.id)]
                    user_ids = request.env['res.users'].with_context(active_test=False).sudo().search(domain).ids
                    if not user_ids or request.website.user_id.id not in user_ids:
                        checkout.update( self.checkout_parse("billing", order.partner_id) )
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

        shippings -= partner

        if shipping_id == partner.id:
            shipping_id = 0
        elif shipping_id > 0 and shipping_id not in shippings.ids:
            shippings |= request.env['res.partner'].browse(shipping_id)
        elif shipping_id is None and shippings:
            shipping_id = shippings[0].id

        if shipping_id > 0:
            shipping = request.env['res.partner'].with_context(show_address=1).sudo().browse(shipping_id)
            checkout.update(self.checkout_parse("shipping", shipping))

        checkout['shipping_id'] = shipping_id

        # Default search by user country
        if not checkout.get('country_id'):
            country_code = request.session['geoip'].get('country_code')
            if country_code:
                checkout['country_id'] = request.env['res.country'].search([('code', '=', country_code)], limit=1).id

        values = {
            'countries': countries,
            'states': states,
            'checkout': checkout,
            'shipping_id': partner.id != shipping_id and shipping_id or 0,
            'shippings': shippings.with_context(show_address=1).sudo(),
            'error': {},
            'has_check_vat': hasattr(request.env['res.partner'], 'check_vat'),
            'only_services': order and order.only_services or False
        }

        return values

    mandatory_billing_fields = ["name", "phone", "email", "street2", "city", "country_id"]
    optional_billing_fields = ["street", "state_id", "vat", "zip"]
    mandatory_shipping_fields = ["name", "phone", "street", "city", "country_id"]
    optional_shipping_fields = ["state_id", "zip"]

    def _get_mandatory_billing_fields(self):
        return self.mandatory_billing_fields

    def _get_optional_billing_fields(self):
        return self.optional_billing_fields

    def _get_mandatory_shipping_fields(self):
        return self.mandatory_shipping_fields

    def _get_optional_shipping_fields(self):
        return self.optional_shipping_fields

    def _post_prepare_query(self, query, data, address_type):
        return query

    def checkout_parse(self, address_type, data, remove_prefix=False):
        """ data is a dict OR a partner browse record
        """
        # set mandatory and optional fields
        assert address_type in ('billing', 'shipping')
        if address_type == 'billing':
            all_fields = self._get_mandatory_billing_fields() + self._get_optional_billing_fields()
            prefix = ''
        else:
            all_fields = self._get_mandatory_shipping_fields() + self._get_optional_shipping_fields()
            prefix = 'shipping_'

        # set data
        if isinstance(data, dict):
            query = dict((prefix + field_name, data[prefix + field_name])
                for field_name in all_fields if prefix + field_name in data)
        else:
            query = dict((prefix + field_name, getattr(data, field_name))
                for field_name in all_fields if getattr(data, field_name))
            if address_type == 'billing' and data.parent_id:
                query[prefix + 'street'] = data.parent_id.name

        if query.get(prefix + 'state_id'):
            query[prefix + 'state_id'] = int(query[prefix + 'state_id'])
        if query.get(prefix + 'country_id'):
            query[prefix + 'country_id'] = int(query[prefix + 'country_id'])

        query = self._post_prepare_query(query, data, address_type)

        if not remove_prefix:
            return query

        return dict((field_name, data[prefix + field_name]) for field_name in all_fields if prefix + field_name in data)

    def checkout_form_validate(self, data):
        Partner = request.env['res.partner']

        error = dict()
        error_message = []

        # Validation
        for field_name in self._get_mandatory_billing_fields():
            if not data.get(field_name):
                error[field_name] = 'missing'

        # email validation
        if data.get('email') and not tools.single_email_re.match(data.get('email')):
            error["email"] = 'error'
            error_message.append(_('Invalid Email! Please enter a valid email address.'))

        # vat validation
        if data.get("vat") and hasattr(Partner, "check_vat"):
            if request.website.company_id.vat_check_vies:
                # force full VIES online check
                check_func = Partner.vies_vat_check
            else:
                # quick and partial off-line checksum validation
                check_func = Partner.simple_vat_check
            vat_country, vat_number = Partner._split_vat(data.get("vat"))
            if not check_func(vat_country, vat_number):  # simple_vat_check
                error["vat"] = 'error'

        if data.get("shipping_id") == -1:
            for field_name in self._get_mandatory_shipping_fields():
                field_name = 'shipping_' + field_name
                if not data.get(field_name):
                    error[field_name] = 'missing'

        # error message for empty required fields
        if [err for err in error.values() if err == 'missing']:
            error_message.append(_('Some required fields are empty.'))

        return error, error_message

    def _get_shipping_info(self, checkout):
        shipping_info = {}
        shipping_info.update(self.checkout_parse('shipping', checkout, True))
        shipping_info['type'] = 'delivery'
        return shipping_info

    def checkout_form_save(self, checkout):

        order = request.website.sale_get_order(force_create=1)
        Partner = request.env['res.partner']
        partner_lang = request.lang if request.lang in request.website.mapped('language_ids.code') else None

        billing_info = {'customer': True}
        if partner_lang:
            billing_info['lang'] = partner_lang
        billing_info.update(self.checkout_parse('billing', checkout, True))

        # set partner_id
        partner = None
        if request.uid != request.website.user_id.id:
            partner = request.env.user.sudo().partner_id
        elif order.partner_id:
            user_ids = request.env['res.users'].with_context(active_test=False).sudo().search([("partner_id", "=", order.partner_id.id)]).ids
            if not user_ids or request.website.user_id.id not in user_ids:
                partner = order.partner_id

        # save partner informations
        if partner and request.website.partner_id.id != partner.id:
            partner.write(billing_info)
        else:
            # create partner
            billing_info['team_id'] = request.website.salesteam_id.id
            partner = Partner.sudo().create(billing_info)
        order.write({'partner_id': partner.id})
        order.onchange_partner_id()

        # create a new shipping partner
        if checkout.get('shipping_id') == -1:
            shipping_info = self._get_shipping_info(checkout)
            if partner_lang:
                shipping_info['lang'] = partner_lang
            shipping_info['parent_id'] = partner.id
            checkout['shipping_id'] = Partner.sudo().create(shipping_info).id

        order_info = {
            'message_partner_ids': [(4, partner.id), (3, request.website.partner_id.id)],
            'partner_shipping_id': checkout.get('shipping_id') or partner.id,
        }
        order.write(order_info)

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

        order.onchange_partner_shipping_id()
        order.order_line._compute_tax_id()

        request.session['sale_last_order_id'] = order.id

        request.website.sale_get_order(update_pricelist=True)

        extra_step = request.env.ref('website_sale.extra_info_option')
        if extra_step.active:
            return request.redirect("/shop/extra_info")

        return request.redirect("/shop/payment")

    # ------------------------------------------------------
    # Extra step
    # ------------------------------------------------------
    @http.route(['/shop/extra_info'], type='http', auth="public", website=True)
    def extra_info(self, **post):

        # Check that this option is activated
        extra_step = request.env.ref('website_sale.extra_info_option')
        if not extra_step.active:
            return request.redirect("/shop/payment")

        # check that cart is valid
        order = request.website.sale_get_order()
        redirection = self.checkout_redirection(order)
        if redirection:
            return redirection

        # if form posted
        if 'post_values' in post:
            values = {}
            for field_name, field_value in post.items():
                if field_name in request.env['sale.order']._fields and field_name.startswith('x_'):
                    values[field_name] = field_value
            if values:
                order.write(values)
            return request.redirect("/shop/payment")

        values = {
            'website_sale_order': order
        }

        values.update(request.env['sale.order']._get_website_data(order))

        return request.website.render("website_sale.extra_info", values)

    # ------------------------------------------------------
    # Payment
    # ------------------------------------------------------

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
        values['errors'] = SaleOrder._get_errors(order)
        values.update(SaleOrder._get_website_data(order))
        if not values['errors']:
            acquirers = request.env['payment.acquirer'].search(
                [('website_published', '=', True), ('company_id', '=', order.company_id.id)]
            )
            values['acquirers'] = list(acquirers)
            acquirer_buttons = acquirers.with_context(submit_class='btn btn-primary', submit_txt=_('Pay Now')).sudo().render(
                '/',
                order.amount_total,
                order.pricelist_id.currency_id.id,
                values={
                    'return_url': '/shop/payment/validate',
                    'partner_id': shipping_partner_id,
                    'billing_partner_id': order.partner_invoice_id.id,
                }
            )
            for index, button in enumerate(acquirer_buttons):
                values['acquirers'][index].button = button

        return request.website.render("website_sale.payment", values)

    @http.route(['/shop/payment/transaction/<int:acquirer_id>'], type='json', auth="public", website=True)
    def payment_transaction(self, acquirer_id, **kwargs):
        """ Json method that creates a payment.transaction, used to create a
        transaction when the user clicks on 'pay now' button. After having
        created the transaction, the event continues and the user is redirected
        to the acquirer website.

        :param int acquirer_id: id of a payment.acquirer record. If not set the
                                user is redirected to the checkout page
        """
        Transaction = request.env['payment.transaction'].sudo()
        order = request.website.sale_get_order()

        # In case the route is called directly from the JS (as done in Stripe payment method)
        so_id = kwargs.get('so_id')
        so_token = kwargs.get('so_token')
        if so_id and so_token:
            order = request.env['sale.order'].sudo().search([('id', '=', so_id), ('access_token', '=', so_token)])
        elif so_id:
            order = request.env['sale.order'].search([('id', '=', so_id)])
        else:
            order = request.website.sale_get_order()

        if not order or not order.order_line or acquirer_id is None:
            return request.redirect("/shop/checkout")

        assert order.partner_id.id != request.website.partner_id.id

        # find an already existing transaction
        tx = request.website.sale_get_transaction()
        if tx:
            if tx.sale_order_id.id != order.id or tx.state in ['error', 'cancel'] or tx.acquirer_id.id != acquirer_id:
                tx = False
            elif tx.state == 'draft':  # button cliked but no more info -> rewrite on tx or create a new one ?
                tx.write(dict(Transaction.on_change_partner_id(order.partner_id.id).get('value', {}), amount=order.amount_total))
        if not tx:
            tx = Transaction.create({
                'acquirer_id': acquirer_id,
                'type': 'form',
                'amount': order.amount_total,
                'currency_id': order.pricelist_id.currency_id.id,
                'partner_id': order.partner_id.id,
                'partner_country_id': order.partner_id.country_id.id,
                'reference': Transaction.get_next_reference(order.name),
                'sale_order_id': order.id,
            })
            request.session['sale_transaction_id'] = tx.id

        # update quotation
        order.write({
            'payment_acquirer_id': acquirer_id,
            'payment_tx_id': request.session['sale_transaction_id']
        })

        # confirm the quotation
        if tx.acquirer_id.auto_confirm == 'at_pay_now':
            order.with_context(send_email=True).action_confirm()

        return tx.acquirer_id.with_context(submit_class='btn btn-primary', submit_txt=_('Pay Now')).sudo().render(
            tx.reference,
            order.amount_total,
            order.pricelist_id.currency_id.id,
            values={
                'return_url': '/shop/payment/validate',
                'partner_id': order.partner_shipping_id.id or order.partner_invoice_id.id,
                'billing_partner_id': order.partner_invoice_id.id,
            },
        )[0]

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
                ['|', ('sale_order_id', '=', order.id), ('reference', '=', order.name)], limit=1
            )

            if not tx:
                if order.amount_total:
                    values.update({'tx_ids': False, 'state': 'error'})
                else:
                    values.update({'tx_ids': False, 'state': 'done', 'validation': None})
            else:
                state = tx.state
                flag = state == 'pending'
                values.update({
                    'tx_ids': True,
                    'state': state,
                    'acquirer_id': tx.acquirer_id,
                    'validation': tx.acquirer_id.auto_confirm == 'none',
                    'tx_post_msg': tx.acquirer_id.post_msg or None
                })

        return {'recall': flag, 'message': request.website._render("website_sale.order_state_message", values)}

    @http.route('/shop/payment/validate', type='http', auth="public", website=True)
    def payment_validate(self, transaction_id=None, sale_order_id=None, **post):
        """ Method that should be called by the server when receiving an update
        for a transaction. State at this point :

         - UDPATE ME
        """
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
                order.with_context(send_email=True).action_confirm()
        elif tx and tx.state == 'cancel':
            # cancel the quotation
            order.action_cancel()

        # clean context and session, then redirect to the confirmation page
        request.website.sale_reset()
        if tx and tx.state == 'draft':
            return request.redirect('/shop')

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
            return request.website.render("website_sale.confirmation", {'order': order})
        else:
            return request.redirect('/shop')

    @http.route(['/shop/print'], type='http', auth="public", website=True)
    def print_saleorder(self):
        sale_order_id = request.session.get('sale_last_order_id')
        if sale_order_id:
            order = request.env['sale.order'].browse(sale_order_id)
            pdf = request.env['report'].sudo().get_pdf(order, 'sale.report_saleorder', data=None)
            pdfhttpheaders = [('Content-Type', 'application/pdf'), ('Content-Length', len(pdf))]
            return request.make_response(pdf, headers=pdfhttpheaders)
        else:
            return request.redirect('/shop')

    # ------------------------------------------------------
    # Edit
    # ------------------------------------------------------

    @http.route(['/shop/add_product'], type='http', auth="user", methods=['POST'], website=True)
    def add_product(self, name=None, category=0, **post):
        product = request.env['product.product'].create({
            'name': name or _("New Product"),
            'public_categ_ids': category
        })

        return request.redirect("/shop/product/%s?enable_editor=1" % slug(product.product_tmpl_id))

    @http.route(['/shop/change_styles'], type='json', auth="public")
    def change_styles(self, id, style_id):
        product = request.env['product.template'].browse(id)

        remove = []
        active = False
        style_id = int(style_id)
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
        product_tmpl = request.env['product.template'].browse(id)
        if sequence == "top":
            product_tmpl.set_sequence_top()
        elif sequence == "bottom":
            product_tmpl.set_sequence_bottom()
        elif sequence == "up":
            product_tmpl.set_sequence_up()
        elif sequence == "down":
            product_tmpl.set_sequence_down()

    @http.route(['/shop/change_size'], type='json', auth="public")
    def change_size(self, id, x, y):
        product = request.env['product.template'].browse(id)
        return product.write({'website_size_x': x, 'website_size_y': y})

    def order_lines_2_google_api(self, order_lines):
        """ Transforms a list of order lines into a dict for google analytics """
        ret = []
        for line in order_lines:
            product = line.product_id
            ret.append({
                'id': line.order_id.id,
                'sku': product.barcode or product.id,
                'name': product.name or '-',
                'category': product.categ_id.name or '-',
                'price': line.price_unit,
                'quantity': line.product_uom_qty,
            })
        return ret

    def order_2_return_dict(self, order):
        """ Returns the tracking_cart dict of the order for Google analytics basically defined to be inherited """
        return {
            'transaction': {
                'id': order.id,
                'affiliation': order.company_id.name,
                'revenue': order.amount_total,
                'tax': order.amount_tax,
                'currency': order.currency_id.name
            },
            'lines': self.order_lines_2_google_api(order.order_line)
        }

    @http.route(['/shop/tracking_last_order'], type='json', auth="public")
    def tracking_cart(self, **post):
        """ return data about order in JSON needed for google analytics"""
        ret = {}
        sale_order_id = request.session.get('sale_last_order_id')
        if sale_order_id:
            order = request.env['sale.order'].sudo().browse(sale_order_id)
            ret = self.order_2_return_dict(order)
        return ret

    @http.route(['/shop/get_unit_price'], type='json', auth="public", methods=['POST'], website=True)
    def get_unit_price(self, product_ids, add_qty, use_order_pricelist=False, **kw):
        products = request.env['product.product'].browse(product_ids)
        partner = request.env.user.partner_id
        pricelist = request.website.get_current_pricelist()
        prices = pricelist.price_rule_get_multi([(product, add_qty, partner) for product in products])
        return {product_id: prices[product_id][pricelist.id][0] for product_id in product_ids}
