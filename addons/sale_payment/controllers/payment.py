# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http, _
from odoo.addons.portal.controllers.portal import _build_url_w_params
from odoo.http import request, route


class PaymentPortal(http.Controller):

    @route('/pay/sale/<int:order_id>/form_tx', type='json', auth="public", website=True)
    def sale_pay_form(self, acquirer_id, order_id, save_token=False, access_token=None, **kwargs):
        """ Json method that creates a payment.transaction, used to create a
        transaction when the user clicks on 'pay now' button on the payment
        form.

        :return html: form containing all values related to the acquirer to
                      redirect customers to the acquirer website """
        success_url = kwargs.get('success_url', '/my')

        order_sudo = request.env['sale.order'].sudo().browse(order_id)
        if not order_sudo:
            return False

        try:
            acquirer = request.env['payment.acquirer'].browse(int(acquirer_id))
        except:
            return False

        if request.env.user == request.env.ref('base.public_user'):
            save_token = False

        token = request.env['payment.token'].sudo()  # currently no support of payment tokens
        tx = request.env['payment.transaction'].sudo()._check_or_create_sale_tx(
            order_sudo,
            acquirer,
            payment_token=token,
            tx_type='form_save' if save_token else 'form',
        )

        # set the transaction id into the session
        request.session['portal_sale_%s_transaction_id' % order_sudo.id] = tx.id

        return tx.render_sale_button(
            order_sudo,
            success_url,
            submit_txt=_('Pay'),
            render_values={
                'type': 'form_save' if save_token else 'form',
                'alias_usage': _('If we store your payment information on our server, subscription payments will be made automatically.'),
            }
        )

    @http.route('/pay/sale/<int:order_id>/s2s_token_tx', type='http', auth='public', website=True)
    def sale_pay_token(self, order_id, pm_id=None, **kwargs):
        """ Use a token to perform a s2s transaction """
        error_url = kwargs.get('error_url', '/my')
        success_url = kwargs.get('success_url', '/my')
        access_token = kwargs.get('access_token')
        params = {}
        if access_token:
            params['access_token'] = access_token

        order_sudo = request.env['sale.order'].sudo().browse(order_id).exists()
        if not order_sudo:
            params['error'] = 'pay_sale_invalid_doc'
            return request.redirect(_build_url_w_params(error_url, params))

        try:
            token = request.env['payment.token'].sudo().browse(int(pm_id))
        except (ValueError, TypeError):
            token = False

        token_owner = order_sudo.partner_id if request.env.user == request.env.ref('base.public_user') else request.env.user.partner_id
        if not token or token.partner_id != token_owner:
            params['error'] = 'pay_sale_invalid_token'
            return request.redirect(_build_url_w_params(error_url, params))

        # find an existing tx or create a new one
        tx = request.env['payment.transaction'].sudo()._check_or_create_sale_tx(
            order_sudo,
            token.acquirer_id,
            payment_token=token,
            tx_type='server2server',
        )

        # set the transaction id into the session
        request.session['portal_sale_%s_transaction_id' % order_sudo.id] = tx.id

        # proceed to the payment
        res = tx.confirm_sale_token()
        if tx.state != 'authorized' or not tx.acquirer_id.capture_manually:
            if res is not True:
                params['error'] = res
                return request.redirect(_build_url_w_params(error_url, params))
            params['success'] = 'pay_sale'
        return request.redirect(_build_url_w_params(success_url, params))
