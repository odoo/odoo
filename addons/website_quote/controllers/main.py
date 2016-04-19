# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import werkzeug

from odoo import fields, SUPERUSER_ID, _
from odoo import http
from odoo.http import request
from odoo.addons.website_mail.controllers.main import _message_post_helper


class sale_quote(http.Controller):
    @http.route([
        "/quote/<int:order_id>",
        "/quote/<int:order_id>/<token>"
    ], type='http', auth="public", website=True)
    def view(self, order_id, pdf=None, token=None, message=False, **post):
        # use SUPERUSER_ID allow to access/view order for public user
        # only if he knows the private token
        now = fields.Date.today()
        if token:
            order = request.env['sale.order'].sudo().search([('id', '=', order_id), ('access_token', '=', token)])
            # Log only once a day
            if order and request.session.get('view_quote') != now:
                request.session['view_quote'] = now
                body = _('Quotation viewed by customer')
                _message_post_helper(res_model='sale.order', res_id=order.id, message=body, token=token, token_field="access_token", message_type='notification')
        else:
            order = request.env['sale.order'].search([('id', '=', order_id)])

        if not order:
            return request.website.render('website.404')

        action = request.env.ref('sale.action_quotations')
        days = 0
        if order.validity_date:
            days = (fields.Date.from_string(order.validity_date) - fields.Date.from_string(fields.Date.today())).days + 1
        if pdf:
            Report = request.env['report']
            pdf = Report.sudo().with_context(set_viewport_size=True).get_pdf(order, 'website_quote.report_quote', data=None)
            pdfhttpheaders = [('Content-Type', 'application/pdf'), ('Content-Length', len(pdf))]
            return request.make_response(pdf, headers=pdfhttpheaders)
        transaction_id = request.session.get('quote_%s_transaction_id' % order.id)
        if not transaction_id:
            transaction = request.env['payment.transaction'].sudo().search([('reference', '=', order.name)])
        else:
            transaction = request.env['payment.transaction'].sudo().browse(transaction_id)
        values = {
            'quotation': order,
            'message': message and int(message) or False,
            'option': bool(filter(lambda x: not x.line_id, order.options)),
            'order_valid': (not order.validity_date) or (now <= order.validity_date),
            'days_valid': days,
            'action': action.id,
            'breadcrumb': request.env.user.partner_id == order.partner_id,
            'tx_id': transaction.id,
            'tx_state': transaction.state,
            'tx_post_msg': transaction.acquirer_id.post_msg if transaction.acquirer_id else False,
            'need_payment': order.invoice_status == 'to invoice' and transaction.state in ['draft', 'cancel', 'error'],
            'token': token,
        }

        if order.require_payment or values['need_payment']:
            Payment_Acquirer = request.env['payment.acquirer']
            user = token and SUPERUSER_ID or request.uid
            values['acquirers'] = list(Payment_Acquirer.sudo(user=user).search([('website_published', '=', True), ('company_id', '=', order.company_id.id)]))
            extra_context = {
                'submit_class': 'btn btn-primary',
                'submit_txt': _('Pay & Confirm')
            }
            for acquirer in values['acquirers']:
                # TOFIX: very ugly/unreliable way to assign property to recordset, recordset added to list for shallow reference
                acquirer.button = acquirer.with_context(**extra_context).render(
                    '/',
                    order.amount_total,
                    order.pricelist_id.currency_id.id,
                    values={
                        'return_url': '/quote/%s/%s' % (order_id, token) if token else '/quote/%s' % order_id,
                        'type': 'form',
                        'alias_usage': _('If we store your payment information on our server, subscription payments will be made automatically.'),
                        'partner_id': order.partner_id.id,
                    })[0]
        return request.website.render('website_quote.so_quotation', values)

    @http.route(['/quote/accept'], type='json', auth="public", website=True)
    def accept(self, order_id, token=None, signer=None, sign=None, **post):
        Order_sudo = request.env['sale.order'].sudo()
        order = Order_sudo.browse(order_id)
        if token != order.access_token or order.require_payment:
            return request.website.render('website.404')
        if order.state != 'sent':
            return False
        attachments = sign and [('signature.png', sign.decode('base64'))] or []
        order.action_confirm()
        message = _('Order signed by %s') % (signer,)
        _message_post_helper(message=message, res_id=order_id, res_model='sale.order', attachments=attachments, **({'token': token, 'token_field': 'access_token'} if token else {}))
        return True

    @http.route(['/quote/<int:order_id>/<token>/decline'], type='http', auth="public", methods=['POST'], website=True)
    def decline(self, order_id, token, **post):
        Order_sudo = request.env['sale.order'].sudo()
        order = Order_sudo.browse(order_id)
        if token != order.access_token:
            return request.website.render('website.404')
        if order.state != 'sent':
            return werkzeug.utils.redirect("/quote/%s/%s?message=4" % (order_id, token))
        order.action_cancel()
        message = post.get('decline_message')
        if message:
            _message_post_helper(message=message, res_id=order_id, res_model='sale.order', **{'token': token, 'token_field': 'access_token'} if token else {})
        return werkzeug.utils.redirect("/quote/%s/%s?message=2" % (order_id, token))

    @http.route(['/quote/update_line'], type='json', auth="public", website=True)
    def update(self, line_id, remove=False, unlink=False, order_id=None, token=None, **post):
        Order_sudo = request.env['sale.order'].sudo()
        Order_Line_sudo = request.env['sale.order.line'].sudo()
        order = Order_sudo.browse(int(order_id))
        if token != order.access_token:
            return request.website.render('website.404')
        if order.state not in ('draft', 'sent'):
            return False
        order_line = Order_Line_sudo.browse(int(line_id))
        if unlink:
            order_line.unlink()
            return False
        number = (remove and -1 or 1)
        quantity = order_line.product_uom_qty + number
        order_line.write({'product_uom_qty': quantity})
        return [str(quantity), str(order.amount_total)]

    @http.route(["/quote/template/<model('sale.quote.template'):quote>"], type='http', auth="user", website=True)
    def template_view(self, quote, **post):
        values = {'template': quote}
        return request.website.render('website_quote.so_template', values)

    @http.route(["/quote/add_line/<int:option_id>/<int:order_id>/<token>"], type='http', auth="public", website=True)
    def add(self, option_id, order_id, token, **post):
        Order_sudo = request.env['sale.order'].sudo()
        Order_Option_sudo = request.env['sale.order.option'].sudo()
        Order_Line_sudo = request.env['sale.order.line'].sudo()

        order = Order_sudo.browse(order_id)
        if token != order.access_token:
            return request.website.render('website.404')
        if order.state not in ['draft', 'sent']:
            return request.website.render('website.http_error', {'status_code': 'Forbidden', 'status_message': _('You cannot add options to a confirmed order.')})
        option = Order_Option_sudo.browse(option_id)

        vals = {
            'price_unit': option.price_unit,
            'website_description': option.website_description,
            'name': option.name,
            'order_id': order.id,
            'product_id': option.product_id.id,
            'layout_category_id': option.layout_category_id.id,
            'product_uom_qty': option.quantity,
            'product_uom': option.uom_id.id,
            'discount': option.discount,
        }

        order_line = Order_Line_sudo.create(vals)
        order_line._compute_tax_id()
        option.line_id = order_line
        return werkzeug.utils.redirect("/quote/%s/%s#pricing" % (order.id, token))

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
        Payment_Transaction_Sudo = request.env['payment.transaction'].sudo()
        Order_Sudo = request.env['sale.order'].sudo()

        order = Order_Sudo.browse(order_id)
        if not order or not order.order_line or acquirer_id is None:
            return request.redirect("/quote/%s" % order_id)

        # find an already existing transaction
        transaction = Payment_Transaction_Sudo.search([('reference', '=', order.name)])
        if transaction:
            if transaction.sale_order_id.id != order.id or transaction.state in ['error', 'cancel'] or transaction.acquirer_id.id != acquirer_id:
                transaction = False
            elif transaction.state == 'draft':
                transaction.write({
                    'amount': order.amount_total,
                })
        if not transaction:
            transaction = Payment_Transaction_Sudo.create({
                'acquirer_id': acquirer_id,
                'type': order._get_payment_type(),
                'amount': order.amount_total,
                'currency_id': order.pricelist_id.currency_id.id,
                'partner_id': order.partner_id.id,
                'reference': Payment_Transaction_Sudo.get_next_reference(order.name),
                'sale_order_id': order.id,
                'callback_eval': "self.sale_order_id._confirm_online_quote(self)"
            })
            request.session['quote_%s_transaction_id' % order.id] = transaction.id

            # update quotation
            order.write({
                    'payment_acquirer_id': acquirer_id,
                    'payment_tx_id': transaction.id
                })

        # confirm the quotation
        if transaction.acquirer_id.auto_confirm == 'at_pay_now':
            order.with_context(send_email=True).action_confirm()
        render_context = {
            'submit_class': 'btn btn-primary',
            'submit_txt': _('Pay & Confirm')
        }
        return transaction.acquirer_id.with_context(**render_context).render(
            transaction.reference,
            order.amount_total,
            order.pricelist_id.currency_id.id,
            values={
                'return_url': '/quote/%s/%s' % (order_id, token) if token else '/quote/%s' % order_id,
                'type': order._get_payment_type(),
                'alias_usage': _('If we store your payment information on our server, subscription payments will be made automatically.'),
                'partner_id': order.partner_shipping_id.id or order.partner_invoice_id.id,
                'billing_partner_id': order.partner_invoice_id.id,
            })[0]
