# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.urls import url_encode

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.urls import urljoin as url_join

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_stripe import const
from odoo.addons.payment_stripe import utils as stripe_utils
from odoo.addons.payment_stripe.controllers.main import StripeController


_logger = get_payment_logger(__name__, const.SENSITIVE_KEYS)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _get_specific_processing_values(self, processing_values):
        """ Override of payment to return Stripe-specific processing values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic processing values of the transaction
        :return: The dict of provider-specific processing values
        :rtype: dict
        """
        if self.provider_code != 'stripe' or self.operation == 'online_token':
            return super()._get_specific_processing_values(processing_values)

        intent = self._stripe_create_intent()
        base_url = self.provider_id.get_base_url()
        return {
            'client_secret': intent['client_secret'] if intent else '',
            'return_url': url_join(
                base_url,
                f'{StripeController._return_url}?{url_encode({"reference": self.reference})}',
            ),
        }

    def _send_payment_request(self):
        """Override of `payment` to send a payment request to Stripe."""
        if self.provider_code != 'stripe':
            return super()._send_payment_request()

        # Send the payment request to Stripe.
        payment_intent = self._stripe_create_intent()

        if not payment_intent:  # The PI might be missing if Stripe failed to create it.
            return  # There is nothing to process; the transaction is in error at this point.

        # Handle the payment request response
        payment_data = {'reference': self.reference}
        StripeController._include_payment_intent_in_payment_data(
            payment_intent, payment_data
        )
        self._process('stripe', payment_data)

    def _stripe_create_intent(self):
        """ Create and return a PaymentIntent or a SetupIntent object, depending on the operation.

        :return: The created PaymentIntent or SetupIntent object or None if creation failed.
        :rtype: dict|None
        """
        try:
            if self.operation == 'validation':
                response = self._send_api_request(
                    'POST', 'setup_intents', data=self._stripe_prepare_setup_intent_payload(),
                )
            else:  # 'online_direct', 'online_token', 'offline'.
                response = self._send_api_request(
                    'POST',
                    'payment_intents',
                    data=self._stripe_prepare_payment_intent_payload(),
                    offline=self.operation == 'offline',
                    idempotency_key=payment_utils.generate_idempotency_key(
                        self, scope='payment_intents'
                    ),
                )
        except ValidationError as error:
            self._set_error(str(error))
            intent = None
        else:
            intent = response

        return intent

    def _stripe_prepare_setup_intent_payload(self):
        """ Prepare the payload for the creation of a SetupIntent object in Stripe format.

        Note: This method serves as a hook for modules that would fully implement Stripe Connect.

        :return: The Stripe-formatted payload for the SetupIntent request.
        :rtype: dict
        """
        customer = self._stripe_create_customer()
        setup_intent_payload = {
            'customer': customer['id'],
            'description': self.reference,
            'payment_method_types[]': const.PAYMENT_METHODS_MAPPING.get(
                self.payment_method_code, self.payment_method_code
            ),
        }
        if self.currency_id.name in const.INDIAN_MANDATES_SUPPORTED_CURRENCIES:
            setup_intent_payload.update(**self._stripe_prepare_mandate_options())
        return setup_intent_payload

    def _stripe_prepare_payment_intent_payload(self):
        """ Prepare the payload for the creation of a PaymentIntent object in Stripe format.

        Note: This method serves as a hook for modules that would fully implement Stripe Connect.

        :return: The Stripe-formatted payload for the PaymentIntent request.
        :rtype: dict
        """
        ppm_code = self.payment_method_id.primary_payment_method_id.code
        payment_method_type = ppm_code or self.payment_method_code
        payment_intent_payload = {
            'amount': payment_utils.to_minor_currency_units(
                self.amount,
                self.currency_id,
                arbitrary_decimal_number=const.CURRENCY_DECIMALS.get(self.currency_id.name),
            ),
            'currency': self.currency_id.name.lower(),
            'description': self.reference,
            'capture_method': 'manual' if self.provider_id.capture_manually else 'automatic',
            'payment_method_types[]': const.PAYMENT_METHODS_MAPPING.get(
                payment_method_type, payment_method_type
            ),
            'expand[]': 'payment_method',
            **stripe_utils.include_shipping_address(self),
        }
        if self.operation in ['online_token', 'offline']:
            if not self.token_id.stripe_payment_method:  # Pre-SCA token, migrate it.
                self.token_id._stripe_sca_migrate_customer()

            payment_intent_payload.update({
                'confirm': True,
                'customer': self.token_id.provider_ref,
                'off_session': True,
                'payment_method': self.token_id.stripe_payment_method,
                'mandate': self.token_id.stripe_mandate or None,
            })
        else:
            customer = self._stripe_create_customer()
            payment_intent_payload['customer'] = customer['id']
            if self.tokenize:
                payment_intent_payload['setup_future_usage'] = 'off_session'
                if self.currency_id.name in const.INDIAN_MANDATES_SUPPORTED_CURRENCIES:
                    payment_intent_payload.update(**self._stripe_prepare_mandate_options())
        return payment_intent_payload

    def _stripe_create_customer(self):
        """ Create and return a Customer.

        :return: The Customer
        :rtype: dict
        """
        customer = self._send_api_request(
            'POST', 'customers', data={
                'address[city]': self.partner_city or None,
                'address[country]': self.partner_country_id.code or None,
                'address[line1]': self.partner_address or None,
                'address[postal_code]': self.partner_zip or None,
                'address[state]': self.partner_state_id.name or None,
                'description': f'Odoo Partner: {self.partner_id.name} (id: {self.partner_id.id})',
                'email': self.partner_email or None,
                'name': self.partner_name,
                'phone': self.partner_phone and self.partner_phone[:20] or None,
            }
        )
        return customer

    def _stripe_prepare_mandate_options(self):
        """ Prepare the configuration options for setting up an eMandate along with an intent.

        :return: The Stripe-formatted payload for the mandate options.
        :rtype: dict
        """
        mandate_values = self._get_mandate_values()

        OPTION_PATH_PREFIX = 'payment_method_options[card][mandate_options]'
        mandate_options = {
            f'{OPTION_PATH_PREFIX}[reference]': self.reference,
            f'{OPTION_PATH_PREFIX}[amount_type]': 'maximum',
            f'{OPTION_PATH_PREFIX}[amount]': payment_utils.to_minor_currency_units(
                mandate_values.get('amount', 15000),
                self.currency_id,
                arbitrary_decimal_number=const.CURRENCY_DECIMALS.get(self.currency_id.name),
            ),  # Use the specified amount, if any, or define the maximum amount of 15.000 INR.
            f'{OPTION_PATH_PREFIX}[start_date]': int(round(
                (mandate_values.get('start_datetime') or fields.Datetime.now()).timestamp()
            )),
            f'{OPTION_PATH_PREFIX}[interval]': 'sporadic',
            f'{OPTION_PATH_PREFIX}[supported_types][]': 'india',
        }
        if mandate_values.get('end_datetime'):
            mandate_options[f'{OPTION_PATH_PREFIX}[end_date]'] = int(round(
                mandate_values['end_datetime'].timestamp()
            ))
        if mandate_values.get('recurrence_unit') and mandate_values.get('recurrence_duration'):
            mandate_options.update({
                f'{OPTION_PATH_PREFIX}[interval]': mandate_values['recurrence_unit'],
                f'{OPTION_PATH_PREFIX}[interval_count]': mandate_values['recurrence_duration'],
            })
        if self.operation == 'validation':
            currency_name = self.provider_id.with_context(
                validation_pm=self.payment_method_id  # Will be converted to a kwarg in master.
            )._get_validation_currency().name.lower()
            mandate_options[f'{OPTION_PATH_PREFIX}[currency]'] = currency_name

        return mandate_options

    def _send_refund_request(self):
        """Override of `payment` to send a refund request to Stripe."""
        if self.provider_code != 'stripe':
            return super()._send_refund_request()

        # Send the refund request to Stripe.
        data = self._send_api_request(
            'POST', 'refunds', data={
                'payment_intent': self.source_transaction_id.provider_reference,
                'amount': payment_utils.to_minor_currency_units(
                    -self.amount,  # Refund transactions' amount is negative, inverse it.
                    self.currency_id,
                    arbitrary_decimal_number=const.CURRENCY_DECIMALS.get(self.currency_id.name),
                ),
            }
        )

        # Process the refund request response.
        payment_data = {}
        StripeController._include_refund_in_payment_data(data, payment_data)
        self._process('stripe', payment_data)

    def _send_capture_request(self):
        """Override of `payment` to send a capture request to Stripe."""
        if self.provider_code != 'stripe':
            return super()._send_capture_request()

        # Make the capture request to Stripe
        payment_intent = self._send_api_request(
            'POST', f'payment_intents/{self.source_transaction_id.provider_reference}/capture'
        )

        # Process the capture request response.
        payment_data = {'reference': self.reference}
        StripeController._include_payment_intent_in_payment_data(
            payment_intent, payment_data
        )
        self._process('stripe', payment_data)

    def _send_void_request(self):
        """Override of `payment` to send a void request to Stripe."""
        if self.provider_code != 'stripe':
            return super()._send_void_request()

        # Make the void request to Stripe
        payment_intent = self._send_api_request(
            'POST', f'payment_intents/{self.source_transaction_id.provider_reference}/cancel'
        )

        # Process the void request response.
        payment_data = {'reference': self.reference}
        StripeController._include_payment_intent_in_payment_data(
            payment_intent, payment_data
        )
        self._process('stripe', payment_data)

    @api.model
    def _search_by_reference(self, provider_code, payment_data):
        """ Override of payment to find the transaction based on Stripe data.

        :param str provider_code: The code of the provider that handled the transaction
        :param dict payment_data: The payment data sent by the provider
        :return: The transaction if found
        :rtype: payment.transaction
        """
        if provider_code != 'stripe':
            return super()._search_by_reference(provider_code, payment_data)

        reference = payment_data.get('reference')
        if reference:
            tx = self.search([('reference', '=', reference), ('provider_code', '=', 'stripe')])
        elif payment_data.get('event_type') == 'charge.refund.updated':
            # The webhook notifications sent for `charge.refund.updated` events only contain a
            # refund object that has no 'description' (the merchant reference) field. We thus search
            # the transaction by its provider reference which is the refund id for refund txs.
            refund_id = payment_data['object_id']  # The object is a refund.
            tx = self.search(
                [('provider_reference', '=', refund_id), ('provider_code', '=', 'stripe')]
            )
        else:
            _logger.warning("Received data with missing merchant reference")
            tx = self

        if not tx:
            _logger.warning("No transaction found matching reference %s.", reference)

        return tx

    def _extract_amount_data(self, payment_data):
        """Override of payment to extract the amount and currency from the payment data."""
        if self.provider_code != 'stripe':
            return super()._extract_amount_data(payment_data)

        if self.operation == 'refund':
            payment_data = payment_data['refund']
        else:  # 'online_direct', 'online_token', 'offline'
            payment_data = payment_data['payment_intent']
        amount = payment_utils.to_major_currency_units(
            payment_data.get('amount', 0),
            self.currency_id,
            arbitrary_decimal_number=const.CURRENCY_DECIMALS.get(self.currency_id.name),
        )
        currency_code = payment_data.get('currency', '').upper()
        return {
            'amount': amount,
            'currency_code': currency_code,
        }

    def _apply_updates(self, payment_data):
        """Override of `payment` to update the transaction based on the payment data."""
        if self.provider_code != 'stripe':
            return super()._apply_updates(payment_data)

        # Update the payment method.
        payment_method = payment_data.get('payment_method')
        if isinstance(payment_method, dict):  # capture/void/refund requests receive a string.
            payment_method_type = payment_method.get('type')
            if self.payment_method_id.code == payment_method_type == 'card':
                payment_method_type = payment_data['payment_method']['card']['brand']
            payment_method = self.env['payment.method']._get_from_code(
                payment_method_type, mapping=const.PAYMENT_METHODS_MAPPING
            )
            self.payment_method_id = payment_method or self.payment_method_id

        # Update the provider reference and the payment state.
        if self.operation == 'validation':
            self.provider_reference = payment_data['setup_intent']['id']
            status = payment_data['setup_intent']['status']
        elif self.operation == 'refund':
            self.provider_reference = payment_data['refund']['id']
            status = payment_data['refund']['status']
        else:  # 'online_direct', 'online_token', 'offline'
            self.provider_reference = payment_data['payment_intent']['id']
            status = payment_data['payment_intent']['status']
        if not status:
            self._set_error(_("Received data with missing intent status."))
        elif status in const.STATUS_MAPPING['draft']:
            pass
        elif status in const.STATUS_MAPPING['pending']:
            self._set_pending()
        elif status in const.STATUS_MAPPING['authorized']:
            self._set_authorized()
        elif status in const.STATUS_MAPPING['done']:
            self._set_done()

            # Immediately post-process the transaction if it is a refund, as the post-processing
            # will not be triggered by a customer browsing the transaction from the portal.
            if self.operation == 'refund':
                self.env.ref('payment.cron_post_process_payment_tx')._trigger()
        elif status in const.STATUS_MAPPING['cancel']:
            self._set_canceled()
        elif status in const.STATUS_MAPPING['error']:
            if self.operation != 'refund':
                last_payment_error = payment_data.get('payment_intent', {}).get(
                    'last_payment_error'
                )
                if last_payment_error:
                    message = last_payment_error.get('message', {})
                else:
                    message = _("The customer left the payment page.")
                self._set_error(message)
            else:
                self._set_error(_(
                    "The refund did not go through. Please log into your Stripe Dashboard to get "
                    "more information on that matter, and address any accounting discrepancies."
                ), extra_allowed_states=('done',))
        else:  # Classify unknown intent statuses as `error` tx state
            _logger.warning(
                "Received invalid payment status (%s) for transaction %s.",
                status, self.reference
            )
            self._set_error(_("Received data with invalid intent status: %s.", status))

    def _extract_token_values(self, payment_data):
        """Override of `payment` to return token data based on Stripe data.

        Note: self.ensure_one() from :meth: `_tokenize`

        :param dict payment_data: The payment data sent by the provider.
        :return: Data to create a token.
        :rtype: dict
        """
        if self.provider_code != 'stripe':
            return super()._extract_token_values(payment_data)

        payment_method = payment_data.get('payment_method')
        if not payment_method:
            _logger.warning("requested tokenization from payment data with missing payment method")
            return {}

        mandate = None
        # Extract the Stripe objects from the payment data.
        if self.operation == 'online_direct':
            customer_id = payment_data['payment_intent']['customer']
            charges_data = payment_data['payment_intent']['charges']
            payment_method_details = charges_data['data'][0].get('payment_method_details')
            if payment_method_details:
                mandate = payment_method_details[payment_method_details['type']].get("mandate")
        else:  # 'validation'
            customer_id = payment_data['setup_intent']['customer']
        # Another payment method (e.g., SEPA) might have been generated.
        if not payment_method[payment_method['type']]:
            try:
                payment_methods = self._send_api_request(
                    'GET', f'customers/{customer_id}/payment_methods'
                )
            except ValidationError as e:
                self._set_error(str(e))
                return {}
            payment_method = payment_methods['data'][0]

        return {
            'payment_details': payment_method[payment_method['type']].get('last4'),
            'provider_ref': customer_id,
            'stripe_payment_method': payment_method['id'],
            'stripe_mandate': mandate,
        }
