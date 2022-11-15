# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment_adyen import utils as adyen_utils
from odoo.addons.payment_adyen.const import CURRENCY_DECIMALS, RESULT_CODES_MAPPING

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

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

        # Make the payment request to Adyen
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
                'recurringDetailReference': self.token_id.acquirer_ref,
            },
            'shopperReference': self.token_id.adyen_shopper_reference,
            'recurringProcessingModel': 'Subscription',
            'shopperIP': payment_utils.get_customer_ip_address(),
            'shopperInteraction': 'ContAuth',
            'shopperEmail': self.partner_email,
            'shopperName': adyen_utils.format_partner_name(self.partner_name),
            'telephoneNumber': self.partner_phone,
            **adyen_utils.include_partner_addresses(self),
        }
        response_content = self.acquirer_id._adyen_make_request(
            url_field_name='adyen_checkout_api_url',
            endpoint='/payments',
            payload=data,
            method='POST'
        )

        # Handle the payment request response
        _logger.info("payment request response:\n%s", pprint.pformat(response_content))
        self._handle_feedback_data('adyen', response_content)

    def _send_refund_request(self, amount_to_refund=None, create_refund_transaction=True):
        """ Override of payment to send a refund request to Adyen.

        Note: self.ensure_one()

        :param float amount_to_refund: The amount to refund
        :param bool create_refund_transaction: Whether a refund transaction should be created or not
        :return: The refund transaction if any
        :rtype: recordset of `payment.transaction`
        """
        if self.provider != 'adyen':
            return super()._send_refund_request(
                amount_to_refund=amount_to_refund,
                create_refund_transaction=create_refund_transaction
            )
        refund_tx = super()._send_refund_request(
            amount_to_refund=amount_to_refund, create_refund_transaction=True
        )

        # Make the refund request to Adyen
        converted_amount = payment_utils.to_minor_currency_units(
            -refund_tx.amount,  # The amount is negative for refund transactions
            refund_tx.currency_id,
            arbitrary_decimal_number=CURRENCY_DECIMALS.get(refund_tx.currency_id.name)
        )
        data = {
            'merchantAccount': self.acquirer_id.adyen_merchant_account,
            'amount': {
                'value': converted_amount,
                'currency': refund_tx.currency_id.name,
            },
            'reference': refund_tx.reference,
        }
        response_content = refund_tx.acquirer_id._adyen_make_request(
            url_field_name='adyen_checkout_api_url',
            endpoint='/payments/{}/refunds',
            endpoint_param=self.acquirer_reference,
            payload=data,
            method='POST'
        )
        _logger.info("refund request response:\n%s", pprint.pformat(response_content))

        # Handle the refund request response
        psp_reference = response_content.get('pspReference')
        status = response_content.get('status')
        if psp_reference and status == 'received':
            # The PSP reference associated with this /refunds request is different from the psp
            # reference associated with the original payment request.
            refund_tx.acquirer_reference = psp_reference

        return refund_tx

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
        event_code = data.get('eventCode')

        tx = self.search([('reference', '=', reference), ('provider', '=', 'adyen')])
        if event_code == 'REFUND' and (not tx or tx.operation != 'refund'):
            # If a refund is initiated from Adyen, the merchant reference can be personalized. We
            # need to get the source transaction and manually create the refund transaction.
            source_acquirer_reference = data.get('originalReference')
            source_tx = self.search(
                [('acquirer_reference', '=', source_acquirer_reference), ('provider', '=', 'adyen')]
            )
            if source_tx:
                # Manually create a refund transaction with a new reference. The reference of
                # the refund transaction was personalized from Adyen and could be identical to
                # that of an existing transaction.
                tx = self._adyen_create_refund_tx_from_feedback_data(source_tx, data)
            else:  # The refund was initiated for an unknown source transaction
                pass  # Don't do anything with the refund notification

        if not tx:
            raise ValidationError(
                "Adyen: " + _("No transaction found matching reference %s.", reference)
            )
        return tx

    def _adyen_create_refund_tx_from_feedback_data(self, source_tx, data):
        """ Create a refund transaction based on Adyen data.

        :param recordset source_tx: The source transaction for which a refund is initiated, as a
                                    `payment.transaction` recordset
        :param dict data: The feedback data sent by the provider
        :return: The created refund transaction
        :rtype: recordset of `payment.transaction`
        :raise: ValidationError if inconsistent data were received
        """
        refund_acquirer_reference = data.get('pspReference')
        amount_to_refund = data.get('amount', {}).get('value')
        if not refund_acquirer_reference or not amount_to_refund:
            raise ValidationError(
                "Adyen: " + _("Received refund data with missing transaction values")
            )

        converted_amount = payment_utils.to_major_currency_units(
            amount_to_refund, source_tx.currency_id
        )
        return source_tx._create_refund_transaction(
            amount_to_refund=converted_amount, acquirer_reference=refund_acquirer_reference
        )

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
        refusal_reason = data.get('refusalReason') or data.get('reason')
        if not payment_state:
            raise ValidationError("Adyen: " + _("Received data with missing payment state."))

        if payment_state in RESULT_CODES_MAPPING['pending']:
            self._set_pending()
        elif payment_state in RESULT_CODES_MAPPING['done']:
            has_token_data = 'recurring.recurringDetailReference' in data.get('additionalData', {})
            if self.tokenize and has_token_data:
                self._adyen_tokenize_from_feedback_data(data)
            self._set_done()
            if self.operation == 'refund':
                self.env.ref('payment.cron_post_process_payment_tx')._trigger()
        elif payment_state in RESULT_CODES_MAPPING['cancel']:
            _logger.warning("The transaction with reference %s was cancelled (reason: %s)",
                            self.reference, refusal_reason)
            self._set_canceled()
        elif payment_state in RESULT_CODES_MAPPING['error']:
            _logger.warning("An error occurred on transaction with reference %s (reason: %s)",
                            self.reference, refusal_reason)
            self._set_error(
                _("An error occurred during the processing of your payment. Please try again.")
            )
        elif payment_state in RESULT_CODES_MAPPING['refused']:
            _logger.warning("The transaction with reference %s was refused (reason: %s)",
                            self.reference, refusal_reason)
            self._set_error(_("Your payment was refused. Please try again."))
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
