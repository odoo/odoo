# -*- coding: utf-8 -*-
import random
import simplejson
import werkzeug

from openerp import SUPERUSER_ID
from openerp.addons.web import http
from openerp.addons.web.http import request

PPG = 20 # Products Per Page
PPR = 4  # Products Per Row

class table_compute(object):
    def __init__(self):
        self.table = {}

    def _check_place(self, posx, posy, sizex, sizey):
        for y in range(sizey):
            for x in range(sizex):
                if posx+x>=PPR:
                    return False
                row = self.table.setdefault(posy+y, {})
                if row.setdefault(posx+x) is not None:
                    return False
        return True

    def process(self, products):
        # Compute products positions on the grid
        minpos = 0
        index = 0
        maxy = 0
        for p in products:
            x = p.website_size_x
            y = p.website_size_y
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
                'class': " ".join(map(lambda x: x.html_class, p.website_style_ids))
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
            rows[col] = map(lambda x: x[1], cols)
        return filter(bool, rows)

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


class website_sale(http.Controller):

    def get_pricelist(self):
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
        sale_order = context.get('sale_order')
        if sale_order:
            pricelist = sale_order.pricelist_id
        else:
            partner = pool['res.users'].browse(cr, SUPERUSER_ID, uid, context=context).partner_id
            pricelist = partner.property_product_pricelist
        return pricelist

    @http.route([
        '/shop/',
        '/shop/page/<int:page>/',
        '/shop/category/<model("product.public.category"):category>/',
        '/shop/category/<model("product.public.category"):category>/page/<int:page>/'
    ], type='http', auth="public", website=True, multilang=True)
    def shop(self, page=0, category=None, search='', **post):
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry

        domain = request.website.sale_product_domain()
        if search:
            domain += ['|', ('name', 'ilike', search), ('description', 'ilike', search)]
        if category:
            domain += [('product_variant_ids.public_categ_id', 'child_of', category.id)]

        attrib_values = map(int,request.httprequest.args.getlist('attrib'))
        if attrib_values:
            domain += [('attribute_lines.value_id', 'in', attrib_values)]
        attrib_set = set(attrib_values) 
        keep = QueryURL('/shop', category=category and category.id, search=search, attrib=attrib_set)

        product_obj = pool.get('product.template')
        product_count = product_obj.search_count(cr, uid, domain, context=context)
        pager = request.website.pager(url="/shop/", total=product_count, page=page, step=PPG, scope=7, url_args=post)
        product_ids = product_obj.search(cr, uid, domain, limit=PPG+10, offset=pager['offset'], order='website_published desc, website_sequence desc', context=context)
        products = product_obj.browse(cr, uid, product_ids, context=context)

        style_obj = pool['product.style']
        style_ids = style_obj.search(cr, uid, [], context=context)
        styles = style_obj.browse(cr, uid, style_ids, context=context)

        category_obj = pool['product.public.category']
        category_ids = category_obj.search(cr, uid, [], context=context)
        categories = category_obj.browse(cr, uid, category_ids, context=context)
        categs = filter(lambda x: not x.parent_id, categories)

        attributes_obj = request.registry['product.attribute']
        attributes_ids = attributes_obj.search(cr, uid, [], context=request.context)
        attributes = attributes_obj.browse(cr, uid, attributes_ids, context=request.context)

        values = {
            'search': search,
            'category': category and category.id,
            'attrib_set': attrib_set,
            'pager': pager,
            'pricelist': self.get_pricelist(),
            'products': products,
            'bins': table_compute().process(products),
            'rows': PPR,
            'styles': styles,
            'categories': categs,
            'attributes': attributes,
            'keep': keep,
            'style_in_product': lambda style, product: style.id in [s.id for s in product.website_style_ids],
            'attrib_encode': lambda attribs: werkzeug.url_encode([('attrib',i) for i in attribs]),
        }

        return request.website.render("website_sale.products", values)

    @http.route(['/shop/product/<model("product.template"):product>/'], type='http', auth="public", website=True, multilang=True)
    def product(self, product, category='', search='', **kwargs):
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry

        if category:
            category = category_obj.browse(request.cr, request.uid, int(category), context=request.context)

        attrib_values = map(int,request.httprequest.args.getlist('attrib'))
        attrib_set = set(attrib_values) 

        keep = QueryURL('/shop', category=category and category.id, search=search, attrib=attrib_set)

        category_obj = pool['product.public.category']
        category_ids = category_obj.search(cr, uid, [], context=context)
        category_list = category_obj.name_get(cr, uid, category_ids, context=context)
        category_list = sorted(category_list, key=lambda category: category[1])

        values = {
            'search': search,
            'category': category,
            'pricelist': self.get_pricelist(),
            'attrib_set': attrib_set,
            'keep': keep,
            'category_list': category_list,
            'main_object': product,
            'product': product,
        }
        return request.website.render("website_sale.product", values)

    @http.route(['/shop/product/comment/<int:product_template_id>'], type='http', auth="public", methods=['POST'], website=True)
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

    @http.route(['/shop/cart'], type='http', auth="public", website=True, multilang=True)
    def cart(self, **post):
        order = request.website.sale_get_order()
        values = {
            'order': order,
            'suggested_products': [],
        }
        if order:
            values['suggested_products'] = order._cart_accessories()
        return request.website.render("website_sale.cart", values)

    @http.route(['/shop/cart/update'], type='http', auth="public", methods=['POST'], website=True, multilang=True)
    def cart_update(self, product_id, add_qty=None, set_qty=None, **kw):
        cr, uid, context = request.cr, request.uid, request.context
        request.website.sale_get_order(force_create=1)._cart_update(product_id=product_id, add_qty=add_qty, set_qty=set_qty)
        return request.redirect("/shop/cart")

    @http.route(['/shop/cart/update_json'], type='json', auth="public", website=True, multilang=True)
    def cart_update_json(self, product_id, add_qty=None, set_qty=None):
        order = request.website.sale_get_order(force_create=1)
        quantity = order._cart_update(product_id=product_id, add_qty=add_qty, set_qty=set_qty)
        return request.website._render("website_sale.total", {'website_sale_order': order}) # FIXME good template

    #------------------------------------------------------
    # Checkout
    #------------------------------------------------------
    def checkout_redirection(self, order):
        cr, uid, context, registry = request.cr, request.uid, request.context, request.registry

        # must have a draft sale order with lines at this point, otherwise reset
        if order.state != 'draft':
            request.website_sale_reset(cr, uid, context=context)
            return request.redirect('/shop')

        # if transaction pending / done: redirect to confirmation
        tx = context.get('website_sale_transaction')
        if tx and tx.state != 'draft':
            return request.redirect('/shop/payment/confirmation/%s' % order.id)

    def checkout_values(self):
        cr, uid, context, registry = request.cr, request.uid, request.context, request.registry
        orm_partner = registry.get('res.partner')
        orm_user = registry.get('res.users')
        orm_country = registry.get('res.country')
        state_orm = registry.get('res.country.state')

        country_ids = orm_country.search(cr, SUPERUSER_ID, [], context=context)
        countries = orm_country.browse(cr, SUPERUSER_ID, country_ids, context)
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
        return values

    def checkout_form_parse(self):
        cr, uid, context, registry = request.cr, request.uid, request.context, request.registry

        #public_id = request.registry['website'].get_public_user(cr, uid, context)
        #if not request.uid == public_id:
        #    partner = orm_user.browse(cr, uid, uid, context).partner_id

        #elif order.partner_id:
        #    domain = [("active", "=", False), ("partner_id", "=", order.partner_id.id)]

        #    user_ids = request.registry['res.users'].search(cr, SUPERUSER_ID, domain, context=context)
        #    if not user_ids or public_id not in user_ids:
        #        partner = orm_partner.browse(cr, SUPERUSER_ID, order.partner_id.id, context)

        #if partner:
        #    partner_info = info.from_partner(partner)
        #    checkout.update(partner_info)
        #    shipping_ids = orm_partner.search(cr, SUPERUSER_ID, [("parent_id", "=", partner.id), ('type', "=", 'delivery')], limit=1, context=context)
        #    if shipping_ids:
        #        values['shipping'] = "true"
        #        shipping_partner = orm_partner.browse(cr, SUPERUSER_ID, shipping_ids[0], context)
        #        checkout.update(info.from_partner(shipping_partner, address_type='shipping'))

        # from query
        query = dict((field_name, post[field_name]) for field_name in self.all_fields() if post[field_name])

        # fill with partner
        assert address_type in ('billing', 'shipping')
        if address_type == 'billing':
            prefix = ''
        else:
            prefix = 'shipping_'
        result = dict((prefix + field_name, getattr(partner, field_name)) for field_name in self.string_billing_fields if getattr(partner, field_name))
        result[prefix + 'state_id'] = partner.state_id and partner.state_id.id or ''
        result[prefix + 'country_id'] = partner.country_id and partner.country_id.id or ''
        result[prefix + 'company'] = partner.parent_id and partner.parent_id.name or ''
        return result

        mandatory_billing_fields = ["name", "phone", "email", "street", "city", "country_id", "zip"]
        optional_billing_fields = ["company", "state_id"]
        #string_billing_fields = ["name", "phone", "email", "street", "city", "zip"]

        mandatory_shipping_fields = ["name", "phone", "street", "city", "country_id", "zip"]
        optional_shipping_field = ["state_id"]
        #string_shipping_fields = ["name", "phone", "street", "city", "zip"]

        return values

    def checkout_form_validate(self):
        cr, uid, context, registry = request.cr, request.uid, request.context, request.registry

        # Validation
        for field_name in info.mandatory_billing_fields:
            if not checkout[field_name]:
                error[field_name] = 'missing'
        if post.get("shipping_different"):
            for field_name in info.mandatory_shipping_fields:
                if not checkout[field_name]:
                    error[field_name] = 'missing'

        return values

    def checkout_form_save(self):

        # save partner for order
        company_name = checkout['company']
        company_id = None
        if post['company']:
            company_ids = orm_partner.search(cr, SUPERUSER_ID, [("name", "ilike", company_name), ('is_company', '=', True)], context=context)
            company_id = (company_ids and company_ids[0]) or orm_partner.create(cr, SUPERUSER_ID, {'name': company_name, 'is_company': True}, context)

        billing_info = dict((k, v) for k,v in checkout.items() if "shipping_" not in k and k != "company")
        billing_info['parent_id'] = company_id

        partner_id = None
        public_id = request.registry['website'].get_public_user(cr, uid, context)
        if request.uid != public_id:
            partner_id = orm_user.browse(cr, SUPERUSER_ID, uid, context=context).partner_id.id
        elif order.partner_id:
            domain = [("active", "=", False), ("partner_id", "=", order.partner_id.id)]
            user_ids = request.registry['res.users'].search(cr, SUPERUSER_ID, domain, context=context)
            if not user_ids or public_id not in user_ids:
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
                'street': post['shipping_street'],
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

    @http.route(['/shop/checkout'], type='http', auth="public", website=True, multilang=True)
    def checkout(self, **post):
        cr, uid, context, registry = request.cr, request.uid, request.context, request.registry

        order = request.website.sale_get_order(cr, uid, force_create=1, context=context)

        redirection = checkout_redirection(order)
        if redirection:
            return redirection

        values = self.checkout_values()
        checkout = values['checkout']

        partner = None
        return request.website.render("website_sale.checkout", values)

    @http.route(['/shop/confirm_order'], type='http', auth="public", website=True, multilang=True)
    def confirm_order(self, **post):
        cr, uid, context, registry = request.cr, request.uid, request.context, request.registry
        order_line_obj = request.registry.get('sale.order')

        order = request.website.sale_get_order(cr, uid, context=context)

        redirection = checkout_redirection(order)
        if redirection:
            return redirection

        values = self.checkout_values()
        checkout = values['checkout']
        checkout.update(post)
        error = values['error']

        if error:
            return request.website.render("website_sale.checkout", values)

        checkout_form_save()

        return request.redirect("/shop/payment")

    #------------------------------------------------------
    # Payment
    #------------------------------------------------------

    @http.route(['/shop/payment'], type='http', auth="public", website=True, multilang=True)
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

        redirection = checkout_redirection(order)
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
        values.update(request.registry.get('sale.order')._get_website_data(cr, uid, order, context))

        # fetch all registered payment means
        if tx:
            acquirer_ids = [tx.acquirer_id.id]
        else:
            acquirer_ids = payment_obj.search(cr, SUPERUSER_ID, [('website_published', '=', True)], context=context)
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

    @http.route(['/shop/payment/transaction/<int:acquirer_id>'], type='http', methods=['POST'], auth="public", website=True)
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
        order = request.website.sale_get_order(cr, uid, context=context)

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
        return request.redirect(acquirer_total_url)

    @http.route('/shop/payment/get_status/<int:sale_order_id>', type='json', auth="public", website=True, multilang=True)
    def payment_get_status(self, sale_order_id, **post):
        cr, uid, context = request.cr, request.uid, request.context

        order = request.registry['sale.order'].browse(cr, SUPERUSER_ID, sale_order_id, context=context)
        assert order.website_session_id == request.httprequest.session['website_session_id']

        if not order:
            return {
                'state': 'error',
                'message': '<p>There seems to be an error with your request.</p>',
            }

        tx_ids = request.registry['payment.transaction'].search(
            cr, uid, [
                '|', ('sale_order_id', '=', order.id), ('reference', '=', order.name)
            ], context=context)

        if not tx_ids:
            if order.amount_total:
                return {
                    'state': 'error',
                    'message': '<p>There seems to be an error with your request.</p>',
                }
            else:
                state = 'done'
                message = ""
                validation = None
        else:
            tx = request.registry['payment.transaction'].browse(cr, uid, tx_ids[0], context=context)
            state = tx.state
            if state == 'done':
                message = '<p>Your payment has been received.</p>'
            elif state == 'cancel':
                message = '<p>The payment seems to have been canceled.</p>'
            elif state == 'pending' and tx.acquirer_id.validation == 'manual':
                message = '<p>Your transaction is waiting confirmation.</p>'
                message += tx.acquirer_id.post_msg
            else:
                message = '<p>Your transaction is waiting confirmation.</p>'
            validation = tx.acquirer_id.validation

        return {
            'state': state,
            'message': message,
            'validation': validation
        }

    @http.route('/shop/payment/validate', type='http', auth="public", website=True, multilang=True)
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
            order = request.website.sale_get_order(cr, uid, context=context)
        else:
            order = request.registry['sale.order'].browse(cr, SUPERUSER_ID, sale_order_id, context=context)
            assert order.website_session_id == request.httprequest.session['website_session_id']

        if not tx or not order:
            return request.redirect('/shop/')

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

    #------------------------------------------------------
    # Edit
    #------------------------------------------------------

    @http.route(['/shop/add_product'], type='http', auth="user", methods=['POST'], website=True, multilang=True)
    def add_product(self, name="New Product", category=0, **post):
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
        product_obj = pool['product.product']
        product_id = product_obj.create(cr, uid, { 'name': name, 'public_categ_id': category }, context=context)
        product = product_obj.browse(cr, uid, product_id, context=request.context)

        return request.redirect("/shop/product/%s/?enable_editor=1" % product.product_tmpl_id.id)

    @http.route(['/shop/reorder'], type='json', auth="public")
    def reorder(self, product_id, operation):
        request.registry['product.template'].website_reorder(request.cr, request.uid, [id], operation, context=request.context)

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

    @http.route(['/shop/change_size'], type='json', auth="public")
    def change_size(self, id, x, y):
        product_obj = request.registry.get('product.template')
        product = product_obj.browse(request.cr, request.uid, id, context=request.context)
        return product.write({'website_size_x': x, 'website_size_y': y})


# vim:expandtab:tabstop=4:softtabstop=4:shiftwidth=4:
