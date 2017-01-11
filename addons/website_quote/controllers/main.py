# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import werkzeug

from odoo import fields, http, _
from odoo.http import request
from odoo.addons.website_mail.controllers.main import _message_post_helper
from odoo.addons.website_portal.controllers.main import get_records_pager


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
            # Log only once a day
            if Order and request.session.get('view_quote') != now:
                request.session['view_quote'] = now
                body = _('Quotation viewed by customer')
                _message_post_helper(res_model='sale.order', res_id=Order.id, message=body, token=token, token_field="access_token", message_type='notification', subtype="mail.mt_note", partner_ids=Order.user_id.partner_id.ids)
        else:
            Order = request.env['sale.order'].search([('id', '=', order_id)])

        if not Order:
            return request.render('website.404')

        days = 0
        if Order.validity_date:
            days = (fields.Date.from_string(Order.validity_date) - fields.Date.from_string(fields.Date.today())).days + 1
        if pdf:
            pdf = request.env['report'].sudo().with_context(set_viewport_size=True).get_pdf([Order.id], 'website_quote.report_quote')
            pdfhttpheaders = [('Content-Type', 'application/pdf'), ('Content-Length', len(pdf))]
            return request.make_response(pdf, headers=pdfhttpheaders)
        transaction_id = request.session.get('quote_%s_transaction_id' % Order.id)
        if not transaction_id:
            Transaction = request.env['payment.transaction'].sudo().search([('reference', '=', Order.name)])
        else:
            Transaction = request.env['payment.transaction'].sudo().browse(transaction_id)
        values = {
            'quotation': Order,
            'message': message and int(message) or False,
            'option': bool(filter(lambda x: not x.line_id, Order.options)),
            'order_valid': (not Order.validity_date) or (now <= Order.validity_date),
            'days_valid': days,
            'action': request.env.ref('sale.action_quotations').id,
            'breadcrumb': request.env.user.partner_id == Order.partner_id,
            'tx_id': Transaction.id if Transaction else False,
            'tx_state': Transaction.state if Transaction else False,
            'tx_post_msg': Transaction.acquirer_id.post_msg if Transaction else False,
            'need_payment': Order.invoice_status == 'to invoice' and Transaction.state in ['draft', 'cancel', 'error'],
            'token': token,
        }

        if Order.require_payment or values['need_payment']:
            values['acquirers'] = list(request.env['payment.acquirer'].sudo().search([('website_published', '=', True), ('company_id', '=', Order.company_id.id)]))
            extra_context = {
                'submit_class': 'btn btn-primary',
                'submit_txt': _('Pay & Confirm')
            }
            values['buttons'] = {}
            for acquirer in values['acquirers']:
                values['buttons'][acquirer.id] = acquirer.with_context(**extra_context).render(
                    '/',
                    Order.amount_total,
                    Order.pricelist_id.currency_id.id,
                    values={
                        'return_url': '/quote/%s/%s' % (order_id, token) if token else '/quote/%s' % order_id,
                        'type': 'form',
                        'alias_usage': _('If we store your payment information on our server, subscription payments will be made automatically.'),
                        'partner_id': Order.partner_id.id,
                    })
        history = request.session.get('my_quotes_history', [])
        values.update(get_records_pager(history, Order))
        return request.render('website_quote.so_quotation', values)

    @http.route(['/quote/accept'], type='json', auth="public", website=True)
    def accept(self, order_id, token=None, signer=None, sign=None, **post):
        Order = request.env['sale.order'].sudo().browse(order_id)
        if token != Order.access_token or Order.require_payment:
            return request.render('website.404')
        if Order.state != 'sent':
            return False
        attachments = [('signature.png', sign.decode('base64'))] if sign else []
        Order.action_confirm()
        message = _('Order signed by %s') % (signer,)
        _message_post_helper(message=message, res_id=order_id, res_model='sale.order', attachments=attachments, **({'token': token, 'token_field': 'access_token'} if token else {}))
        return True

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
            _message_post_helper(message=message, res_id=order_id, res_model='sale.order', **{'token': token, 'token_field': 'access_token'} if token else {})
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
    @http.route(['/quote/<int:order_id>/transaction/<int:acquirer_id>'], type='json', auth="public", website=True)
    def payment_transaction(self, acquirer_id, order_id):
        return self.payment_transaction_token(acquirer_id, order_id, None)

    @http.route(['/quote/<int:order_id>/transaction/<int:acquirer_id>/<token>'], type='json', auth="public", website=True)
    def payment_transaction_token(self, acquirer_id, order_id, token):
        """ Json method that creates a payment.transaction, used to create a
        transaction when the user clicks on 'pay now' button. After having
        created the transaction, the event continues and the user is redirected
        to the acquirer website.

        :param int acquirer_id: id of a payment.acquirer record. If not set the
                                user is redirected to the checkout page
        """
        PaymentTransaction = request.env['payment.transaction'].sudo()

        Order = request.env['sale.order'].sudo().browse(order_id)
        if not Order or not Order.order_line or acquirer_id is None:
            return request.redirect("/quote/%s" % order_id)

        # find an already existing transaction
        Transaction = PaymentTransaction.search([('reference', '=', Order.name)])
        if Transaction:
            if Transaction.sale_order_id != Order or Transaction.state in ['error', 'cancel'] or Transaction.acquirer_id.id != acquirer_id:
                Transaction = False
            elif Transaction.state == 'draft':
                Transaction.write({
                    'amount': Order.amount_total,
                })
        if not Transaction:
            Transaction = PaymentTransaction.create({
                'acquirer_id': acquirer_id,
                'type': Order._get_payment_type(),
                'amount': Order.amount_total,
                'currency_id': Order.pricelist_id.currency_id.id,
                'partner_id': Order.partner_id.id,
                'reference': PaymentTransaction.get_next_reference(Order.name),
                'sale_order_id': Order.id,
                'callback_model_id': request.env['ir.model'].sudo().search([('model', '=', Order._name)], limit=1).id,
                'callback_res_id': Order.id,
                'callback_method': '_confirm_online_quote',
            })
            request.session['quote_%s_transaction_id' % Order.id] = Transaction.id

            # update quotation
            Order.write({
                'payment_acquirer_id': acquirer_id,
                'payment_tx_id': Transaction.id
            })

        return Transaction.acquirer_id.with_context(
            submit_class='btn btn-primary',
            submit_txt=_('Pay & Confirm')).render(
            Transaction.reference,
            Order.amount_total,
            Order.pricelist_id.currency_id.id,
            values={
                'return_url': '/quote/%s/%s' % (order_id, token) if token else '/quote/%s' % order_id,
                'type': Order._get_payment_type(),
                'alias_usage': _('If we store your payment information on our server, subscription payments will be made automatically.'),
                'partner_id': Order.partner_shipping_id.id or Order.partner_invoice_id.id,
                'billing_partner_id': Order.partner_invoice_id.id,
            })
