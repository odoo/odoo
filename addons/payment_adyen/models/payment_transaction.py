# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment_adyen.models.payment_acquirer import CURRENCY_DECIMALS

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    adyen_payment_data = fields.Char(
        string="Saved Payment Data",
        help="Data that must be passed back to Adyen when returning from redirect", readonly=True,
        groups='base.group_system')  # TODO ANV review group

    #=== BUSINESS METHODS ===#

    def _get_specific_processing_values(self, processing_values):
        """ Return a dict of acquirer-specific values used to process the transaction.

        Note: self.ensure_one()

        :param dict processing_values: The generic processing values of the transaction
        :return: The dict of acquirer-specific processing values
        :rtype: dict
        """

        if self.acquirer_id.provider != 'adyen':
            return super()._get_specific_processing_values(processing_values)

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

    def _send_payment_request(self):
        """ Request Adyen to execute the payment.

        :return: None
        """
        super()._send_payment_request()  # Log the 'sent' message

        if self.acquirer_id.provider != 'adyen':
            return

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
            tx._handle_feedback_data('adyen', response_content)

    @api.model
    def _get_tx_from_feedback_data(self, provider, data):
        """ Find the transaction based on the feedback data.

        :param str provider: The provider of the acquirer that handled the transaction
        :param dict data: The feedback data sent by the acquirer
        :return: The transaction if found
        :rtype: recordset of `payment.transaction`
        :raise: ValidationError if inconsistent data were received
        """
        if provider != 'adyen':
            return super()._get_tx_from_feedback_data(provider, data)

        reference = data.get('merchantReference')
        if not reference:
            raise ValidationError("Adyen: " + _("Received data with missing merchant reference"))

        tx = self.env['payment.transaction'].search([('reference', '=', reference)])
        if not tx or len(tx) > 1:
            raise ValidationError(
                "Adyen: " + _(
                    "received data with reference %(ref)s matching %(num_tx)d transaction(s)",
                    ref=reference, num_tx=len(tx)
                )
            )
        return tx

    def _process_feedback_data(self, data):
        """ Update the transaction state and the acquirer reference based on the feedback data.

        See https://docs.adyen.com/checkout/payment-result-codes for the exhaustive list of codes.

        Note: self.ensure_one()

        :param dict data: The feedback data sent by the acquirer
        :return: None
        :raise: ValidationError if inconsistent data were received
        """
        super()._process_feedback_data(data)
        if self.provider != 'adyen':
            return

        # Handle the acquirer reference
        if 'pspReference' in data:
            self.acquirer_reference = data.get('pspReference')

        # Handle the payment state
        payment_state = data.get('resultCode')
        if not payment_state:
            raise ValidationError("Adyen: " + _("Received data with missing payment state."))

        if payment_state in (
            'ChallengeShopper', 'IdentifyShopper', 'Pending', 'PresentToShopper', 'Received',
            'RedirectShopper'
        ):  # `pending` tx state
            if self.state != 'pending':  # Redundant feedbacks can be sent through the webhook
                self._set_pending()
        elif payment_state == 'Authorised':  # `done` tx state
            has_token_data = 'recurring.recurringDetailReference' in data.get('additionalData', {})
            if self.tokenize and has_token_data:
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
        elif payment_state == 'Cancelled':  # `cancel` tx state
            if self.state != 'cancel':  # Redundant feedbacks can be sent through the webhook
                self._set_canceled()
        else:  # `error` tx state
            if self.state != 'error':  # Redundant feedbacks can be sent through the webhook
                _logger.info(f"received data with invalid payment state: {payment_state}")
                self._set_error(
                    "Adyen: " + _("Received data with invalid payment state: %s", payment_state)
                )
