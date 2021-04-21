# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment_adyen.const import CURRENCY_DECIMALS, RESULT_CODES_MAPPING

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    adyen_payment_data = fields.Char(
        string="Saved Payment Data",
        help="Data that must be passed back to Adyen when returning from redirect", readonly=True,
        groups='base.group_system')
    adyen_capture_reference = fields.Char(
        string="Saved Capture Reference",
        help="If later on a notification came about the capture, this is the reference that'll \
        be used, and not the original pspreference.")
    adyen_cancel_reference = fields.Char(
        string="Saved Cancel Reference",
        help="If later on a notification came about the cancel, this is the reference that'll \
        be used, and not the original pspreference.")

    #=== BUSINESS METHODS ===#

    def _get_specific_processing_values(self, processing_values):
        """ Override of payment to return Adyen-specific processing values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic processing values of the transaction
        :return: The dict of acquirer-specific processing values
        :rtype: dict
        """
        res = super()._get_specific_processing_values(processing_values)
        if self.provider != 'adyen':
            return res

        converted_amount = payment_utils.to_minor_currency_units(
            self.amount, self.currency_id, CURRENCY_DECIMALS.get(self.currency_id.name)
        )
        return {
            'converted_amount': converted_amount,
            'access_token': payment_utils.generate_access_token(
                processing_values['reference'],
                converted_amount,
                processing_values['partner_id']
            )
        }

    def _send_payment_request(self):
        """ Override of payment to send a payment request to Adyen.

        Note: self.ensure_one()

        :return: None
        :raise: UserError if the transaction is not linked to a token
        """
        super()._send_payment_request()
        if self.provider != 'adyen':
            return

        # Prepare the payment request to Adyen
        if not self.token_id:
            raise UserError("Adyen: " + _("The transaction is not linked to a token."))

        converted_amount = payment_utils.to_minor_currency_units(
            self.amount, self.currency_id, CURRENCY_DECIMALS.get(self.currency_id.name)
        )
        data = {
            'merchantAccount': self.acquirer_id.adyen_merchant_account,
            'amount': {
                'value': converted_amount,
                'currency': self.currency_id.name,
            },
            'reference': self.reference,
            'paymentMethod': {
                'recurringDetailReference': self.token_id.acquirer_ref
            },  # Required by Adyen although it is also provided with 'storedPaymentMethodId'
            'storedPaymentMethodId': self.token_id.acquirer_ref,
            'shopperReference': self.token_id.adyen_shopper_reference,
            'recurringProcessingModel': 'Subscription',
            'shopperIP': payment_utils.get_customer_ip_address(),
            'shopperInteraction': 'ContAuth',
        }

        # Avoid authorisation without capture for users who have Adyen settings set as "manual"
        if not self.acquirer_id.capture_manually:
            data.update({"captureDelayHours": 0,})

        # Make the payment request to Adyen
        response_content = self.acquirer_id._adyen_make_request(
            url_field_name='adyen_checkout_api_url',
            endpoint='/payments',
            payload=data,
            method='POST'
        )

        # Handle the payment request response
        _logger.info("payment request response:\n%s", pprint.pformat(response_content))
        self._handle_feedback_data('adyen', response_content)

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
        if provider != 'adyen':
            return tx

        reference = data.get('merchantReference')
        if not reference:
            raise ValidationError("Adyen: " + _("Received data with missing merchant reference"))

        tx = self.search([('reference', '=', reference), ('provider', '=', 'adyen')])
        if not tx:
            raise ValidationError(
                "Adyen: " + _("No transaction found matching reference %s.", reference)
            )
        return tx

    def _process_feedback_data(self, data):
        """ Override of payment to process the transaction based on Adyen data.

        Note: self.ensure_one()

        :param dict data: The feedback data sent by the provider
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

        if payment_state in RESULT_CODES_MAPPING['pending']:
            self._set_pending()
        elif payment_state in RESULT_CODES_MAPPING['done']:
            has_token_data = 'recurring.recurringDetailReference' in data.get('additionalData', {})
            if self.tokenize and has_token_data:
                self._adyen_tokenize_from_feedback_data(data)
            if self.acquirer_id.capture_manually and self.state != 'authorized':
                self._set_authorized()
            else:
                self._set_done()
        elif payment_state in RESULT_CODES_MAPPING['cancel']:
            self._set_canceled()
        else:  # Classify unsupported payment state as `error` tx state
            _logger.warning("received data with invalid payment state: %s", payment_state)
            self._set_error(
                "Adyen: " + _("Received data with invalid payment state: %s", payment_state)
            )

    def _adyen_tokenize_from_feedback_data(self, data):
        """ Create a new token based on the feedback data.

        Note: self.ensure_one()

        :param dict data: The feedback data sent by the provider
        :return: None
        """
        self.ensure_one()

        token = self.env['payment.token'].create({
            'acquirer_id': self.acquirer_id.id,
            'name': payment_utils.build_token_name(data['additionalData'].get('cardSummary')),
            'partner_id': self.partner_id.id,
            'acquirer_ref': data['additionalData']['recurring.recurringDetailReference'],
            'adyen_shopper_reference': data['additionalData']['recurring.shopperReference'],
            'verified': True,  # The payment is authorized, so the payment method is valid
        })
        self.write({
            'token_id': token,
            'tokenize': False,
        })
        _logger.info(
            "created token with id %s for partner with id %s", token.id, self.partner_id.id
        )

    def _send_capture_request(self):
        """ Override of payment to send a capture request to Adyen.
        Note: self.ensure_one()
        :return: None
        """
        super()._send_capture_request()
        if self.provider != 'adyen':
            return

        converted_amount = payment_utils.to_minor_currency_units(
            self.amount, self.currency_id, CURRENCY_DECIMALS.get(self.currency_id.name)
        )
        data = {
            'merchantAccount': self.acquirer_id.adyen_merchant_account,
            'modificationAmount': {
                'value': converted_amount,
                'currency': self.currency_id.name,
            },
            'originalReference': self.acquirer_reference,
            'reference': self.reference,
        }
        response_content = self.acquirer_id._adyen_make_request(
            url_field_name='adyen_payment_api_url',
            endpoint='/capture',
            payload=data,
            method='POST'
        )

        # Handle the payment request response
        _logger.info("capture request response:\n%s", pprint.pformat(response_content))
        # the PSP reference associated with this /capture request is different from the
        # psp reference associated with the original payment request
        if response_content['pspReference']:
            self.adyen_capture_reference = response_content['pspReference']
        else:
            self._set_error(
                "Adyen: " + _("Received data with invalid capture reference")
            )
        if response_content['response']:
            if response_content['response'] == '[capture-received]':
                self._set_done()
            else:
                self._set_error(
                    "Adyen: " + _("Received data with invalid capture response: %s", response_content["response"])
                )
        else:
            self._set_error(
                    "Adyen: " + _("Received data without capture response")
                )

    def _send_void_request(self):
        """ Override of payment to send a void request to Adyen.

        Note: self.ensure_one()

        :return: None
        """
        super()._send_void_request()
        if self.provider != 'adyen':
            return

        data = {
            'merchantAccount': self.acquirer_id.adyen_merchant_account,
            'originalReference': self.acquirer_reference,
            'reference': self.reference,
        }
        response_content = self.acquirer_id._adyen_make_request(
            url_field_name='adyen_payment_api_url',
            endpoint='/cancel',
            payload=data,
            method='POST'
        )

        # Handle the payment request response
        _logger.info("cancel request response:\n%s", pprint.pformat(response_content))
        # the PSP reference associated with this /cancel request is different from the
        # psp reference associated with the original payment request
        if response_content['pspReference']:
            self.adyen_cancel_reference = response_content['pspReference']
        else:
            self._set_error(
                "Adyen: " + _("Received data with invalid cancel reference")
            )
        if response_content['response']:
            if response_content['response'] == '[cancel-received]':
                self._set_canceled()
            else:
                self._set_error(
                    "Adyen: " + _("Received data with invalid cancel response: %s", response_content["response"])
                )
        else:
            self._set_error(
                    "Adyen: " + _("Received data without cancel response")
                )
