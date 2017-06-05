# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http, _
from odoo.http import request
from odoo.exceptions import AccessError

from odoo.addons.payment.controllers.main import Payment


class Payment(Payment):

    @http.route()
    def pay(self, payment_request_id=None, token=None, pdf=None, **kwargs):
        payment_request = self._get_invoice_payment_request(payment_request_id, token, **kwargs)
        if not token:
            try:
                payment_request.invoice_id.check_access_rights('read')
                payment_request.invoice_id.check_access_rule('read')
            except AccessError:
                return request.render("website.403")

        if not payment_request:
            return request.render("website.403")
        return super(Payment, self).pay(payment_request_id=payment_request_id, token=token, pdf=pdf, **kwargs)

class WebsitePayment(http.Controller):
    @http.route(['/my/payment_method'], type='http', auth="user", website=True)
    def payment_method(self, **kwargs):
        acquirers = list(request.env['payment.acquirer'].search([('website_published', '=', True), ('registration_view_template_id', '!=', False)]))
        partner = request.env.user.partner_id
        payment_tokens = partner.payment_token_ids
        payment_tokens |= partner.commercial_partner_id.sudo().payment_token_ids
        values = {
            'pms': payment_tokens,
            'acquirers': acquirers
        }
        return_url = request.params.get('redirect', '/my/payment_method')
        for acquirer in acquirers:
            acquirer.form = acquirer.sudo()._registration_render(request.env.user.partner_id.id, {'error': {}, 'error_message': [], 'return_url': return_url, 'json': False, 'bootstrap_formatting': True})
        return request.render("website_payment.pay_methods", values)

    @http.route(['/website_payment/delete/'], methods=['POST'], type='http', auth="user", website=True)
    def delete(self, delete_pm_id=None):
        if delete_pm_id:
            pay_meth = request.env['payment.token'].browse(int(delete_pm_id))
            pay_meth.unlink()
        return request.redirect('/my/payment_method')

    @http.route(['/website_payment/pay'], type='http', auth='public', website=True)
    def pay(self, reference='', amount=False, currency_id=None, acquirer_id=None, **kw):
        env = request.env
        user = env.user.sudo()

        currency_id = currency_id and int(currency_id) or user.company_id.currency_id.id
        currency = env['res.currency'].browse(currency_id)

        # Try default one then fallback on first
        acquirer_id = acquirer_id and int(acquirer_id) or \
            env['ir.values'].get_default('payment.transaction', 'acquirer_id', company_id=user.company_id.id) or \
            env['payment.acquirer'].search([('website_published', '=', True), ('company_id', '=', user.company_id.id)])[0].id

        acquirer = env['payment.acquirer'].with_context(submit_class='btn btn-primary pull-right',
                                                        submit_txt=_('Pay Now')).browse(acquirer_id)
        # auto-increment reference with a number suffix if the reference already exists
        reference = request.env['payment.transaction'].get_next_reference(reference)

        partner_id = user.partner_id.id if user.partner_id.id != request.website.partner_id.id else False

        payment_form = acquirer.sudo().render(reference, float(amount), currency.id, values={'return_url': '/website_payment/confirm', 'partner_id': partner_id})
        values = {
            'reference': reference,
            'acquirer': acquirer,
            'currency': currency,
            'amount': float(amount),
            'payment_form': payment_form,
        }
        return request.render('website_payment.pay', values)

    @http.route(['/website_payment/transaction'], type='json', auth="public", website=True)
    def transaction(self, reference, amount, currency_id, acquirer_id):
        partner_id = request.env.user.partner_id.id if request.env.user.partner_id != request.website.partner_id else False
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
            return request.render('website_payment.confirm', {'tx': tx, 'status': status, 'message': message})
        else:
            return request.redirect('/my/home')

    @http.route(['/payment/transaction_token/confirm'], type='json', auth="public", website=True)
    def payment_transaction_token_confirm(self, tx_id, **kwargs):
        tx = request.env['payment.transaction'].sudo().browse(int(tx_id))
        if (tx and tx.payment_token_id and
                tx.partner_id == tx.payment_request_id.partner_id):
                return tx.validate_transaction_token('/payment/%s' % tx.payment_request_id.id)
        return dict(success=False, error='Tx missmatch')

    @http.route(['/payment/transaction_token'], type='http', methods=['POST'], auth="public", website=True)
    def payment_transaction_token(self, tx_id, **kwargs):
        tx = request.env['payment.transaction'].sudo().browse(int(tx_id))
        if (tx and tx.payment_token_id and tx.partner_id == tx.payment_request_id.partner_id):
            return request.render("website_payment.payment_token_form_confirm", dict(tx=tx, payment_request=tx.payment_request_id))
        else:
            return request.redirect("/payment/%s" % tx.payment_request_id.id, "?error=no_token_or_missmatch_tx")
