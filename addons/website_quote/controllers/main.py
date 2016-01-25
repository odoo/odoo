# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import werkzeug

from odoo import fields, http, _
from odoo.http import request
from odoo.addons.website_mail.controllers.main import _message_post_helper


class SaleQuote(http.Controller):
    @http.route([
        "/quote/<int:order_id>",
        "/quote/<int:order_id>/<token>"
    ], type='http', auth="public", website=True)
    def view(self, order_id, pdf=None, token=None, message=False, **post):
        # use sudo() allow to access/view order for public user
        # only if he knows the private token
        SaleOrder = request.env['sale.order']
        now = fields.Date.from_string(fields.Date.today())
        if token:
            order = SaleOrder.sudo().search([('id', '=', order_id), ('access_token', '=', token)])
            if not order:
                return request.website.render('website.404')
            # Log only once a day
            if request.session.get('view_quote', False) != now:
                request.session['view_quote'] = now
                body = _('Quotation viewed by customer')
                _message_post_helper(res_model='sale.order', res_id=order.id, message=body, token=token, token_field="access_token", message_type='notification')
        else:
            order = SaleOrder.browse(order_id)
        days = 0
        if order.validity_date:
            days = (fields.Datetime.from_string(order.validity_date) - fields.Datetime.from_string(fields.Datetime.now())).days + 1
        if pdf:
            pdf = request.env['report'].sudo().get_pdf(order, 'website_quote.report_quote')
            pdfhttpheaders = [('Content-Type', 'application/pdf'), ('Content-Length', len(pdf))]
            return request.make_response(pdf, headers=pdfhttpheaders)
        user = request.env['res.users'].sudo().browse(request.uid)
        payment_transaction = request.env['payment.transaction'].sudo().search([('reference', '=', order.name)])
        values = {
            'quotation': order,
            'message': message and int(message) or False,
            'option': bool(order.options.filtered(lambda x: not x.line_id)),
            'order_valid': (not order.validity_date) or (now <= fields.Date.from_string(order.validity_date)),
            'days_valid': days,
            'breadcrumb': user.partner_id == order.partner_id,
            'action': request.env.ref('sale.action_quotations').id,
            'tx_id': payment_transaction.id,
            'tx_state': payment_transaction.state if payment_transaction else False,
            'tx_post_msg': payment_transaction.acquirer_id.post_msg if payment_transaction else False,
            'need_payment': order.invoice_status == 'to invoice' and (not payment_transaction or payment_transaction.state in ['draft', 'cancel', 'error']),
            'token': token,
        }

        if order.require_payment or values['need_payment']:
            PaymentAcquirer = request.env['payment.acquirer']
            values['acquirers'] = list(PaymentAcquirer.search([('website_published', '=', True), ('company_id', '=', order.company_id.id)]))
            render_ctx = dict(request.env.context, submit_class='btn btn-primary', submit_txt=_('Pay & Confirm'))
            for acquirer in values['acquirers']:
                acquirer.button = acquirer.with_context(render_ctx).render(
                    order.name,
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
        order_sudo = request.env['sale.order'].sudo().search([('id', '=', int(order_id)), ('access_token', '=', token)])
        if not order_sudo:
            return request.website.render('website.404')
        if order_sudo.state != 'sent':
            return False
        attachments = sign and [('signature.png', sign.decode('base64'))] or []
        order_sudo.action_confirm()
        message = _('Order signed by %s') % (signer,)
        _message_post_helper(message=message, res_id=order_sudo, res_model='sale.order', attachments=attachments, **({'token': token, 'token_field': 'access_token'} if token else {}))
        return True

    @http.route(['/quote/<int:order_id>/<token>/decline'], type='http', auth="public", methods=['POST'], website=True)
    def decline(self, order_id, token, **post):
        order_sudo = request.env['sale.order'].sudo().browse(order_id)
        if not order_sudo:
            return request.website.render('website.404')
        if order_sudo.state != 'sent':
            return werkzeug.utils.redirect("/quote/%s/%s?message=4" % (order_id, token))
        order_sudo.action_cancel()
        message = post.get('decline_message')
        if message:
            _message_post_helper(message=message, res_id=order_id, res_model='sale.order', **{'token': token, 'token_field': 'access_token'} if token else {})
        return werkzeug.utils.redirect("/quote/%s/%s?message=2" % (order_id, token))

    @http.route(['/quote/update_line'], type='json', auth="public", website=True)
    def update(self, line_id, remove=False, unlink=False, order_id=None, token=None, **post):
        order_sudo = request.env['sale.order'].sudo().browse(int(order_id))
        if not order_sudo:
            return request.website.render('website.404')
        if order_sudo.state not in ('draft', 'sent'):
            return False
        line_id = int(line_id)
        if unlink:
            request.env['sale.order.line'].search([('id', '=', line_id), ('order_id', '=', order_id)]).sudo().unlink()
            return False
        number = (remove and -1 or 1)
        order_line = request.env['sale.order.line'].sudo().browse(line_id)
        order_line.product_uom_qty += number
        return [str(order_line.product_uom_qty), str(order_sudo.amount_total)]

    @http.route(["/quote/template/<model('sale.quote.template'):quote>"], type='http', auth="user", website=True)
    def template_view(self, quote, **post):
        return request.website.render('website_quote.so_template', {'template': quote})

    @http.route(["/quote/add_line/<int:option_id>/<int:order_id>/<token>"], type='http', auth="public", website=True)
    def add(self, option_id, order_id, token, **post):
        vals = {}
        order_sudo = request.env['sale.order'].sudo().browse(order_id)
        if not order_sudo:
            return request.website.render('website.404')
        if order_sudo.state not in ['draft', 'sent']:
            return request.website.render('website.http_error', {'status_code': 'Forbidden', 'status_message': _('You cannot add options to a confirmed order.')})
        option_sudo = request.env['sale.order.option'].sudo().browse(option_id)

        vals = {
            'price_unit': option_sudo.price_unit,
            'website_description': option_sudo.website_description,
            'name': option_sudo.name,
            'order_id': order_sudo.id,
            'product_id': option_sudo.product_id.id,
            'product_uom_qty': option_sudo.quantity,
            'product_uom': option_sudo.uom_id.id,
            'discount': option_sudo.discount,
        }
        order_line = request.env['sale.order.line'].sudo().create(vals)
        order_line._compute_tax_id()
        option_sudo.line_id = order_line.id
        return werkzeug.utils.redirect("/quote/%s/%s#pricing" % (order_sudo.id, token))

    # note dbo: website_sale code
    @http.route(['/quote/<int:order_id>/transaction/<int:acquirer_id>'], type='json', auth="public", website=True)
    def payment_transaction(self, acquirer_id, order_id):
        """ Json method that creates a payment.transaction, used to create a
        transaction when the user clicks on 'pay now' button. After having
        created the transaction, the event continues and the user is redirected
        to the acquirer website.

        :param int acquirer_id: id of a payment.acquirer record. If not set the
                                user is redirected to the checkout page
        """
        PaymentTransaction = request.env['payment.transaction']
        order_sudo = request.env['sale.order'].sudo().browse(order_id)

        if not order_sudo or not order_sudo.order_line or acquirer_id is None:
            return request.redirect("/quote/" + str(order_id))

        # find an already existing transaction
        transaction_sudo = PaymentTransaction.sudo().search([('reference', '=', order_sudo.name)])
        if transaction_sudo:
            if transaction_sudo.state == 'draft':  # button cliked but no more info -> rewrite on tx or create a new one ?
                transaction_sudo.acquirer_id = acquirer_id
        else:
            transaction_sudo = PaymentTransaction.sudo().create({
                'acquirer_id': acquirer_id,
                'type': 'form',
                'amount': order_sudo.amount_total,
                'currency_id': order_sudo.pricelist_id.currency_id.id,
                'partner_id': order_sudo.partner_id.id,
                'reference': order_sudo.name,
                'sale_order_id': order_sudo.id,
                'callback_eval': "self.env['sale.order']._confirm_online_quote(self.sale_order_id.id, self)"
            })
            # update quotation
            order_sudo.write({
                'payment_acquirer_id': acquirer_id,
                'payment_tx_id': transaction_sudo.id
            })
        # confirm the quotation
        if transaction_sudo.acquirer_id.auto_confirm == 'at_pay_now':
            order_sudo.with_context(send_email=True).action_confirm()
        return transaction_sudo.id
