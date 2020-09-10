# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import werkzeug

from odoo import http, _
from odoo.addons.portal.controllers.portal import _build_url_w_params
from odoo.addons.payment.controllers.portal import PaymentPostProcessing
from odoo.exceptions import AccessError, MissingError
from odoo.http import request, route


class PaymentPortal(http.Controller):

    @route('/invoice/pay/<int:invoice_id>', type='json', auth='public', website=True)
    def invoice_pay(
        self, invoice_id, payment_option_id, flow, tokenization_requested, access_token=None,
        **kwargs
    ):
        """ Create the transaction in draft and return its processing values.

        :param str invoice_id: The invoice to pay, as a `account.move` id
        :param int payment_option_id: The payment option handling the transaction, as a
                                      `payment.acquirer` id or a `payment.token` id
        :param str flow: The online payment flow of the transaction: 'redirect', 'direct' or 'token'
        :param bool tokenization_requested: Whether the user requested that a token is created
        :param str access_token: The access token used to authenticate the request
        :param dict kwargs: Optional data. Locally processed keys: order_id
        :return: The values necessary for the processing of the transaction
        :rtype: dict
        :raise: werkzeug.exceptions.NotFound if the invoice id or the access token is invalid
        """
        # Raise an HTTP 404 if the invoice id or the access token is incorrect to avoid leaking
        # information about (non-)existing ids
        try:
            invoice_sudo = self._document_check_access('account.move', invoice_id, access_token)
        except (AccessError, MissingError):
            raise werkzeug.exceptions.NotFound

        # Prepare the create values that are common to all online payment flows
        order_id = kwargs.get('order_id')
        tx_reference = request.env['payment.transaction']._compute_reference(
            invoice_ids=[invoice_id]
        )
        # TODO ANV continue from here
        # create_tx_values = {
        #     'reference': tx_reference,
        #     'amount': amount,
        #     'currency_id': currency_id,
        #     'partner_id': partner_id,
        #     'operation': f'online_{flow}' if not is_validation else 'validation',
        #     'landing_route': invoice_sudo.get_portal_url(),
        # }
        #
        # processing_values = {}  # The generic and acquirer-specific values to process the tx
        # if flow in ['redirect', 'direct']:  # Payment through (inline or redirect) form
        #     acquirer_sudo = request.env['payment.acquirer'].sudo().browse(payment_option_id)
        #     tokenize = bool(
        #         # Public users are not allowed to save tokens as their partner is unknown
        #         not request.env.user.sudo()._is_public()
        #         # Token is only saved if requested by the user and allowed by the acquirer
        #         and tokenization_requested and acquirer_sudo.allow_tokenization
        #     )
        #     tx_sudo = request.env['payment.transaction'].sudo().with_context(lang=None).create({
        #         'acquirer_id': acquirer_sudo.id,
        #         'tokenize': tokenize,
        #         **create_tx_values,
        #     })
        #     processing_values = tx_sudo._get_processing_values()
        # elif flow == 'token':  # Payment by token
        #     token_sudo = request.env['payment.token'].sudo().browse(payment_option_id).exists()
        #     if not token_sudo:
        #         raise UserError(_("No token token with id %s could be found.", payment_option_id))
        #     if order_id:
        #         create_tx_values.update(sale_order_ids=[(6, 0, [int(order_id)])])
        #     tx_sudo = request.env['payment.transaction'].sudo().with_context(lang=None).create({
        #         'acquirer_id': token_sudo.acquirer_id.id,
        #         'token_id': payment_option_id,
        #         **create_tx_values,
        #     })  # Created in sudo to allowed writing on callback fields
        #     tx_sudo._send_payment_request()  # Tokens process transactions immediately
        #     # The dict of processing values is not filled in token flow since the user is redirected
        #     # to the payment process page directly from the client
        # else:
        #     raise UserError(
        #         _("The payment should either be direct, with redirection, or made by a token.")
        #     )
        #
        # # Monitor the transaction to make it available in the portal
        # PaymentPostProcessing.monitor_transactions(tx_sudo)
        #
        # return processing_values

        # old code ->

        # acquirer_sudo = request.env['payment.acquirer'].browse(acquirer_id).sudo()
        # tokenize = bool(
        #     # Public users are not allowed to save tokens as their partner is unknown
        #     not request.env.user.sudo()._is_public()
        #     # Token is only saved if requested by the user and allowed by the acquirer
        #     and tokenization_requested and acquirer_sudo.allow_tokenization
        # )
        #
        # success_url = kwargs.get(
        #     'success_url', "%s?%s" % (invoice_sudo.access_url, werkzeug.urls.url_encode({'access_token': access_token}) if access_token else '')
        # )
        # vals = {
        #     'acquirer_id': acquirer_id,
        #     'landing_route': success_url,
        #     'operation': f'online_{flow}',
        #     'tokenize': tokenize,
        # }
        #
        # transaction = invoice_sudo._create_payment_transaction(vals)  # TODO ANV use inv._get_vals...
        # PaymentPostProcessing.monitor_transactions(transaction)
        #
        # return transaction.render_invoice_button(invoice_sudo)

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
            'success_url', "%s?%s" % (invoice_sudo.access_url, werkzeug.urls.url_encode({'access_token': access_token}) if access_token else '')
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
            'token_id': token.id,
            'operation': 'online_token',
            'landing_route': _build_url_w_params(success_url, params),
        }

        tx = invoice_sudo._create_payment_transaction(vals)  # TODO ANV use inv._get_vals... bis
        PaymentPostProcessing.monitor_transactions(tx)

        params['success'] = 'pay_invoice'
        return request.redirect('/payment/status')
