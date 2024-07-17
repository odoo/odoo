# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint

from odoo import _, models
from odoo.exceptions import UserError, ValidationError

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment_worldline import const


_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _get_specific_rendering_values(self, processing_values):
        """ Override of `payment` to return Worldline-specific processing values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic processing values of the transaction.
        :return: The dict of provider-specific processing values.
        :rtype: dict
        """
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != 'worldline':
            return res

        converted_amount = payment_utils.to_minor_currency_units(self.amount, self.currency_id)
        checkout_session_info = self.provider_id._worldline_create_hosted_checkout_session(
            self, converted_amount
        )
        rendering_values = {
            'merchant_reference': self.reference,
            'amount': str(converted_amount),
            'currency': self.currency_id.name,
            'language': self.partner_lang[:2],
            'customer_email': self.partner_id.email_normalized,
            'api_url': checkout_session_info['redirectUrl'],
        }

        return rendering_values

    def _send_payment_request(self):
        """ Override of payment to send a payment request to Worldline.

        Note: self.ensure_one()

        :return: None
        :raise UserError: If the transaction is not linked to a token.
        """
        super()._send_payment_request()
        if self.provider_code != 'worldline':
            return

        # Prepare the payment request to Worldline.
        if not self.token_id:
            raise UserError("Worldline: " + _("The transaction is not linked to a token."))

        # see https://apireference.connect.worldline-solutions.com/s2sapi/v1/en_US/go/payments/create.html?paymentPlatform=ALL
        request_body = {
            'cardPaymentMethodSpecificInput': {
                'authorizationMode': 'SALE',  # Force the capture
                'token': self.token_id.provider_ref,
                'unscheduledCardOnFileRequestor': 'merchantInitiated',
                'unscheduledCardOnFileSequenceIndicator': 'subsequent',
            },
            'order': {
                'amountOfMoney': {
                    'currencyCode': self.currency_id.name,
                    'amount': payment_utils.to_minor_currency_units(self.amount, self.currency_id),
                },
                'references': {
                    'merchantReference': self.reference,
                },
            },
        }

        endpoint = '/v2/' + self.provider_id.worldline_psp_id + '/payments'

        # Make the payment request to Worldline.
        response_content = self.provider_id._worldline_make_request(endpoint, payload=request_body)

        # Handle the payment request response.
        _logger.info(
            "payment request response for transaction with reference %s:\n%s",
            self.reference, pprint.pformat(response_content)
        )
        self._handle_notification_data('worldline', response_content)

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """ Override of `payment` to find the transaction based on Worldline data.

        :param str provider_code: The code of the provider that handled the transaction.
        :param dict notification_data: The notification data sent by the provider.
        :return: The transaction if found.
        :rtype: recordset of `payment.transaction`
        :raise ValidationError: If inconsistent data are received.
        :raise ValidationError: If the data match no transaction.
        """
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'worldline' or len(tx) == 1:
            return tx

        payment_output = notification_data.get('payment', {}).get('paymentOutput', {})
        references = payment_output.get('references', {})
        reference = references.get('merchantReference', '')
        if not reference:
            raise ValidationError(
                "Worldline: " + _("Received data with missing reference %(ref)s.", ref=reference)
            )

        tx = self.search(
            [('reference', '=', reference), ('provider_code', '=', 'worldline')]
        )
        if not tx:
            raise ValidationError(
                "Worldline: " + _("No transaction found matching reference %s.", reference)
            )

        return tx

    def _process_notification_data(self, notification_data):
        """ Override of `payment' to process the transaction based on Worldline data.

        Note: self.ensure_one()

        :param dict notification_data: The notification data sent by the provider.
        :return: None
        :raise ValidationError: If inconsistent data are received.
        """
        super()._process_notification_data(notification_data)
        if self.provider_code != 'worldline':
            return

        # Update the payment method.
        payment_output = notification_data.get('payment', {}).get('paymentOutput', {})
        if 'cardPaymentMethodSpecificOutput' in payment_output:
            payment_method_data = payment_output['cardPaymentMethodSpecificOutput']
        else:
            payment_method_data = payment_output.get('redirectPaymentMethodSpecificOutput', {})
        payment_option = payment_method_data.get('paymentProductId', '')
        payment_method = self.env['payment.method']._get_from_code(
            payment_option, mapping=const.PAYMENT_METHODS_MAPPING
        )
        self.payment_method_id = payment_method or self.payment_method_id

        # Update the payment state.
        status = notification_data.get('payment', {}).get('status')
        if not status:
            raise ValidationError("Worldline: " + _("Received data with missing payment state."))
        if status in const.PAYMENT_STATUS_MAPPING['pending']:
            self._set_pending()
        elif status in const.PAYMENT_STATUS_MAPPING['done']:
            has_token_data = 'token' in payment_method_data
            if self.tokenize and has_token_data:
                self._worldline_tokenize_from_notification_data(notification_data)
            self._set_done()
        else:  # Classify unsupported payment state as `error` tx state.
            _logger.info(
                "Received data with invalid payment status (%(status)s) for transaction with"
                " reference %(ref)s",
                {'status': status, 'ref': self.reference},
            )
            self._set_error("Worldline: " + _(
                "Received invalid transaction status %(status)s.", status=status
            ))

    def _worldline_tokenize_from_notification_data(self, notification_data):
        """ Create a new token based on the notification data.

        Note: self.ensure_one()

        :param dict notification_data: The notification data sent by the provider
        :return: None
        """
        self.ensure_one()

        payment_output = notification_data['payment'].get('paymentOutput', {})
        payment_method_data = payment_output.get('cardPaymentMethodSpecificOutput', {})
        token = self.env['payment.token'].create({
            'provider_id': self.provider_id.id,
            'payment_method_id': self.payment_method_id.id,
            'payment_details': payment_method_data['card']['cardNumber'].strip('*'),
            'partner_id': self.partner_id.id,
            'provider_ref': payment_method_data['token'],
        })
        self.write({
            'token_id': token,
            'tokenize': False,
        })
        _logger.info(
            "Created token with id %(token_id)s for partner with id %(partner_id)s from "
            "transaction with reference %(ref)s",
            {'token_id': token.id, 'partner_id': self.partner_id.id, 'ref': self.reference},
        )
