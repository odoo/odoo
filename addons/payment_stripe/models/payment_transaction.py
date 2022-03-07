# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint

from werkzeug import urls

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment_stripe.const import INTENT_STATUS_MAPPING, PAYMENT_METHOD_TYPES
from odoo.addons.payment_stripe.controllers.main import StripeController

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    stripe_payment_intent = fields.Char(string="Stripe Payment Intent ID", readonly=True)

    def _get_specific_processing_values(self, processing_values):
        """ Override of payment to return Stripe-specific processing values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic processing values of the transaction
        :return: The dict of acquirer-specific processing values
        :rtype: dict
        """
        res = super()._get_specific_processing_values(processing_values)
        if self.provider != 'stripe' or self.operation == 'online_token':
            return res

        checkout_session = self._stripe_create_checkout_session()
        return {
            'publishable_key': self.acquirer_id._get_stripe_publishable_key(),
            'session_id': checkout_session['id'],
        }

    def _stripe_create_checkout_session(self):
        """ Create and return a Checkout Session.

        :return: The Checkout Session
        :rtype: dict
        """
        # Filter payment method types by available payment method
        existing_pms = [pm.name.lower() for pm in self.env['payment.icon'].search([])]
        linked_pms = [pm.name.lower() for pm in self.acquirer_id.payment_icon_ids]
        pm_filtered_pmts = filter(
            lambda pmt: pmt.name == 'card'
            # If the PM (payment.icon) record related to a PMT doesn't exist, don't filter out the
            # PMT because the user couldn't even have linked it to the acquirer in the first place.
            or (pmt.name in linked_pms or pmt.name not in existing_pms),
            PAYMENT_METHOD_TYPES
        )
        # Filter payment method types by country code
        country_code = self.partner_country_id and self.partner_country_id.code.lower()
        country_filtered_pmts = filter(
            lambda pmt: not pmt.countries or country_code in pmt.countries, pm_filtered_pmts
        )
        # Filter payment method types by currency name
        currency_name = self.currency_id.name.lower()
        currency_filtered_pmts = filter(
            lambda pmt: not pmt.currencies or currency_name in pmt.currencies, country_filtered_pmts
        )
        # Filter payment method types by recurrence if the transaction must be tokenized
        if self.tokenize:
            recurrence_filtered_pmts = filter(
                lambda pmt: pmt.recurrence == 'recurring', currency_filtered_pmts
            )
        else:
            recurrence_filtered_pmts = currency_filtered_pmts
        # Build the session values related to payment method types
        pmt_values = {}
        for pmt_id, pmt_name in enumerate(map(lambda pmt: pmt.name, recurrence_filtered_pmts)):
            pmt_values[f'payment_method_types[{pmt_id}]'] = pmt_name

        # Create the session according to the operation and return it
        customer = self._stripe_create_customer()
        common_session_values = self._get_common_stripe_session_values(pmt_values, customer)
        base_url = self.acquirer_id.get_base_url()
        if self.operation == 'online_redirect':
            return_url = f'{urls.url_join(base_url, StripeController._checkout_return_url)}' \
                         f'?reference={urls.url_quote_plus(self.reference)}'
            # Specify a future usage for the payment intent to:
            # 1. attach the payment method to the created customer
            # 2. trigger a 3DS check if one if required, while the customer is still present
            future_usage = 'off_session' if self.tokenize else None
            checkout_session = self.acquirer_id._stripe_make_request(
                'checkout/sessions', payload={
                    **common_session_values,
                    'mode': 'payment',
                    'success_url': return_url,
                    'cancel_url': return_url,
                    'line_items[0][price_data][currency]': self.currency_id.name,
                    'line_items[0][price_data][product_data][name]': self.reference,
                    'line_items[0][price_data][unit_amount]': payment_utils.to_minor_currency_units(
                        self.amount, self.currency_id
                    ),
                    'line_items[0][quantity]': 1,
                    'payment_intent_data[description]': self.reference,
                    'payment_intent_data[setup_future_usage]': future_usage,
                }
            )
            self.stripe_payment_intent = checkout_session['payment_intent']
        else:  # 'validation'
            # {CHECKOUT_SESSION_ID} is a template filled by Stripe when the Session is created
            return_url = f'{urls.url_join(base_url, StripeController._validation_return_url)}' \
                         f'?reference={urls.url_quote_plus(self.reference)}' \
                         f'&checkout_session_id={{CHECKOUT_SESSION_ID}}'
            checkout_session = self.acquirer_id._stripe_make_request(
                'checkout/sessions', payload={
                    **common_session_values,
                    'mode': 'setup',
                    'success_url': return_url,
                    'cancel_url': return_url,
                }
            )
        return checkout_session

    def _stripe_create_customer(self):
        """ Create and return a Customer.

        :return: The Customer
        :rtype: dict
        """
        customer = self.acquirer_id._stripe_make_request(
            'customers', payload={
                'address[city]': self.partner_city or None,
                'address[country]': self.partner_country_id.code or None,
                'address[line1]': self.partner_address or None,
                'address[postal_code]': self.partner_zip or None,
                'address[state]': self.partner_state_id.name or None,
                'description': f'Odoo Partner: {self.partner_id.name} (id: {self.partner_id.id})',
                'email': self.partner_email,
                'name': self.partner_name,
                'phone': self.partner_phone or None,
            }
        )
        return customer

    def _get_common_stripe_session_values(self, pmt_values, customer):
        """ Return the Stripe Session values that are common to redirection and validation.

        Note: This method is overridden by the internal module responsible for Stripe Connect.

        :param dict pmt_values: The payment method types values
        :param dict customer: The Stripe customer to assign to the session
        :return: The common Stripe Session values
        :rtype: dict
        """
        return {
            **pmt_values,
            'client_reference_id': self.reference,
            # Assign a customer to the session so that Stripe automatically attaches the payment
            # method to it in a validation flow. In checkout flow, a customer is automatically
            # created if not provided but we still do it here to avoid requiring the customer to
            # enter his email on the checkout page.
            'customer': customer['id'],
        }

    def _send_payment_request(self):
        """ Override of payment to send a payment request to Stripe with a confirmed PaymentIntent.

        Note: self.ensure_one()

        :return: None
        :raise: UserError if the transaction is not linked to a token
        """
        super()._send_payment_request()
        if self.provider != 'stripe':
            return

        # Make the payment request to Stripe
        if not self.token_id:
            raise UserError("Stripe: " + _("The transaction is not linked to a token."))

        payment_intent = self._stripe_create_payment_intent()
        feedback_data = {'reference': self.reference}
        StripeController._include_payment_intent_in_feedback_data(payment_intent, feedback_data)
        _logger.info("entering _handle_feedback_data with data:\n%s", pprint.pformat(feedback_data))
        self._handle_feedback_data('stripe', feedback_data)

    def _stripe_create_payment_intent(self):
        """ Create and return a PaymentIntent.

        Note: self.ensure_one()

        :return: The Payment Intent
        :rtype: dict
        """
        if not self.token_id.stripe_payment_method:  # Pre-SCA token -> migrate it
            self.token_id._stripe_sca_migrate_customer()

        response = self.acquirer_id._stripe_make_request(
            'payment_intents',
            payload=self._stripe_prepare_payment_intent_payload(),
            offline=self.operation == 'offline',
        )
        if 'error' not in response:
            payment_intent = response
        else:  # A processing error was returned in place of the payment intent
            error_msg = response['error'].get('message')
            self._set_error("Stripe: " + _(
                "The communication with the API failed.\n"
                "Stripe gave us the following info about the problem:\n'%s'", error_msg
            ))  # Flag transaction as in error now as the intent status might have a valid value
            payment_intent = response['error'].get('payment_intent')  # Get the PI from the error

        return payment_intent

    def _stripe_prepare_payment_intent_payload(self):
        """ Prepare the payload for the creation of a payment intent in Stripe format.

        Note: This method is overridden by the internal module responsible for Stripe Connect.
        Note: self.ensure_one()

        :return: The Stripe-formatted payload for the payment intent request
        :rtype: dict
        """
        return {
            'amount': payment_utils.to_minor_currency_units(self.amount, self.currency_id),
            'currency': self.currency_id.name.lower(),
            'confirm': True,
            'customer': self.token_id.acquirer_ref,
            'off_session': True,
            'payment_method': self.token_id.stripe_payment_method,
            'description': self.reference,
        }

    @api.model
    def _get_tx_from_feedback_data(self, provider, data):
        """ Override of payment to find the transaction based on Stripe data.

        :param str provider: The provider of the acquirer that handled the transaction
        :param dict data: The feedback data sent by the provider
        :return: The transaction if found
        :rtype: recordset of `payment.transaction`
        :raise: ValidationError if inconsistent data were received
        :raise: ValidationError if the data match no transaction
        """
        tx = super()._get_tx_from_feedback_data(provider, data)
        if provider != 'stripe':
            return tx

        reference = data.get('reference')
        if not reference:
            raise ValidationError("Stripe: " + _("Received data with missing merchant reference"))

        tx = self.search([('reference', '=', reference), ('provider', '=', 'stripe')])
        if not tx:
            raise ValidationError(
                "Stripe: " + _("No transaction found matching reference %s.", reference)
            )
        return tx

    def _process_feedback_data(self, data):
        """ Override of payment to process the transaction based on Adyen data.

        Note: self.ensure_one()

        :param dict data: The feedback data build from information passed to the return route.
                          Depending on the operation of the transaction, the entries with the keys
                          'payment_intent', 'charge', 'setup_intent' and 'payment_method' can be
                          populated with their corresponding Stripe API objects.
        :return: None
        :raise: ValidationError if inconsistent data were received
        """
        super()._process_feedback_data(data)
        if self.provider != 'stripe':
            return

        if 'charge' in data:
            self.acquirer_reference = data['charge']['id']

        # Handle the intent status
        if self.operation == 'validation':
            intent_status = data.get('setup_intent', {}).get('status')
        else:  # 'online_redirect', 'online_token', 'offline'
            intent_status = data.get('payment_intent', {}).get('status')
        if not intent_status:
            raise ValidationError(
                "Stripe: " + _("Received data with missing intent status.")
            )

        if intent_status in INTENT_STATUS_MAPPING['draft']:
            pass
        elif intent_status in INTENT_STATUS_MAPPING['pending']:
            self._set_pending()
        elif intent_status in INTENT_STATUS_MAPPING['done']:
            if self.tokenize:
                self._stripe_tokenize_from_feedback_data(data)
            self._set_done()
        elif intent_status in INTENT_STATUS_MAPPING['cancel']:
            self._set_canceled()
        else:  # Classify unknown intent statuses as `error` tx state
            _logger.warning("received data with invalid intent status: %s", intent_status)
            self._set_error(
                "Stripe: " + _("Received data with invalid intent status: %s", intent_status)
            )

    def _stripe_tokenize_from_feedback_data(self, data):
        """ Create a new token based on the feedback data.

        :param dict data: The feedback data built with Stripe objects. See `_process_feedback_data`.
        :return: None
        """
        if self.operation == 'online_redirect':
            payment_method_id = data.get('charge', {}).get('payment_method')
            customer_id = data.get('charge', {}).get('customer')
        else:  # 'validation'
            payment_method_id = data.get('setup_intent', {}).get('payment_method', {}).get('id')
            customer_id = data.get('setup_intent', {}).get('customer')
        payment_method = data.get('payment_method')
        if not payment_method_id or not payment_method:
            _logger.warning("requested tokenization with payment method missing from feedback data")
            return

        if payment_method.get('type') != 'card':
            # Only 'card' payment methods can be tokenized. This case should normally not happen as
            # non-recurring payment methods are not shown to the customer if the "Save my payment
            # details checkbox" is shown. Still, better be on the safe side..
            _logger.warning("requested tokenization of non-recurring payment method")
            return

        token = self.env['payment.token'].create({
            'acquirer_id': self.acquirer_id.id,
            'name': payment_utils.build_token_name(payment_method['card'].get('last4')),
            'partner_id': self.partner_id.id,
            'acquirer_ref': customer_id,
            'verified': True,
            'stripe_payment_method': payment_method_id,
        })
        self.write({
            'token_id': token,
            'tokenize': False,
        })
        _logger.info(
            "created token with id %s for partner with id %s", token.id, self.partner_id.id
        )
