# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _
from odoo.exceptions import AccessError, MissingError, ValidationError
from odoo.http import request, route

from odoo.addons.payment.controllers import portal as payment_portal
from odoo.addons.payment.controllers.post_processing import PaymentPostProcessing


class PaymentPortal(payment_portal.PaymentPortal):

    @route('/invoice/transaction/<int:invoice_id>', type='json', auth='public', csrf=True)
    def invoice_transaction(  # TODO ANV merge with /payment/transaction
        self, invoice_id, payment_option_id, amount, currency_id, partner_id, flow,
        tokenization_requested, landing_route, access_token, **kwargs
    ):
        """ Create a draft `payment.transaction` record and return its processing values.

        :param int invoice_id: The invoice to pay, as an `account.move` id
        :param int payment_option_id: The payment option handling the transaction, as a
                                      `payment.acquirer` id or a `payment.token` id
        :param float amount: The amount to pay in the given currency
        :param int currency_id: The currency of the transaction, as a `res.currency` id
        :param int partner_id: The partner making the payment, as a `res.partner` id
        :param str flow: The online payment flow of the transaction: 'redirect', 'direct' or 'token'
        :param bool tokenization_requested: Whether the user requested that a token is created
        :param str landing_route: The route the user is redirected to after the transaction
        :param str access_token: The access token used to authenticate the request
        :param dict kwargs: Optional data. Locally processed keys: order_id
        :return: The mandatory values for the processing of the transaction
        :rtype: dict
        :raise: ValidationError if the invoice id or the access token is invalid
        """
        # Check the invoice id and the access token
        try:
            self._document_check_access('account.move', invoice_id, access_token)
        except MissingError as error:
            raise error
        except AccessError:
            raise ValidationError("The access token is missing or invalid.")

        # Prepare the create values that are common to all online payment flows
        create_tx_values = {
            'reference': None,  # The reference is computed based on the invoice at creation time
            'amount': amount,
            'currency_id': currency_id,
            'partner_id': partner_id,
            'operation': f'online_{flow}',
            'landing_route': landing_route,
            'invoice_ids': [(6, 0, [invoice_id])],
        }

        processing_values = {}  # The generic and acquirer-specific values to process the tx
        if flow in ['redirect', 'direct']:  # Direct payment or payment with redirection
            acquirer_sudo = request.env['payment.acquirer'].sudo().browse(payment_option_id)
            tokenize = bool(
                # Public users are not allowed to save tokens as their partner is unknown
                not request.env.user.sudo()._is_public()
                # Token is only saved if requested by the user and allowed by the acquirer
                and tokenization_requested and acquirer_sudo.allow_tokenization
            )
            tx_sudo = request.env['payment.transaction'].sudo().with_context(lang=None).create({
                'acquirer_id': acquirer_sudo.id,
                'tokenize': tokenize,
                **create_tx_values,
            })  # In sudo mode to allow writing on callback fields
            processing_values = tx_sudo._get_processing_values()
        elif flow == 'token':  # Payment by token
            token_sudo = request.env['payment.token'].sudo().browse(payment_option_id).exists()
            if not token_sudo:
                raise UserError(_("No token token with id %s could be found.", payment_option_id))
            tx_sudo = request.env['payment.transaction'].sudo().with_context(lang=None).create({
                'acquirer_id': token_sudo.acquirer_id.id,
                'token_id': payment_option_id,
                **create_tx_values,
            })  # In sudo mode to allow writing on callback fields
            tx_sudo._send_payment_request()  # Tokens process transactions immediately
            # The dict of processing values is not filled in token flow since the user is redirected
            # to the payment process page directly from the client
        else:
            raise UserError(
                _("The payment should either be direct, with redirection, or made by a token.")
            )

        # Monitor the transaction to make it available in the portal
        PaymentPostProcessing.monitor_transactions(tx_sudo)

        # TODO ANV there used to be a call to tx._log_sent_message(). See if still necessary
        return processing_values
