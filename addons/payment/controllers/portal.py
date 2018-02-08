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
    def pay(self, reference='', amount=False, currency_id=None, acquirer_id=None, **kw):
        env = request.env
        user = env.user.sudo()

        currency_id = currency_id and int(currency_id) or user.company_id.currency_id.id
        currency = env['res.currency'].browse(currency_id)

        # Try default one then fallback on first
        acquirer_id = acquirer_id and int(acquirer_id) or \
            env['ir.default'].get('payment.transaction', 'acquirer_id', company_id=user.company_id.id) or \
            env['payment.acquirer'].search([('website_published', '=', True), ('company_id', '=', user.company_id.id)])[0].id

        acquirer = env['payment.acquirer'].with_context(submit_class='btn btn-primary pull-right',
                                                        submit_txt=_('Pay Now')).browse(acquirer_id)
        # auto-increment reference with a number suffix if the reference already exists
        reference = request.env['payment.transaction'].get_next_reference(reference)

        partner_id = user.partner_id.id if not user._is_public() else False

        payment_form = acquirer.sudo().render(reference, float(amount), currency.id, values={'return_url': '/website_payment/confirm', 'partner_id': partner_id})
        values = {
            'reference': reference,
            'acquirer': acquirer,
            'currency': currency,
            'amount': float(amount),
            'payment_form': payment_form,
        }
        # TODO: remove return when payment is implemented with refactored payments, i.e. use of
        # payment.payment_tokens_list in the template.
        # return request.render('payment.pay', values)
        return request.render('website.404')

    @http.route(['/website_payment/transaction'], type='json', auth="public", website=True)
    def transaction(self, reference, amount, currency_id, acquirer_id):
        partner_id = request.env.user.partner_id.id if not request.env.user._is_public() else False
        values = {
            'acquirer_id': int(acquirer_id),
            'reference': reference,
            'amount': float(amount),
            'currency_id': int(currency_id),
            'partner_id': partner_id,
        }

        tx = request.env['payment.transaction'].sudo().create(values)
        request.session['website_payment_tx_id'] = tx.id
        return tx.id

    @http.route(['/website_payment/confirm'], type='http', auth='public', website=True)
    def confirm(self, **kw):
        tx_id = request.session.pop('website_payment_tx_id', False)
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
