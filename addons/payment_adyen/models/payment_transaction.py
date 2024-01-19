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
        :return: The dict of provider-specific processing values
        :rtype: dict
        """
        res = super()._get_specific_processing_values(processing_values)
        if self.provider_code != 'adyen':
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
        if self.provider_code != 'adyen':
            return

        # Prepare the payment request to Adyen
        if not self.token_id:
            raise UserError("Adyen: " + _("The transaction is not linked to a token."))

        converted_amount = payment_utils.to_minor_currency_units(
            self.amount, self.currency_id, CURRENCY_DECIMALS.get(self.currency_id.name)
        )
        data = {
            'merchantAccount': self.provider_id.adyen_merchant_account,
            'amount': {
                'value': converted_amount,
                'currency': self.currency_id.name,
            },
            'reference': self.reference,
            'paymentMethod': {
                'recurringDetailReference': self.token_id.provider_ref,
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

        # Force the capture delay on Adyen side if the provider is not configured for capturing
        # payments manually. This is necessary because it's not possible to distinguish
        # 'AUTHORISATION' events sent by Adyen with the merchant account's capture delay set to
        # 'manual' from events with the capture delay set to 'immediate' or a number of hours. If
        # the merchant account is configured to capture payments with a delay but the provider is
        # not, we force the immediate capture to avoid considering authorized transactions as
        # captured on Odoo.
        if not self.provider_id.capture_manually:
            data.update(captureDelayHours=0)

        # Make the payment request to Adyen
        response_content = self.provider_id._adyen_make_request(
            url_field_name='adyen_checkout_api_url',
            endpoint='/payments',
            payload=data,
            method='POST',
            idempotency_key=payment_utils.generate_idempotency_key(
                self, scope='payment_request_token'
            )
        )

        # Handle the payment request response
        _logger.info(
            "payment request response for transaction with reference %s:\n%s",
            self.reference, pprint.pformat(response_content)
        )
        self._handle_notification_data('adyen', response_content)

    def _send_refund_request(self, amount_to_refund=None):
        """ Override of payment to send a refund request to Adyen.

        Note: self.ensure_one()

        :param float amount_to_refund: The amount to refund
        :return: The refund transaction created to process the refund request.
        :rtype: recordset of `payment.transaction`
        """
        refund_tx = super()._send_refund_request(amount_to_refund=amount_to_refund)
        if self.provider_code != 'adyen':
            return refund_tx

        # Make the refund request to Adyen
        converted_amount = payment_utils.to_minor_currency_units(
            -refund_tx.amount,  # The amount is negative for refund transactions
            refund_tx.currency_id,
            arbitrary_decimal_number=CURRENCY_DECIMALS.get(refund_tx.currency_id.name)
        )
        data = {
            'merchantAccount': self.provider_id.adyen_merchant_account,
            'amount': {
                'value': converted_amount,
                'currency': refund_tx.currency_id.name,
            },
            'reference': refund_tx.reference,
        }
        response_content = refund_tx.provider_id._adyen_make_request(
            url_field_name='adyen_checkout_api_url',
            endpoint='/payments/{}/refunds',
            endpoint_param=self.provider_reference,
            payload=data,
            method='POST'
        )
        _logger.info(
            "refund request response for transaction with reference %s:\n%s",
            self.reference, pprint.pformat(response_content)
        )

        # Handle the refund request response
        psp_reference = response_content.get('pspReference')
        status = response_content.get('status')
        if psp_reference and status == 'received':
            # The PSP reference associated with this /refunds request is different from the psp
            # reference associated with the original payment request.
            refund_tx.provider_reference = psp_reference

        return refund_tx

    def _send_capture_request(self):
        """ Override of payment to send a capture request to Adyen.

        Note: self.ensure_one()

        :return: None
        """
        super()._send_capture_request()
        if self.provider_code != 'adyen':
            return

        converted_amount = payment_utils.to_minor_currency_units(
            self.amount, self.currency_id, CURRENCY_DECIMALS.get(self.currency_id.name)
        )
        data = {
            'merchantAccount': self.provider_id.adyen_merchant_account,
            'amount': {
                'value': converted_amount,
                'currency': self.currency_id.name,
            },
            'reference': self.reference,
        }
        response_content = self.provider_id._adyen_make_request(
            url_field_name='adyen_checkout_api_url',
            endpoint='/payments/{}/captures',
            endpoint_param=self.provider_reference,
            payload=data,
            method='POST',
        )
        _logger.info("capture request response:\n%s", pprint.pformat(response_content))

        # Handle the capture request response
        status = response_content.get('status')
        if status == 'received':
            self._log_message_on_linked_documents(_(
                "The capture of the transaction with reference %s has been requested (%s).",
                self.reference, self.provider_id.name
            ))

    def _send_void_request(self):
        """ Override of payment to send a void request to Adyen.

        Note: self.ensure_one()

        :return: None
        """
        super()._send_void_request()
        if self.provider_code != 'adyen':
            return

        data = {
            'merchantAccount': self.provider_id.adyen_merchant_account,
            'reference': self.reference,
        }
        response_content = self.provider_id._adyen_make_request(
            url_field_name='adyen_checkout_api_url',
            endpoint='/payments/{}/cancels',
            endpoint_param=self.provider_reference,
            payload=data,
            method='POST',
        )
        _logger.info("void request response:\n%s", pprint.pformat(response_content))

        # Handle the void request response
        status = response_content.get('status')
        if status == 'received':
            self._log_message_on_linked_documents(_(
                "A request was sent to void the transaction with reference %s (%s).",
                self.reference, self.provider_id.name
            ))

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """ Override of payment to find the transaction based on Adyen data.

        :param str provider_code: The code of the provider that handled the transaction
        :param dict notification_data: The notification data sent by the provider
        :return: The transaction if found
        :rtype: recordset of `payment.transaction`
        :raise: ValidationError if inconsistent data were received
        :raise: ValidationError if the data match no transaction
        """
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'adyen' or len(tx) == 1:
            return tx

        reference = notification_data.get('merchantReference')
        if not reference:
            raise ValidationError("Adyen: " + _("Received data with missing merchant reference"))

        event_code = notification_data.get('eventCode', 'AUTHORISATION')  # Fallback on auth if S2S.
        provider_reference = notification_data.get('pspReference')
        source_reference = notification_data.get('originalReference')
        if event_code == 'AUTHORISATION':
            tx = self.search([('reference', '=', reference), ('provider_code', '=', 'adyen')])
        elif event_code in ['CAPTURE', 'CANCELLATION']:
            # The capture/void may be initiated from Adyen, so we can't trust the reference.
            # We find the transaction based on the original provider reference since Adyen will have
            # two different references: one for the original transaction and one for the capture.
            tx = self.search(
                [('provider_reference', '=', source_reference), ('provider_code', '=', 'adyen')]
            )
        else:  # 'REFUND'
            # The refund may be initiated from Adyen, so we can't trust the reference, which could
            # be identical to another existing transaction. We find the transaction based on the
            # provider reference.
            tx = self.search(
                [('provider_reference', '=', provider_reference), ('provider_code', '=', 'adyen')]
            )
            if not tx:  # The refund was initiated from Adyen
                # Find the source transaction based on the original reference
                source_tx = self.search(
                    [('provider_reference', '=', source_reference), ('provider_code', '=', 'adyen')]
                )
                if source_tx:
                    # Manually create a refund transaction with a new reference. The reference of
                    # the refund transaction was personalized from Adyen and could be identical to
                    # that of an existing transaction.
                    tx = self._adyen_create_refund_tx_from_notification_data(
                        source_tx, notification_data
                    )
                else:  # The refund was initiated for an unknown source transaction
                    pass  # Don't do anything with the refund notification

        if not tx:
            raise ValidationError(
                "Adyen: " + _("No transaction found matching reference %s.", reference)
            )
        return tx

    def _adyen_create_refund_tx_from_notification_data(self, source_tx, notification_data):
        """ Create a refund transaction based on Adyen data.

        :param recordset source_tx: The source transaction for which a refund is initiated, as a
                                    `payment.transaction` recordset
        :param dict notification_data: The notification data sent by the provider
        :return: The newly created refund transaction
        :rtype: recordset of `payment.transaction`
        :raise: ValidationError if inconsistent data were received
        """
        refund_provider_reference = notification_data.get('pspReference')
        amount_to_refund = notification_data.get('amount', {}).get('value')
        if not refund_provider_reference or not amount_to_refund:
            raise ValidationError(
                "Adyen: " + _("Received refund data with missing transaction values")
            )

        converted_amount = payment_utils.to_major_currency_units(
            amount_to_refund, source_tx.currency_id
        )
        return source_tx._create_refund_transaction(
            amount_to_refund=converted_amount, provider_reference=refund_provider_reference
        )

    def _process_notification_data(self, notification_data):
        """ Override of payment to process the transaction based on Adyen data.

        Note: self.ensure_one()

        :param dict notification_data: The notification data sent by the provider
        :return: None
        :raise: ValidationError if inconsistent data were received
        """
        super()._process_notification_data(notification_data)
        if self.provider_code != 'adyen':
            return

        # Extract or assume the event code. If none is provided, the feedback data originate from a
        # direct payment request whose feedback data share the same payload as an 'AUTHORISATION'
        # webhook notification.
        event_code = notification_data.get('eventCode', 'AUTHORISATION')

        # Handle the provider reference. If the event code is 'CAPTURE' or 'CANCELLATION', we
        # discard the pspReference as it is different from the original pspReference of the tx.
        if 'pspReference' in notification_data and event_code in ['AUTHORISATION', 'REFUND']:
            self.provider_reference = notification_data.get('pspReference')

        # Handle the payment state
        payment_state = notification_data.get('resultCode')
        refusal_reason = notification_data.get('refusalReason') or notification_data.get('reason')
        if not payment_state:
            raise ValidationError("Adyen: " + _("Received data with missing payment state."))

        if payment_state in RESULT_CODES_MAPPING['pending']:
            self._set_pending()
        elif payment_state in RESULT_CODES_MAPPING['done']:
            additional_data = notification_data.get('additionalData', {})
            has_token_data = 'recurring.recurringDetailReference' in additional_data
            if self.tokenize and has_token_data:
                self._adyen_tokenize_from_notification_data(notification_data)

            if not self.provider_id.capture_manually:
                self._set_done()
            else:  # The payment was configured for manual capture.
                # Differentiate the state based on the event code.
                if event_code == 'AUTHORISATION':
                    self._set_authorized()
                else:  # 'CAPTURE'
                    self._set_done()

            # Immediately post-process the transaction if it is a refund, as the post-processing
            # will not be triggered by a customer browsing the transaction from the portal.
            if self.operation == 'refund':
                self.env.ref('payment.cron_post_process_payment_tx')._trigger()
        elif payment_state in RESULT_CODES_MAPPING['cancel']:
            self._set_canceled()
        elif payment_state in RESULT_CODES_MAPPING['error']:
            if event_code in ['AUTHORISATION', 'REFUND']:
                _logger.warning(
                    "the transaction with reference %s underwent an error. reason: %s",
                    self.reference, refusal_reason
                )
                self._set_error(
                    _("An error occurred during the processing of your payment. Please try again.")
                )
            elif event_code == 'CANCELLATION':
                _logger.warning(
                    "the void of the transaction with reference %s failed. reason: %s",
                    self.reference, refusal_reason
                )
                self._log_message_on_linked_documents(
                    _("The void of the transaction with reference %s failed.", self.reference)
                )
            else:  # 'CAPTURE'
                _logger.warning(
                    "the capture of the transaction with reference %s failed. reason: %s",
                    self.reference, refusal_reason
                )
                self._log_message_on_linked_documents(
                    _("The capture of the transaction with reference %s failed.", self.reference)
                )
        elif payment_state in RESULT_CODES_MAPPING['refused']:
            _logger.warning(
                "the transaction with reference %s was refused. reason: %s",
                self.reference, refusal_reason
            )
            self._set_error(_("Your payment was refused. Please try again."))
        else:  # Classify unsupported payment state as `error` tx state
            _logger.warning(
                "received data for transaction with reference %s with invalid payment state: %s",
                self.reference, payment_state
            )
            self._set_error(
                "Adyen: " + _("Received data with invalid payment state: %s", payment_state)
            )

    def _adyen_tokenize_from_notification_data(self, notification_data):
        """ Create a new token based on the notification data.

        Note: self.ensure_one()

        :param dict notification_data: The notification data sent by the provider
        :return: None
        """
        self.ensure_one()

        additional_data = notification_data['additionalData']
        token = self.env['payment.token'].create({
            'provider_id': self.provider_id.id,
            'payment_details': additional_data.get('cardSummary'),
            'partner_id': self.partner_id.id,
            'provider_ref': additional_data['recurring.recurringDetailReference'],
            'adyen_shopper_reference': additional_data['recurring.shopperReference'],
            'verified': True,  # The payment is authorized, so the payment method is valid
        })
        self.write({
            'token_id': token,
            'tokenize': False,
        })
        _logger.info(
            "created token with id %(token_id)s for partner with id %(partner_id)s from "
            "transaction with reference %(ref)s",
            {
                'token_id': token.id,
                'partner_id': self.partner_id.id,
                'ref': self.reference,
            },
        )
