# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, models
from odoo.tools import format_amount

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_adyen import const
from odoo.addons.payment_adyen import utils as adyen_utils


_logger = get_payment_logger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    # === BUSINESS METHODS - PRE-PROCESSING === #

    def _get_specific_processing_values(self, processing_values):
        """ Override of payment to return Adyen-specific processing values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic processing values of the transaction
        :return: The dict of provider-specific processing values
        :rtype: dict
        """
        if self.provider_code != 'adyen':
            return super()._get_specific_processing_values(processing_values)

        converted_amount = payment_utils.to_minor_currency_units(
            self.amount, self.currency_id, const.CURRENCY_DECIMALS.get(self.currency_id.name)
        )
        return {
            'converted_amount': converted_amount,
            'access_token': payment_utils.generate_access_token(
                processing_values['reference'],
                converted_amount,
                self.currency_id.id,
                processing_values['partner_id']
            )
        }

    def _send_payment_request(self):
        """Override of `payment` to send a payment request to Adyen."""
        if self.provider_code != 'adyen':
            return super()._send_payment_request()

        # Prepare the payment request to Adyen.
        converted_amount = payment_utils.to_minor_currency_units(
            self.amount, self.currency_id, const.CURRENCY_DECIMALS.get(self.currency_id.name)
        )
        partner_country_code = (
            self.partner_country_id.code or self.provider_id.company_id.country_id.code or 'NL'
        )
        data = {
            'merchantAccount': self.provider_id.adyen_merchant_account,
            'amount': {
                'value': converted_amount,
                'currency': self.currency_id.name,
            },
            'countryCode': partner_country_code,
            'reference': self.reference,
            'paymentMethod': {
                'storedPaymentMethodId': self.token_id.provider_ref,
            },
            'shopperReference': self.token_id.adyen_shopper_reference,
            'recurringProcessingModel': 'Subscription',
            'shopperIP': payment_utils.get_customer_ip_address(),
            'shopperInteraction': 'ContAuth',
            'shopperEmail': self.partner_email,
            'shopperName': adyen_utils.format_partner_name(self.partner_name),
            'telephoneNumber': self.partner_phone,
            **adyen_utils.include_partner_addresses(self),
            'lineItems': [{
                'amountIncludingTax': converted_amount,
                'quantity': '1',
                'description': self.reference,
            }],
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

        # Send the payment request to Adyen.
        response_content = self._send_api_request(
            'POST',
            '/payments',
            json=data,
            idempotency_key=payment_utils.generate_idempotency_key(
                self, scope='payment_request_token'
            )
        )
        self._process('adyen', response_content)

    def _send_capture_request(self):
        """Override of `payment` to send a capture request to Adyen."""
        if self.provider_code != 'adyen':
            return super()._send_capture_request()

        # Send the capture request to Adyen.
        converted_amount = payment_utils.to_minor_currency_units(
            self.amount, self.currency_id, const.CURRENCY_DECIMALS.get(self.currency_id.name)
        )
        data = {
            'merchantAccount': self.provider_id.adyen_merchant_account,
            'amount': {
                'value': converted_amount,
                'currency': self.currency_id.name,
            },
            'reference': self.reference,
        }

        response_content = self._send_api_request(
            'POST',
            '/payments/{}/captures',
            json=data,
            endpoint_param=self.provider_reference,
        )

        # Process the capture request response.
        status = response_content.get('status')
        formatted_amount = format_amount(self.env, self.amount, self.currency_id)
        if status == 'received':
            self._log_message_on_linked_documents(_(
                "The capture request of %(amount)s for transaction %(ref)s has been sent.",
                amount=formatted_amount, ref=self.reference
            ))

        # The PSP reference associated with this capture request is different from the PSP
        # reference associated with the original payment request.
        self.provider_reference = response_content.get('pspReference')

    def _send_void_request(self):
        """Override of `payment` to send a void request to Adyen."""
        if self.provider_code != 'adyen':
            return super()._send_void_request()

        data = {
            'merchantAccount': self.provider_id.adyen_merchant_account,
            'reference': self.reference,
        }
        response_content = self._send_api_request(
            'POST',
            '/payments/{}/cancels',
            json=data,
            endpoint_param=self.provider_reference,
        )

        # Process the void request response.
        status = response_content.get('status')
        if status == 'received':
            self._log_message_on_linked_documents(_(
                "A request was sent to void the transaction %(reference)s.",
                reference=self.reference
            ))

        # The PSP reference associated with this void request is different from the PSP
        # reference associated with the original payment request.
        self.provider_reference = response_content.get('pspReference')

    def _send_refund_request(self):
        """Override of `payment` to send a refund request to Adyen."""
        if self.provider_code != 'adyen':
            return super()._send_refund_request()

        # Send the refund request to Adyen.
        converted_amount = payment_utils.to_minor_currency_units(
            -self.amount,  # The amount is negative for refund transactions
            self.currency_id,
            arbitrary_decimal_number=const.CURRENCY_DECIMALS.get(self.currency_id.name)
        )
        data = {
            'merchantAccount': self.provider_id.adyen_merchant_account,
            'amount': {
                'value': converted_amount,
                'currency': self.currency_id.name,
            },
            'reference': self.reference,
        }
        response_content = self._send_api_request(
            'POST',
            '/payments/{}/refunds',
            json=data,
            endpoint_param=self.source_transaction_id.provider_reference,
        )

        # Process the refund request response.
        psp_reference = response_content.get('pspReference')
        status = response_content.get('status')
        if psp_reference and status == 'received':
            # The PSP reference associated with this /refunds request is different from the psp
            # reference associated with the original payment request.
            self.provider_reference = psp_reference

    # === BUSINESS METHODS - PROCESSING === #

    @api.model
    def _search_by_reference(self, provider_code, payment_data):
        """Override of `payment` to search the transaction  with a specific logic for Adyen."""
        if provider_code != 'adyen':
            return super()._search_by_reference(provider_code, payment_data)

        tx = self
        reference = payment_data.get('merchantReference')
        if not reference:
            _logger.warning("Received data with missing reference.")
            return tx

        event_code = payment_data.get('eventCode', 'AUTHORISATION')  # Fallback on auth if S2S.
        provider_reference = payment_data.get('pspReference')
        source_reference = payment_data.get('originalReference')
        if event_code == 'AUTHORISATION':
            tx = self.search([('reference', '=', reference), ('provider_code', '=', 'adyen')])
        elif event_code in ['CANCELLATION', 'CAPTURE', 'CAPTURE_FAILED']:
            # The capture/void may be initiated from Adyen, so we can't trust the reference.
            # We find the transaction based on the original provider reference since Adyen will have
            # two different references: one for the original transaction and one for the capture or
            # void. We keep the second one only for child transactions. For full capture/void, no
            # child transaction are created. Thus, we first look for the source transaction before
            # checking if we need to find/create a child transaction.
            source_tx = self.search(
                [('provider_reference', '=', source_reference), ('provider_code', '=', 'adyen')]
            )
            if source_tx:
                payment_data_amount = payment_data.get('amount', {}).get('value')
                converted_notification_amount = payment_utils.to_major_currency_units(
                    payment_data_amount,
                    source_tx.currency_id,
                    arbitrary_decimal_number=const.CURRENCY_DECIMALS.get(self.currency_id.name),
                )
                if source_tx.amount == converted_notification_amount:  # Full capture/void.
                    tx = source_tx
                else:  # Partial capture/void; we search for the child transaction instead.
                    tx = self.search([
                        ('provider_reference', '=', provider_reference),
                        ('provider_code', '=', 'adyen'),
                    ])
                    if tx and tx.amount != converted_notification_amount:
                        # If the void was requested expecting a certain amount but, in the meantime,
                        # others captures that Odoo was unaware of were done, the amount voided will
                        # be different from the amount of the existing transaction.
                        tx._set_error(_(
                            "The amount processed by Adyen for the transaction %s is different than"
                            " the one requested. Another transaction is created with the correct"
                            " amount.", tx.reference
                        ))
                        tx = self.env['payment.transaction']
                    if not tx:  # Partial capture/void initiated from Adyen or with a wrong amount.
                        # Manually create a child transaction with a new reference. The reference of
                        # the child transaction was personalized from Adyen and could be identical
                        # to that of an existing transaction.
                        tx = self._adyen_create_child_tx(source_tx, payment_data)
            else:  # The capture/void was initiated for an unknown source transaction
                pass  # Don't do anything with the capture/void notification
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
                    tx = self._adyen_create_child_tx(source_tx, payment_data, is_refund=True)
                else:  # The refund was initiated for an unknown source transaction
                    pass  # Don't do anything with the refund notification
        if not tx:
            _logger.warning("No transaction found matching reference %s.", reference)
        return tx

    def _adyen_create_child_tx(self, source_tx, payment_data, is_refund=False):
        """Create a child transaction based on Adyen data.

        :param payment.transaction source_tx: The source transaction for which a new operation is
                                              initiated.
        :param dict payment_data: The payment data sent by the provider.
        :return: The newly created child transaction.
        :rtype: payment.transaction
        """
        provider_reference = payment_data.get('pspReference')
        amount = payment_data.get('amount', {}).get('value')
        if not provider_reference or amount is None:  # amount == 0 if success == False
            _logger.warning("Received data for child transaction with missing transaction values.")
            return self.env['payment.transaction']

        converted_amount = payment_utils.to_major_currency_units(
            amount,
            source_tx.currency_id,
            arbitrary_decimal_number=const.CURRENCY_DECIMALS.get(self.currency_id.name),
        )
        return source_tx._create_child_transaction(
            converted_amount, is_refund=is_refund, provider_reference=provider_reference
        )

    def _extract_amount_data(self, payment_data):
        """Override of `payment` to extract the amount and currency from the payment data."""
        if self.provider_code != 'adyen':
            return super()._extract_amount_data(payment_data)

        # Redirection payments don't have the amount or currency in their payment_data, but
        # processing them results in a pending transaction anyway.
        if payment_data.get('action', {}).get('type') == 'redirect':
            return None  # Skip the validation

        amount_data = payment_data.get('amount', {})
        amount = payment_utils.to_major_currency_units(
            amount_data.get('value', 0),
            self.currency_id,
            arbitrary_decimal_number=const.CURRENCY_DECIMALS.get(self.currency_id.name),
        )
        currency_code = amount_data.get('currency')
        return {
            'amount': amount,
            'currency_code': currency_code,
        }

    def _apply_updates(self, payment_data):
        """Override of payment to update the transaction based on the payment data."""
        if self.provider_code != 'adyen':
            return super()._apply_updates(payment_data)

        # Extract or assume the event code. If none is provided, the feedback data originate from a
        # direct payment request whose feedback data share the same payload as an 'AUTHORISATION'
        # webhook notification.
        event_code = payment_data.get('eventCode', 'AUTHORISATION')

        # Update the provider reference. If the event code is 'CAPTURE' or 'CANCELLATION', we
        # discard the pspReference as it is different from the original pspReference of the tx.
        if 'pspReference' in payment_data and event_code in ['AUTHORISATION', 'REFUND']:
            self.provider_reference = payment_data.get('pspReference')

        # Update the payment method.
        payment_method_data = payment_data.get('paymentMethod', '')
        if isinstance(payment_method_data, dict):  # Not from webhook: the data contain the PM code.
            payment_method_type = payment_method_data['type']
            if payment_method_type == 'scheme':  # card
                payment_method_code = payment_method_data['brand']
            else:
                payment_method_code = payment_method_type
        else:  # Sent from the webhook: the PM code is directly received as a string.
            payment_method_code = payment_method_data

        payment_method = self.env['payment.method']._get_from_code(
            payment_method_code, mapping=const.PAYMENT_METHODS_MAPPING
        )
        self.payment_method_id = payment_method or self.payment_method_id

        # Update the payment state.
        payment_state = payment_data.get('resultCode')
        refusal_reason = payment_data.get('refusalReason') or payment_data.get('reason')
        if not payment_state:
            self._set_error(_("Received data with missing payment state."))
        elif payment_state in const.RESULT_CODES_MAPPING['pending']:
            self._set_pending()
        elif payment_state in const.RESULT_CODES_MAPPING['done']:
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
        elif payment_state in const.RESULT_CODES_MAPPING['cancel']:
            self._set_canceled()
        elif payment_state in const.RESULT_CODES_MAPPING['error']:
            if event_code in ['AUTHORISATION', 'REFUND']:
                _logger.warning(
                    "The transaction %s underwent an error. reason: %s.",
                    self.reference, refusal_reason,
                )
                self._set_error(
                    _("An error occurred during the processing of your payment. Please try again.")
                )
            elif event_code == 'CANCELLATION':
                _logger.warning(
                    "The void of the transaction %s failed. reason: %s.",
                    self.reference, refusal_reason,
                )
                if self.source_transaction_id:  # child tx => The event can't be retried.
                    self._set_error(_("The void of the transaction %s failed.", self.reference))
                else:  # source tx with failed void stays in its state, could be voided again
                    self._log_message_on_linked_documents(
                        _("The void of the transaction %s failed.", self.reference)
                    )
            else:  # 'CAPTURE', 'CAPTURE_FAILED'
                _logger.warning(
                    "The capture of the transaction %s failed. reason: %s.",
                    self.reference, refusal_reason,
                )
                if self.source_transaction_id:  # child_tx => The event can't be retried.
                    self._set_error(_(
                        "The capture of the transaction %s failed.", self.reference
                    ))
                else:  # source tx with failed capture stays in its state, could be captured again
                    self._log_message_on_linked_documents(_(
                        "The capture of the transaction %s failed.", self.reference
                    ))
        elif payment_state in const.RESULT_CODES_MAPPING['refused']:
            _logger.warning(
                "the transaction %s was refused. reason: %s",
                self.reference, refusal_reason
            )
            self._set_error(_("Your payment was refused. Please try again."))
        else:  # Classify unsupported payment state as `error` tx state
            _logger.warning(
                "received data for transaction %s with invalid payment state: %s",
                self.reference, payment_state
            )
            self._set_error(
                "Adyen: " + _("Received data with invalid payment state: %s", payment_state)
            )

    def _extract_token_values(self, payment_data):
        """Override of `payment` to extract the token values from the payment data."""
        if self.provider_code != 'adyen':
            return super()._extract_token_values(payment_data)

        additional_data = payment_data['additionalData']

        if 'recurring.recurringDetailReference' not in additional_data:
            return {}

        return {
            'provider_ref': additional_data['recurring.recurringDetailReference'],
            'payment_details': additional_data.get('cardSummary'),
            'adyen_shopper_reference': additional_data['recurring.shopperReference'],
        }
