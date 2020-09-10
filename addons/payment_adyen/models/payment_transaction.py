# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

import odoo.addons.payment.utils as payment_utils
from odoo.addons.payment_adyen.models.payment_acquirer import CURRENCY_DECIMALS

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):

    _inherit = 'payment.transaction'

    adyen_payment_data = fields.Char(
        string="Saved Payment Data",
        help="Data that must be passed back to Adyen when returning from redirect", readonly=True)

    #=== BUSINESS METHODS ===#

    def _get_specific_processing_values(self, processing_values):
        """ Return a dict of acquirer-specific values used to process the transaction.

        Note: self.ensure_one()

        :param dict processing_values: The generic processing values of the transaction
        :return: The dict of acquirer-specific processing values
        :rtype: dict
        """

        if self.acquirer_id.provider != 'adyen':
            return super()._get_processing_values()

        converted_amount = payment_utils.convert_to_minor_units(
            self.amount, self.currency_id, CURRENCY_DECIMALS.get(self.currency_id.name)
        )
        return {
            'converted_amount': converted_amount,
            'access_token': payment_utils.generate_access_token(
                self.env['ir.config_parameter'].sudo().get_param('database.secret'),
                processing_values['reference'],
                converted_amount,
                processing_values['partner_id']
            )
        }

    def _send_payment_request(self, _operation='online'):
        """ Request Adyen to execute the payment.

        :param str _operation: The operation of the payment: 'online', 'offline' or 'validation'.
        :return: None
        """
        if self.acquirer_id.provider != 'adyen':
            return super()._send_payment_request(_operation)

        # Make the payment requests to Adyen
        for tx in self:
            if not tx.token_id:
                _logger.warning(
                    f"attempted to send a payment request for transaction with id {tx.id} which "
                    f"has no registered token"
                )
                continue

            acquirer = tx.acquirer_id
            converted_amount = payment_utils.convert_to_minor_units(
                tx.amount, tx.currency_id, CURRENCY_DECIMALS.get(tx.currency_id.name)
            )
            data = {
                'merchantAccount': acquirer.adyen_merchant_account,
                'amount': {
                    'value': converted_amount,
                    'currency': tx.currency_id.name,
                },
                'reference': tx.reference,
                'paymentMethod': {
                    'recurringDetailReference': tx.token_id.acquirer_ref
                },  # Required by Adyen although it is also provided with 'storedPaymentMethodId'
                'storedPaymentMethodId': tx.token_id.acquirer_ref,
                'shopperReference': tx.token_id.adyen_shopper_reference,
                'recurringProcessingModel': 'Subscription',
                'shopperInteraction': 'ContAuth',
            }
            response_content = acquirer._adyen_make_request(
                base_url=acquirer.adyen_checkout_api_url,
                endpoint_key='payments',
                payload=data,
                method='POST'
            )

            # Handle the payment request response
            _logger.info(f"payment request response:\n{pprint.pformat(response_content)}")
            tx._handle_feedback_data(response_content, 'adyen')

        return super()._send_payment_request(_operation)

    @api.model
    def _get_tx_from_data(self, data, provider):
        """ Find the transaction based on the transaction data.

        :param dict data: The transaction data sent by the acquirer
        :param str provider: The provider of the acquirer that handled the transaction
        :return: The payment.transaction record if found, else None
        :rtype: recordset or None
        """
        if provider != 'adyen':
            return super()._get_tx_from_data(data, provider)

        # Check that all necessary keys are in feedback data
        reference = data.get('merchantReference')
        if not reference:
            raise ValidationError("Adyen: " + _("Received data with missing merchant reference"))

        # Fetch the transaction based on the merchant reference
        tx = self.env['payment.transaction'].search([('reference', '=', reference)])
        if not tx or len(tx) > 1:
            raise ValidationError(
                "Adyen: " + _(
                    "received data with reference %(ref)s matching %(num_tx)d transaction(s)",
                    ref=reference, num_tx=len(tx)
                )
            )
        return tx

    def _get_invalid_parameters(self, data):
        """ List acquirer-specific invalid parameters and return them.

        Note: self.ensure_one()

        :param dict data: The transaction data sent by the acquirer
        :return: The dict of invalid parameters whose entries have the name of the parameter
                 as key and a tuple (expected value, received value) as value
        :rtype: dict
        """
        if self.provider != 'adyen':
            return super()._get_invalid_parameters(data)

        invalid_parameters = {}
        if not data.get('resultCode'):
            invalid_parameters['resultCode'] = ('something', data.get('resultCode'))
        return invalid_parameters

    def _process_feedback_data(self, data):
        """ Update the transaction status and the acquirer reference based on the feedback data.

        See https://docs.adyen.com/checkout/payment-result-codes for the exhaustive list of codes.

        Note: self.ensure_one()

        :param dict data: The transaction data sent by the acquirer
        :return: True the transaction status is recognized
        :rtype: bool
        """
        if self.provider != 'adyen':
            return super()._process_feedback_data(data)

        if 'pspReference' in data:
            self.acquirer_reference = data.get('pspReference')
        tx_status = data.get('resultCode', 'Pending')
        if tx_status in (
            'ChallengeShopper', 'IdentifyShopper', 'Pending', 'PresentToShopper', 'Received',
            'RedirectShopper'
        ):  # pending
            if self.state != 'pending':  # Redundant feedbacks can be sent through the webhook
                self._set_pending()
        elif tx_status == 'Authorised':  # done
            if self.tokenize \
                    and 'recurring.recurringDetailReference' in data.get('additionalData', {}):
                # Create the token with the data of the payment method  TODO probably factor that out when manage tokens is in da place
                token = self.env['payment.token'].create({
                    'name': f"XXXXXXXXXXXX{data['additionalData'].get('cardSummary', '????')}",
                    'partner_id': self.partner_id.id,
                    'acquirer_id': self.acquirer_id.id,
                    'acquirer_ref': data['additionalData']['recurring.recurringDetailReference'],
                    'adyen_shopper_reference': data['additionalData']['recurring.shopperReference'],
                    'verified': True,  # The payment is authorized, so the payment method is valid
                })
                self.token_id = token
                self.tokenize = False
                _logger.info(
                    f"created token with id {token.id} for partner with id {self.partner_id.id}"
                )
            if self.state != 'done':  # Redundant feedbacks can be sent through the webhook
                self._set_done()
        elif tx_status == 'Cancelled':  # cancel
            if self.state != 'cancel':  # Redundant feedbacks can be sent through the webhook
                self._set_canceled()
        else:  # error
            if self.state != 'error':  # Redundant feedbacks can be sent through the webhook
                _logger.info(f"received data with invalid transaction status: {tx_status}")
                self._set_error("Adyen: " + _(
                    "received data with invalid transaction status: %(tx_status)s",
                    tx_status=tx_status
                ))
                return False
        return True
