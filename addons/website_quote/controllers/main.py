# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import werkzeug

from odoo import exceptions, fields, http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import get_records_pager
from odoo.addons.sale.controllers.portal import CustomerPortal
from odoo.addons.portal.controllers.mail import _message_post_helper
from odoo.osv import expression


class CustomerPortal(CustomerPortal):

    @http.route()
    def portal_order_page(self, order=None, access_token=None, **kw):
        try:
            order_sudo = self._order_check_access(order, access_token=access_token)
        except exceptions.AccessError:
            pass
        else:
            if order_sudo.template_id and order_sudo.template_id.active:
                return request.redirect('/quote/%s/%s' % (order, access_token or ''))
        return super(CustomerPortal, self).portal_order_page(order=order, access_token=access_token, **kw)

    def _portal_quote_user_can_accept(self, order_id):
        result = super(CustomerPortal, self)._portal_quote_user_can_accept(order_id)
        order_sudo = request.env['sale.order'].sudo().browse(order_id)
        # either use quote template settings or fallback on default behavior
        return not order_sudo.require_payment if order_sudo.template_id else result


class sale_quote(http.Controller):

    @http.route("/quote/<int:order_id>", type='http', auth="user", website=True)
    def view_user(self, *args, **kwargs):
        return self.view(*args, **kwargs)

    @http.route("/quote/<int:order_id>/<token>", type='http', auth="public", website=True)
    def view(self, order_id, pdf=None, token=None, message=False, **post):
        # use sudo to allow accessing/viewing orders for public user
        # only if he knows the private token
        now = fields.Date.today()
        if token:
            Order = request.env['sale.order'].sudo().search([('id', '=', order_id), ('access_token', '=', token)])
        else:
            Order = request.env['sale.order'].search([('id', '=', order_id)])
        # Log only once a day
        if Order and request.session.get('view_quote_%s' % Order.id) != now and request.env.user.share:
            request.session['view_quote_%s' % Order.id] = now
            body = _('Quotation viewed by customer')
            _message_post_helper(res_model='sale.order', res_id=Order.id, message=body, token=Order.access_token, message_type='notification', subtype="mail.mt_note", partner_ids=Order.user_id.sudo().partner_id.ids)
        if not Order:
            return request.render('website.404')

        # Token or not, sudo the order, since portal user has not access on
        # taxes, required to compute the total_amout of SO.
        order_sudo = Order.sudo()

        days = 0
        if order_sudo.validity_date:
            days = (fields.Date.from_string(order_sudo.validity_date) - fields.Date.from_string(fields.Date.today())).days + 1
        if pdf:
            pdf = request.env.ref('website_quote.report_web_quote').sudo().with_context(set_viewport_size=True).render_qweb_pdf([order_sudo.id])[0]
            pdfhttpheaders = [('Content-Type', 'application/pdf'), ('Content-Length', len(pdf))]
            return request.make_response(pdf, headers=pdfhttpheaders)
        transaction_id = request.session.get('quote_%s_transaction_id' % order_sudo.id)
        if not transaction_id:
            Transaction = request.env['payment.transaction'].sudo().search([('reference', '=', order_sudo.name)])
        else:
            Transaction = request.env['payment.transaction'].sudo().browse(transaction_id)
        values = {
            'quotation': order_sudo,
            'message': message and int(message) or False,
            'option': any(not x.line_id for x in order_sudo.options),
            'order_valid': (not order_sudo.validity_date) or (now <= order_sudo.validity_date),
            'days_valid': days,
            'action': request.env.ref('sale.action_quotations').id,
            'no_breadcrumbs': request.env.user.partner_id.commercial_partner_id not in order_sudo.message_partner_ids,
            'tx_id': Transaction.id if Transaction else False,
            'tx_state': Transaction.state if Transaction else False,
            'tx_post_msg': Transaction.acquirer_id.post_msg if Transaction else False,
            'payment_tx': Transaction,
            'need_payment': order_sudo.invoice_status == 'to invoice' and Transaction.state in ['draft', 'cancel', 'error'],
            'token': token,
            'return_url': '/shop/payment/validate',
            'bootstrap_formatting': True,
            'partner_id': order_sudo.partner_id.id,
        }

        if order_sudo.require_payment or values['need_payment']:
            domain = expression.AND([
                ['&', ('website_published', '=', True), ('company_id', '=', order_sudo.company_id.id)],
                ['|', ('specific_countries', '=', False), ('country_ids', 'in', [order_sudo.partner_id.country_id.id])]
            ])
            acquirers = request.env['payment.acquirer'].sudo().search(domain)

            values['form_acquirers'] = [acq for acq in acquirers if acq.payment_flow == 'form' and acq.view_template_id]
            values['s2s_acquirers'] = [acq for acq in acquirers if acq.payment_flow == 's2s' and acq.registration_view_template_id]
            values['pms'] = request.env['payment.token'].search(
                [('partner_id', '=', order_sudo.partner_id.id),
                ('acquirer_id', 'in', [acq.id for acq in values['s2s_acquirers']])])

            for acq in values['form_acquirers']:
                acq.form = acq.render('/', order_sudo.amount_total, order_sudo.pricelist_id.currency_id.id,
                    values={
                        'return_url': '/quote/%s/%s' % (order_id, token) if token else '/quote/%s' % order_id,
                        'type': 'form',
                        'alias_usage': _('If we store your payment information on our server, subscription payments will be made automatically.'),
                        'partner_id': order_sudo.partner_id.id,
                    })
        history = request.session.get('my_quotes_history', [])
        values.update(get_records_pager(history, order_sudo))
        return request.render('website_quote.so_quotation', values)

    @http.route(['/quote/<int:order_id>/<token>/decline'], type='http', auth="public", methods=['POST'], website=True)
    def decline(self, order_id, token, **post):
        Order = request.env['sale.order'].sudo().browse(order_id)
        if token != Order.access_token:
            return request.render('website.404')
        if Order.state != 'sent':
            return werkzeug.utils.redirect("/quote/%s/%s?message=4" % (order_id, token))
        Order.action_cancel()
        message = post.get('decline_message')
        if message:
            _message_post_helper(message=message, res_id=order_id, res_model='sale.order', **{'token': token} if token else {})
        return werkzeug.utils.redirect("/quote/%s/%s?message=2" % (order_id, token))

    @http.route(['/quote/update_line'], type='json', auth="public", website=True)
    def update(self, line_id, remove=False, unlink=False, order_id=None, token=None, **post):
        Order = request.env['sale.order'].sudo().browse(int(order_id))
        if token != Order.access_token:
            return request.render('website.404')
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

    @http.route(["/quote/template/<model('sale.quote.template'):quote>"], type='http', auth="user", website=True)
    def template_view(self, quote, **post):
        values = {'template': quote}
        return request.render('website_quote.so_template', values)

    @http.route(["/quote/add_line/<int:option_id>/<int:order_id>/<token>"], type='http', auth="public", website=True)
    def add(self, option_id, order_id, token, **post):
        Order = request.env['sale.order'].sudo().browse(order_id)
        if token != Order.access_token:
            return request.render('website.404')
        if Order.state not in ['draft', 'sent']:
            return request.render('website.http_error', {'status_code': 'Forbidden', 'status_message': _('You cannot add options to a confirmed order.')})
        Option = request.env['sale.order.option'].sudo().browse(option_id)
        vals = {
            'price_unit': Option.price_unit,
            'website_description': Option.website_description,
            'name': Option.name,
            'order_id': Order.id,
            'product_id': Option.product_id.id,
            'layout_category_id': Option.layout_category_id.id,
            'product_uom_qty': Option.quantity,
            'product_uom': Option.uom_id.id,
            'discount': Option.discount,
        }

        OrderLine = request.env['sale.order.line'].sudo().create(vals)
        OrderLine._compute_tax_id()
        Option.write({'line_id': OrderLine.id})
        return werkzeug.utils.redirect("/quote/%s/%s#pricing" % (Order.id, token))

    # note dbo: website_sale code
    @http.route(['/quote/<int:order_id>/transaction/'], type='json', auth="public", website=True)
    def payment_transaction_token(self, acquirer_id, order_id, save_token=False,access_token=None, **kwargs):
        """ Json method that creates a payment.transaction, used to create a
        transaction when the user clicks on 'pay now' button. After having
        created the transaction, the event continues and the user is redirected
        to the acquirer website.

        :param int acquirer_id: id of a payment.acquirer record. If not set the
                                user is redirected to the checkout page
        """
        order = request.env['sale.order'].sudo().browse(order_id)
        if not order or not order.order_line or acquirer_id is None:
            return False

        # find an already existing transaction
        acquirer = request.env['payment.acquirer'].browse(int(acquirer_id))
        token = request.env['payment.token'].sudo()  # currently no support of payment tokens
        tx = request.env['payment.transaction'].sudo().search([('reference', '=', order.name)], limit=1)
        tx_type = order._get_payment_type()
        tx = tx._check_or_create_sale_tx(order, acquirer, payment_token=token, tx_type=tx_type)
        request.session['quote_%s_transaction_id' % order.id] = tx.id

        return tx.render_sale_button(order, '/quote/%s/%s' % (order_id, access_token) if access_token else '/quote/%s' % order_id,
                                     submit_txt=_('Pay & Confirm'), render_values={
                                         'type': order._get_payment_type(),
                                         'alias_usage': _('If we store your payment information on our server, subscription payments will be made automatically.'),
                                         })

    @http.route('/quote/<int:order_id>/transaction/token', type='http', auth='public', website=True)
    def payment_token(self, order_id, pm_id=None, **kwargs):

        order = request.env['sale.order'].sudo().browse(order_id)
        if not order or not order.order_line or pm_id is None:
            return request.redirect("/quote/%s" % order_id)

        # try to convert pm_id into an integer, if it doesn't work redirect the user to the quote
        try:
            pm_id = int(pm_id)
        except ValueError:
            return request.redirect('/quote/%s' % order_id)

        # retrieve the token from its id
        token = request.env['payment.token'].sudo().browse(pm_id)
        if not token:
            return request.redirect('/quote/%s' % order_id)

        # find an already existing transaction
        tx = request.env['payment.transaction'].sudo().search([('reference', '=', order.name)], limit=1)
        # set the transaction type to server2server
        tx_type = 'server2server'
        # check if the transaction exists, if not then it create one
        tx = tx._check_or_create_sale_tx(order, token.acquirer_id, payment_token=token, tx_type=tx_type)
        # set the transaction id into the session
        request.session['quote_%s_transaction_id' % order_id] = tx.id
        # proceed to the payment
        tx.confirm_sale_token()
        # redirect the user to the online quote
        return request.redirect('/quote/%s/%s' % (order_id, order.access_token))
