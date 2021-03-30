# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
import pprint

from werkzeug import urls

from odoo import _, api, models
from odoo.exceptions import UserError, ValidationError

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment_odoo.const import CURRENCY_DECIMALS, RESULT_CODES_MAPPING
from odoo.addons.payment_odoo.controllers.main import OdooController

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _get_specific_rendering_values(self, processing_values):
        """ Override of payment to return Odoo-specific rendering values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic and specific processing values of the transaction
        :return: The dict of acquirer-specific processing values
        :rtype: dict
        """
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider != 'odoo':
            return res

        converted_amount = payment_utils.to_minor_currency_units(
            self.amount, self.currency_id, CURRENCY_DECIMALS.get(self.currency_id.name)
        )
        # The lang is taken from the context rather than from the partner because it is not required
        # to be logged to make a payment and because the lang is not always set on the partner.
        # Adyen only supports a reduced set of languages but, instead of looking for the closest
        # match in https://docs.adyen.com/checkout/components-web/localization-components, we simply
        # provide the lang string as is (after adapting the format) and let Adyen find the best fit.
        lang_code = (self._context.get('lang') or 'en-US').replace('_', '-')
        base_url = self.acquirer_id._get_base_url()
        signature = payment_utils.generate_access_token(
            converted_amount, self.currency_id.name, self.reference
        )
        data = {
            'adyen_uuid': self.acquirer_id.odoo_adyen_account_id.adyen_uuid,
            'payout': self.acquirer_id.odoo_adyen_payout_id.code,
            'amount': {
                'value': converted_amount,
                'currency': self.currency_id.name,
            },
            'reference': self.reference,
            'shopperLocale': lang_code,
            'shopperReference': self.acquirer_id._odoo_compute_shopper_reference(
                self.partner_id.id
            ),
            'recurringProcessingModel': 'CardOnFile',
            'storePaymentMethod': self.tokenize,  # True by default on Adyen side
            # Since the Pay by Link API redirects the customer without any payload, we use the
            # /payment/status route directly as return url.
            'returnUrl': urls.url_join(base_url, '/payment/status'),
            'metadata': {
                'merchant_signature': signature,
                'notification_url': urls.url_join(base_url, OdooController._notification_url),
            },  # Proxy-specific data
        }
        return {
            'data': json.dumps(data),
            'api_url': self.acquirer_id._odoo_get_api_url(),
        }

    def _send_payment_request(self):
        """ Override of payment to send a payment request to Adyen through the Odoo proxy.

        Note: self.ensure_one()

        :return: None
        :raise: UserError if the transaction is not linked to a token
        """
        super()._send_payment_request()
        if self.provider != 'odoo':
            return

        # Make the payment request
        if not self.token_id:
            raise UserError("Odoo Payments: " + _("The transaction is not linked to a token."))

        converted_amount = payment_utils.to_minor_currency_units(
            self.amount, self.currency_id, CURRENCY_DECIMALS.get(self.currency_id.name)
        )
        base_url = self.acquirer_id._get_base_url()
        signature = payment_utils.generate_access_token(
            converted_amount, self.currency_id.name, self.reference
        )
        data = {
            'payout': self.acquirer_id.odoo_adyen_payout_id.code,
            'amount': {
                'value': converted_amount,
                'currency': self.currency_id.name,
            },
            'reference': self.reference,
            'paymentMethod': {
                'type': self.token_id.odoo_payment_method_type,
                'storedPaymentMethodId': self.token_id.acquirer_ref,
            },
            'shopperReference': self.acquirer_id._odoo_compute_shopper_reference(
                self.partner_id.id
            ),
            'recurringProcessingModel': 'Subscription',
            'shopperInteraction': 'ContAuth',
            'metadata': {
                'merchant_signature': signature,
                'notification_url': urls.url_join(base_url, OdooController._notification_url),
            },  # Proxy-specific data
        }
        response_content = self.acquirer_id.odoo_adyen_account_id._adyen_rpc('payments', data)

        # Handle the payment request response
        _logger.info("payment request response:\n%s", pprint.pformat(response_content))
        self._handle_feedback_data('odoo', response_content)

    @api.model
    def _get_tx_from_feedback_data(self, provider, data):
        """ Override of payment to find the transaction based on Adyen data.

        :param str provider: The provider of the acquirer that handled the transaction
        :param dict data: The feedback data sent by the provider
        :return: The transaction if found
        :rtype: recordset of `payment.transaction`
        :raise: ValidationError if inconsistent data were received
        :raise: ValidationError if the data match no transaction
        """
        tx = super()._get_tx_from_feedback_data(provider, data)
        if provider != 'odoo':
            return tx

        reference = data.get('merchantReference')
        if not reference:
            raise ValidationError(
                "Odoo Payments: " + _("Received data with missing merchant reference")
            )

        tx = self.search([('reference', '=', reference), ('provider', '=', 'odoo')])
        if not tx:
            raise ValidationError(
                "Odoo Payments: " + _("No transaction found matching reference %s.", reference)
            )
        return tx

    def _process_feedback_data(self, data):
        """ Override of payment to process the transaction based on Adyen data.

        Since only webhook notifications send data, the parsing is exclusively done according to the
        structure of NotificationRequestItem object.
        See https://docs.adyen.com/development-resources/webhooks/notifications-api

        Note: self.ensure_one()

        :param dict data: The feedback data sent by the provider
        :return: None
        :raise: ValidationError if inconsistent data were received
        """
        super()._process_feedback_data(data)
        if self.provider != 'odoo':
            return

        # Handle the acquirer reference
        if 'pspReference' in data:
            self.acquirer_reference = data.get('pspReference')

        # Handle the payment state
        payment_state = data.get('resultCode')
        if not payment_state:
            raise ValidationError(
                "Odoo Payments: " + _("Received data with missing payment state.")
            )

        if payment_state in RESULT_CODES_MAPPING['pending']:
            self._set_pending()
        elif payment_state in RESULT_CODES_MAPPING['done']:
            has_token_data = 'recurring.recurringDetailReference' in data.get('additionalData', {})
            if self.tokenize and has_token_data:
                self._odoo_tokenize_from_feedback_data(data)
            self._set_done()
        elif payment_state in RESULT_CODES_MAPPING['cancel']:
            self._set_canceled()
        else:  # Classify unsupported payment state as `error` tx state
            _logger.info("received data with invalid payment state: %s", payment_state)
            self._set_error(
                "Odoo Payments: " + _("Received data with invalid payment state: %s", payment_state)
            )

    def _odoo_tokenize_from_feedback_data(self, data):
        """ Create a new token based on the feedback data.

        Note: self.ensure_one()

        :param dict data: The feedback data sent by the provider
        :return: None
        """
        self.ensure_one()

        # Retrieve all stored payment methods for the customer from the API and match them with the
        # acquirer reference of the transaction to find its payment method
        response_content = self.acquirer_id.odoo_adyen_account_id._adyen_rpc(
            'payment_methods',
            dict(shopperReference=data['additionalData']['recurring.shopperReference']),
        )
        payment_methods = response_content['storedPaymentMethods']
        acquirer_ref = data['additionalData']['recurring.recurringDetailReference']
        payment_method_type = next(pm['type'] for pm in payment_methods if pm['id'] == acquirer_ref)

        # Create the token
        token = self.env['payment.token'].create({
            'acquirer_id': self.acquirer_id.id,
            'name': payment_utils.build_token_name(data['additionalData'].get('cardSummary')),
            'partner_id': self.partner_id.id,
            'acquirer_ref': acquirer_ref,
            'verified': True,  # The payment is authorized, so the payment method is valid
            'odoo_payment_method_type': payment_method_type,
        })
        self.write({
            'token_id': token,
            'tokenize': False,
        })
        _logger.info(
            "created token with id %s for partner with id %s", token.id, self.partner_id.id
        )
