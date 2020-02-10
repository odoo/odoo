# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http, _
from odoo.exceptions import UserError
from odoo.addons.portal.controllers.portal import _build_url_w_params
from odoo.http import request, route


class PaymentPortal(http.Controller):

    @route('/invoice/pay/<int:invoice_id>/form_tx', type='json', auth="public", website=True)
    def invoice_pay_form(self, acquirer_id, invoice_id, save_token=False, access_token=None, **kwargs):
        """ Json method that creates a payment.transaction, used to create a
        transaction when the user clicks on 'pay now' button on the payment
        form.

        :return html: form containing all values related to the acquirer to
                      redirect customers to the acquirer website """
        success_url = kwargs.get('success_url', '/my')

        invoice_sudo = request.env['account.invoice'].sudo().browse(invoice_id)
        if not invoice_sudo:
            return False

        try:
            acquirer = request.env['payment.acquirer'].browse(int(acquirer_id))
        except:
            return False

        if request.env.user._is_public():
            save_token = False # we avoid to create a token for the public user

        token = request.env['payment.token'].sudo()  # currently no support of payment tokens
        tx = request.env['payment.transaction'].sudo()._check_or_create_invoice_tx(
            invoice_sudo,
            acquirer,
            payment_token=token,
            tx_type='form_save' if save_token else 'form',
        )

        # set the transaction id into the session
        request.session['portal_invoice_%s_transaction_id' % invoice_sudo.id] = tx.id

        return tx.render_invoice_button(
            invoice_sudo,
            success_url,
            submit_txt=_('Pay & Confirm'),
            render_values={
                'type': 'form_save' if save_token else 'form',
                'alias_usage': _('If we store your payment information on our server, subscription payments will be made automatically.'),
            }
        )

    @http.route('/invoice/pay/<int:invoice_id>/s2s_token_tx', type='http', auth='public', website=True)
    def invoice_pay_token(self, invoice_id, pm_id=None, **kwargs):
        """ Use a token to perform a s2s transaction """
        error_url = kwargs.get('error_url', '/my')
        success_url = kwargs.get('success_url', '/my')
        access_token = kwargs.get('access_token')
        params = {}
        if access_token:
            params['access_token'] = access_token

        invoice_sudo = request.env['account.invoice'].sudo().browse(invoice_id).exists()
        if not invoice_sudo:
            params['error'] = 'pay_invoice_invalid_doc'
            return request.redirect(_build_url_w_params(error_url, params))

        try:
            token = request.env['payment.token'].sudo().browse(int(pm_id))
        except (ValueError, TypeError):
            token = False
        token_owner = invoice_sudo.partner_id if request.env.user == request.env.ref('base.public_user') else request.env.user.partner_id
        if not token or token.partner_id != token_owner:
            params['error'] = 'pay_invoice_invalid_token'
            return request.redirect(_build_url_w_params(error_url, params))

        # find an existing tx or create a new one
        tx = request.env['payment.transaction'].sudo()._check_or_create_invoice_tx(
            invoice_sudo,
            token.acquirer_id,
            payment_token=token,
            tx_type='server2server',
        )

        # set the transaction id into the session
        request.session['portal_invoice_%s_transaction_id' % invoice_sudo.id] = tx.id

        # proceed to the payment
        res = tx.confirm_invoice_token()
        if tx.state != 'authorized' or not tx.acquirer_id.capture_manually:
            if res is not True:
                params['error'] = res
                return request.redirect(_build_url_w_params(error_url, params))
            params['success'] = 'pay_invoice'
        return request.redirect(_build_url_w_params(success_url, params))

    @http.route('/invoice/pay/<int:invoice_id>/s2s_json_token_tx', type='json', auth='public')
    def invoice_pay_token_json(self, invoice_id, pm_id=None, **kwargs):
        """ Use a token to perform a s2s transaction """
        invoice_sudo = request.env['account.invoice'].sudo().browse(invoice_id).exists()
        if not invoice_sudo:
            raise UserError(_('Faulty invoice'))

        try:
            token = request.env['payment.token'].sudo().browse(int(pm_id))
        except (ValueError, TypeError):
            token = False
        token_owner = invoice_sudo.partner_id if request.env.user == request.env.ref('base.public_user') else request.env.user.partner_id
        if not token or token.partner_id != token_owner:
            raise UserError(_('Invalid token'))
        # find an existing tx or create a new one
        tx = request.env['payment.transaction'].sudo()._check_or_create_invoice_tx(
            invoice_sudo,
            token.acquirer_id,
            payment_token=token,
            tx_type='server2server',
        )

        # set the transaction id into the session
        request.session['portal_invoice_%s_transaction_id' % invoice_sudo.id] = tx.id

        # proceed to the payment
        res = tx.with_context(off_session=False).confirm_invoice_token()
        tx_info = tx._get_json_info()
        return {
            'tx_info': tx_info,
            'redirect': '/my/invoices/%s' % (invoice_sudo.id),
        }