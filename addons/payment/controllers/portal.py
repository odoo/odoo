# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http, _
from odoo.http import request


class WebsitePayment(http.Controller):
    @http.route(['/my/payment_method'], type='http', auth="user", website=True)
    def payment_method(self, **kwargs):
        acquirers = list(request.env['payment.acquirer'].search([('website_published', '=', True), ('registration_view_template_id', '!=', False), ('payment_flow', '=', 's2s')]))
        partner = request.env.user.partner_id
        payment_tokens = partner.payment_token_ids
        payment_tokens |= partner.commercial_partner_id.sudo().payment_token_ids
        return_url = request.params.get('redirect', '/my/payment_method')
        values = {
            'pms': payment_tokens,
            'acquirers': acquirers,
            'error_message': [kwargs['error']] if kwargs.get('error') else False,
            'return_url': return_url,
            'bootstrap_formatting': True,
            'partner_id': partner.id
        }
        return request.render("payment.pay_methods", values)

    @http.route(['/website_payment/pay'], type='http', auth='public', website=True)
    def pay(self, reference='', order_id=None, amount=False, currency_id=None, acquirer_id=None, **kw):
        env = request.env
        user = env.user.sudo()

        # Default values
        values = {
            'amount': 0.0,
            'currency': user.company_id.currency_id,
        }

        # Check sale order
        if order_id:
            try:
                order_id = int(order_id)
                order = env['sale.order'].browse(order_id)
                values.update({
                    'currency': order.currency_id,
                    'amount': order.amount_total,
                    'order_id': order_id
                })
            except:
                order_id = None

        # Check currency
        if currency_id:
            try:
                currency_id = int(currency_id)
                values['currency'] = env['res.currency'].browse(currency_id)
            except:
                pass

        # Check amount
        if amount:
            try:
                amount = float(amount)
                values['amount'] = amount
            except:
                pass

        # Check reference
        reference_values = order_id and {'sale_order_ids': [(4, order_id)]} or {}
        values['reference'] = env['payment.transaction']._compute_reference(values=reference_values, prefix=reference)

        # Check acquirer
        acquirers = None
        if acquirer_id:
            acquirers = env['payment.acquirer'].browse(int(acquirer_id))
        if not acquirers:
            acquirers = env['payment.acquirer'].search([('website_published', '=', True), ('company_id', '=', user.company_id.id)])

        # Check partner
        partner_id = user.partner_id.id if not user._is_public() else False

        values.update({
            'return_url': '/website_payment/confirm',
            'partner_id': partner_id,
            'bootstrap_formatting': True,
            'error_msg': kw.get('error_msg')
        })

        values['s2s_acquirers'] = [acq for acq in acquirers if acq.payment_flow == 's2s']
        values['form_acquirers'] = [acq for acq in acquirers if acq.payment_flow == 'form']
        values['pms'] = request.env['payment.token'].search([('acquirer_id', 'in', [acq.id for acq in values['s2s_acquirers']])])

        return request.render('payment.pay', values)

    @http.route(['/website_payment/transaction/<string:reference>/<string:amount>/<string:currency_id>',
                '/website_payment/transaction/v2/<string:amount>/<string:currency_id>/<path:reference>',], type='json', auth='public')
    def transaction(self, acquirer_id, reference, amount, currency_id, **kwargs):
        partner_id = request.env.user.partner_id.id if not request.env.user._is_public() else False
        acquirer = request.env['payment.acquirer'].browse(acquirer_id)
        order_id = kwargs.get('order_id')

        values = {
            'acquirer_id': int(acquirer_id),
            'reference': reference,
            'amount': float(amount),
            'currency_id': int(currency_id),
            'partner_id': partner_id,
            'type': 'form_save' if acquirer.save_token != 'none' and partner_id else 'form',
        }

        if order_id:
            values['sale_order_ids'] = [(6, 0, [order_id])]

        tx = request.env['payment.transaction'].sudo().with_context(lang=None).create(values)

        render_values = {
            'return_url': '/website_payment/confirm?tx_id=%d' % tx.id,
            'partner_id': partner_id,
        }

        return acquirer.sudo().render(reference, float(amount), int(currency_id), values=render_values)

    @http.route(['/website_payment/token/<string:reference>/<string:amount>/<string:currency_id>',
                '/website_payment/token/v2/<string:amount>/<string:currency_id>/<path:reference>'], type='http', auth='public', website=True)
    def payment_token(self, pm_id, reference, amount, currency_id, return_url=None, **kwargs):
        token = request.env['payment.token'].browse(int(pm_id))
        order_id = kwargs.get('order_id')

        if not token:
            return request.redirect('/website_payment/pay?error_msg=%s' % _('Cannot setup the payment.'))

        partner_id = request.env.user.partner_id.id if not request.env.user._is_public() else False

        values = {
            'acquirer_id': token.acquirer_id.id,
            'reference': reference,
            'amount': float(amount),
            'currency_id': int(currency_id),
            'partner_id': partner_id,
            'payment_token_id': pm_id,
            'type': 'form_save' if token.acquirer_id.save_token != 'none' and partner_id else 'form',
        }

        if order_id:
            values['sale_order_ids'] = [(6, 0, [order_id])]

        tx = request.env['payment.transaction'].sudo().with_context(lang=None).create(values)

        try:
            res = tx.s2s_do_transaction()
        except Exception as e:
            return request.redirect('/website_payment/pay?error_msg=%s' % _('Payment transaction failed.'))

        valid_state = 'authorized' if tx.acquirer_id.capture_manually else 'done'
        if not res or tx.state != valid_state:
            return request.redirect('/website_payment/pay?error_msg=%s' % _('Payment transaction failed.'))

        return request.redirect(return_url if return_url else '/website_payment/confirm?tx_id=%d' % tx.id)

    @http.route(['/website_payment/confirm'], type='http', auth='public', website=True)
    def confirm(self, **kw):
        tx_id = int(kw.get('tx_id', 0))
        if tx_id:
            tx = request.env['payment.transaction'].browse(tx_id)
            if tx.state == 'done':
                status = 'success'
                message = tx.acquirer_id.done_msg
            elif tx.state == 'pending':
                status = 'warning'
                message = tx.acquirer_id.pending_msg
            else:
                status = 'danger'
                message = tx.acquirer_id.error_msg
            return request.render('payment.confirm', {'tx': tx, 'status': status, 'message': message})
        else:
            return request.redirect('/my/home')
