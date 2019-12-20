# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.urls import url_encode

from odoo import http, _
from odoo.addons.portal.controllers.portal import _build_url_w_params
from odoo.addons.payment.controllers.portal import PaymentProcessing
from odoo.http import request, route


class PaymentPortal(http.Controller):

    @route('/invoice/pay/<int:invoice_id>/form_tx', type='json', auth="public", website=True)
    def invoice_pay_form(self, acquirer_id, invoice_id, transaction_type='form', access_token=None, **kwargs):
        """ Json method that creates a payment.transaction, used to create a
        transaction when the user clicks on 'pay now' button on the payment
        form.

        :return html: form containing all values related to the acquirer to
                      redirect customers to the acquirer website """
        invoice_sudo = request.env['account.move'].sudo().browse(invoice_id)
        if not invoice_sudo:
            return False

        try:
            acquirer_id = int(acquirer_id)
        except:
            return False

        if request.env.user._is_public():
            transaction_type = 'form'  # we avoid to create a token for the public user

        success_url = kwargs.get(
            'success_url', "%s?%s" % (invoice_sudo.access_url, url_encode({'access_token': access_token}) if access_token else '')
        )
        vals = {
            'acquirer_id': acquirer_id,
            'return_url': success_url,
            'type': transaction_type
        }

        transaction = invoice_sudo._create_payment_transaction(vals)
        PaymentProcessing.add_payment_transaction(transaction)

        return transaction.render_invoice_button(
            invoice_sudo,
            submit_txt=_('Pay & Confirm'),
            render_values={
                'type': transaction_type,
                'alias_usage': _('If we store your payment information on our server, subscription payments will be made automatically.'),
            }
        )

    @http.route('/invoice/pay/<int:invoice_id>/s2s_token_tx', type='http', auth='public', website=True)
    def invoice_pay_token(self, invoice_id, pm_id=None, **kwargs):
        """ Use a token to perform a s2s transaction """
        error_url = kwargs.get('error_url', '/my')
        access_token = kwargs.get('access_token')
        params = {}
        if access_token:
            params['access_token'] = access_token

        invoice_sudo = request.env['account.move'].sudo().browse(invoice_id).exists()
        if not invoice_sudo:
            params['error'] = 'pay_invoice_invalid_doc'
            return request.redirect(_build_url_w_params(error_url, params))

        success_url = kwargs.get(
            'success_url', "%s?%s" % (invoice_sudo.access_url, url_encode({'access_token': access_token}) if access_token else '')
        )
        try:
            token = request.env['payment.token'].sudo().browse(int(pm_id))
        except (ValueError, TypeError):
            token = False
        token_owner = invoice_sudo.partner_id if request.env.user._is_public() else request.env.user.partner_id
        if not token or token.partner_id != token_owner:
            params['error'] = 'pay_invoice_invalid_token'
            return request.redirect(_build_url_w_params(error_url, params))

        vals = {
            'payment_token_id': token.id,
            'type': kwargs.get('transaction_type'),
            'return_url': _build_url_w_params(success_url, params),
        }

        tx = invoice_sudo._create_payment_transaction(vals)
        PaymentProcessing.add_payment_transaction(tx)

        params['success'] = 'pay_invoice'
        return request.redirect('/payment/process')
