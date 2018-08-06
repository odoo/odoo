# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import werkzeug

from odoo import http, _
from odoo.exceptions import AccessError
from odoo.http import request
from odoo.addons.sale.controllers.portal import CustomerPortal
from odoo.addons.portal.controllers.mail import _message_post_helper


class CustomerPortal(CustomerPortal):

    def _portal_quote_user_can_accept(self, order):
        result = super(CustomerPortal, self)._portal_quote_user_can_accept(order)
        # either use quote template settings or fallback on default behavior
        return order.require_signature if order.template_id else result

    def _compute_values(self, order_sudo, pdf, access_token, message, now):
        values = super(CustomerPortal, self)._compute_values(order_sudo, pdf, access_token, message, now)
        values.update(option=any(not x.line_id for x in order_sudo.options))
        return values

    @http.route("/quote/<int:order_id>", type='http', auth="user", website=True)
    def view_user(self, *args, **kwargs):
        return self.view(*args, **kwargs)

    @http.route("/quote/<int:order_id>/<token>", type='http', auth="public", website=True)
    def view(self, order_id, pdf=None, token=None, message=False, **post):
        # /quote/ is an older route that we want to keep to not break previous links.
        return request.redirect('/my/orders/%s?%s%s%s' % (
            order_id,
            '?access_token=' + token if token else '',
            '&message=' + message if message else '',
            '&pdf=' + pdf if pdf else '',
        ))

    @http.route(['/quotation/<int:order_id>/decline'], type='http', auth="public", methods=['POST'], website=True)
    def decline(self, order_id, token=None, **post):
        try:
            self._document_check_access('sale.order', order_id, access_token=token)
        except AccessError:
            return request.redirect('/my')

        Order = request.env['sale.order'].sudo().browse(order_id)
        if Order.state != 'sent':
            return werkzeug.utils.redirect("/my/orders/%s?access_token=%s&message=4" % (order_id, token))
        Order.action_cancel()
        message = post.get('decline_message')
        if message:
            _message_post_helper(message=message, res_id=order_id, res_model='sale.order', **{'token': token} if token else {})
        return werkzeug.utils.redirect("/my/orders/%s%s" % (order_id, '?access_token=%s' % token if token else ''))

    @http.route(['/quotation/<int:order_id>/update_line'], type='json', auth="public", website=True)
    def update(self, line_id, remove=False, unlink=False, order_id=None, token=None, **post):
        try:
            self._document_check_access('sale.order', order_id, access_token=token)
        except AccessError:
            return request.redirect('/my')

        Order = request.env['sale.order'].sudo().browse(int(order_id))
        if Order.state not in ('draft', 'sent'):
            return False
        OrderLine = request.env['sale.order.line'].sudo().browse(int(line_id))
        if unlink:
            OrderLine.unlink()
            return False
        number = -1 if remove else 1
        quantity = OrderLine.product_uom_qty + number
        OrderLine.write({'product_uom_qty': quantity})
        return [str(quantity), str(Order.amount_total)]

    @http.route(["/quotation/template/<model('sale.quote.template'):quote>"], type='http', auth="user", website=True)
    def template_view(self, quote, **post):
        values = {'template': quote}
        return request.render('sale.so_template', values)

    @http.route(["/quotation/<int:order_id>/add_line/<int:option_id>"], type='http', auth="public", website=True)
    def add(self, order_id, option_id, token=None, **post):
        try:
            self._document_check_access('sale.order', order_id, access_token=token)
        except AccessError:
            return request.redirect('/my')

        Order = request.env['sale.order'].sudo().browse(order_id)
        if Order.state not in ['draft', 'sent']:
            return request.render('website.http_error', {'status_code': 'Forbidden', 'status_message': _('You cannot add options to a confirmed order.')})
        Option = request.env['sale.order.option'].sudo().browse(option_id)
        vals = {
            'price_unit': Option.price_unit,
            # TODO SEB website_description into sale_design
            'website_description': Option.website_description,
            'name': Option.name,
            'order_id': Order.id,
            'product_id': Option.product_id.id,
            'product_uom_qty': Option.quantity,
            'product_uom': Option.uom_id.id,
            'discount': Option.discount,
        }

        OrderLine = request.env['sale.order.line'].sudo().create(vals)
        OrderLine._compute_tax_id()
        Option.write({'line_id': OrderLine.id})
        return werkzeug.utils.redirect("/my/orders/%s?%s#pricing" % (Order.id, 'access_token=%' % token if token else ''))

    # note dbo: website_sale code
    @http.route(['/quotation/<int:order_id>/transaction/'], type='json', auth="public", website=True)
    def payment_transaction_token(self, acquirer_id, order_id, save_token=False,access_token=None, **kwargs):
        """ Json method that creates a payment.transaction, used to create a
        transaction when the user clicks on 'pay now' button. After having
        created the transaction, the event continues and the user is redirected
        to the acquirer website.

        :param int acquirer_id: id of a payment.acquirer record. If not set the
                                user is redirected to the checkout page
        """
        # Ensure a payment acquirer is selected
        if not acquirer_id:
            return False

        try:
            acquirer_id = int(acquirer_id)
        except:
            return False

        order = request.env['sale.order'].sudo().browse(order_id)
        if not order or not order.order_line:
            return False

        # Create transaction
        vals = {
            'acquirer_id': acquirer_id,
            'type': order._get_payment_type(),
        }

        transaction = order._create_payment_transaction(vals)

        return transaction.render_sale_button(
            order,
            '/my/orders/%s%s' % (order_id, '?access_token=%s' % access_token if access_token else ''),
             submit_txt=_('Pay & Confirm'),
            render_values={
                 'type': order._get_payment_type(),
                 'alias_usage': _('If we store your payment information on our server, subscription payments will be made automatically.'),
             }
        )

    @http.route('/quotation/<int:order_id>/transaction/token', type='http', auth='public', website=True)
    def payment_token(self, order_id, pm_id=None, **kwargs):

        order = request.env['sale.order'].sudo().browse(order_id)
        if not order or not order.order_line or pm_id is None:
            return request.redirect("/my/orders/%s" % order_id)

        # try to convert pm_id into an integer, if it doesn't work redirect the user to the quote
        try:
            pm_id = int(pm_id)
        except ValueError:
            return request.redirect('/my/orders/%s' % order_id)

        # Create transaction
        vals = {
            'payment_token_id': pm_id,
            'type': 'server2server',
        }

        order._create_payment_transaction(vals)

        return request.redirect('/my/orders/%s?access_token=%s' % (order_id, order.access_token))
