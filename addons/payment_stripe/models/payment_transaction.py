# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint

from werkzeug.urls import url_encode, url_join

from odoo import _, fields, models
from odoo.exceptions import UserError, ValidationError

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment_stripe import const
from odoo.addons.payment_stripe.controllers.main import StripeController


_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _get_specific_processing_values(self, processing_values):
        """ Override of payment to return Stripe-specific processing values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic processing values of the transaction
        :return: The dict of provider-specific processing values
        :rtype: dict
        """
        res = super()._get_specific_processing_values(processing_values)
        if self.provider_code != 'stripe' or self.operation == 'online_token':
            return res

        intent = self._stripe_create_intent()
        base_url = self.provider_id.get_base_url()
        return {
            'client_secret': intent['client_secret'],
            'return_url': url_join(
                base_url,
                f'{StripeController._return_url}?{url_encode({"reference": self.reference})}',
            ),
        }

    def _send_payment_request(self):
        """ Override of payment to send a payment request to Stripe with a confirmed PaymentIntent.

        Note: self.ensure_one()

        :return: None
        :raise: UserError if the transaction is not linked to a token
        """
        super()._send_payment_request()
        if self.provider_code != 'stripe':
            return

        if not self.token_id:
            raise UserError("Stripe: " + _("The transaction is not linked to a token."))

        # Make the payment request to Stripe
        payment_intent = self._stripe_create_intent()
        _logger.info(
            "payment request response for transaction with reference %s:\n%s",
            self.reference, pprint.pformat(payment_intent)
        )
        if not payment_intent:  # The PI might be missing if Stripe failed to create it.
            return  # There is nothing to process; the transaction is in error at this point.

        # Handle the payment request response
        notification_data = {'reference': self.reference}
        StripeController._include_payment_intent_in_notification_data(
            payment_intent, notification_data
        )
        self._handle_notification_data('stripe', notification_data)

    def _stripe_create_intent(self):
        """ Create and return a PaymentIntent or a SetupIntent object, depending on the operation.

        :return: The created PaymentIntent or SetupIntent object.
        :rtype: dict
        """
        if self.operation == 'validation':
            response = self.provider_id._stripe_make_request(
                'setup_intents', payload=self._stripe_prepare_setup_intent_payload()
            )
        else:  # 'online_direct', 'online_token', 'offline'.
            response = self.provider_id._stripe_make_request(
                'payment_intents',
                payload=self._stripe_prepare_payment_intent_payload(),
                offline=self.operation == 'offline',
                # Prevent multiple offline payments by token (e.g., due to a cursor rollback).
                idempotency_key=payment_utils.generate_idempotency_key(
                    self, scope='payment_intents_token'
                ) if self.operation == 'offline' else None,
            )

        if 'error' not in response:
            intent = response
        else:  # A processing error was returned in place of the intent.
            # The request failed and no error was raised because we are in an offline payment flow.
            # Extract the error from the response, log it, and set the transaction in error to let
            # the calling module handle the issue without rolling back the cursor.
            error_msg = response['error'].get('message')
            _logger.warning(
                "The creation of the intent failed.\n"
                "Stripe gave us the following info about the problem:\n'%s'", error_msg
            )
            self._set_error("Stripe: " + _(
                "The communication with the API failed.\n"
                "Stripe gave us the following info about the problem:\n'%s'", error_msg
            ))  # Flag transaction as in error now, as the intent status might have a valid value.
            intent = response['error'].get('payment_intent') \
                     or response['error'].get('setup_intent')  # Get the intent from the error.

        return intent

    def _stripe_prepare_setup_intent_payload(self):
        """ Prepare the payload for the creation of a SetupIntent object in Stripe format.

        Note: This method serves as a hook for modules that would fully implement Stripe Connect.

        :return: The Stripe-formatted payload for the SetupIntent request.
        :rtype: dict
        """
        customer = self._stripe_create_customer()
        return {
            'customer': customer['id'],
            'description': self.reference,
            'payment_method_types[]': const.PAYMENT_METHODS_MAPPING.get(
                self.payment_method_code, self.payment_method_code
            ),
            **self._stripe_prepare_mandate_options(),
        }

    def _stripe_prepare_payment_intent_payload(self):
        """ Prepare the payload for the creation of a PaymentIntent object in Stripe format.

        Note: This method serves as a hook for modules that would fully implement Stripe Connect.

        :return: The Stripe-formatted payload for the PaymentIntent request.
        :rtype: dict
        """
        ppm_code = self.payment_method_id.primary_payment_method_id.code
        payment_method_type = ppm_code or self.payment_method_code
        payment_intent_payload = {
            'amount': payment_utils.to_minor_currency_units(self.amount, self.currency_id),
            'currency': self.currency_id.name.lower(),
            'description': self.reference,
            'capture_method': 'manual' if self.provider_id.capture_manually else 'automatic',
            'payment_method_types[]': const.PAYMENT_METHODS_MAPPING.get(
                payment_method_type, payment_method_type
            ),
            'expand[]': 'payment_method',
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
                payment_intent_payload.update(
                    setup_future_usage='off_session',
                    **self._stripe_prepare_mandate_options(),
                )
        return payment_intent_payload

    def _stripe_create_customer(self):
        """ Create and return a Customer.

        :return: The Customer
        :rtype: dict
        """
        customer = self.provider_id._stripe_make_request(
            'customers', payload={
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
                mandate_values.get('amount', 15000), self.currency_id
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
            currency_name = self.provider_id._get_validation_currency().name.lower()
            mandate_options[f'{OPTION_PATH_PREFIX}[currency]'] = currency_name

        return mandate_options

    def _send_refund_request(self, amount_to_refund=None):
        """ Override of payment to send a refund request to Stripe.

        Note: self.ensure_one()

        :param float amount_to_refund: The amount to refund.
        :return: The refund transaction created to process the refund request.
        :rtype: recordset of `payment.transaction`
        """
        refund_tx = super()._send_refund_request(amount_to_refund=amount_to_refund)
        if self.provider_code != 'stripe':
            return refund_tx

        # Make the refund request to stripe.
        data = self.provider_id._stripe_make_request(
            'refunds', payload={
                'payment_intent': self.provider_reference,
                'amount': payment_utils.to_minor_currency_units(
                    -refund_tx.amount,  # Refund transactions' amount is negative, inverse it.
                    refund_tx.currency_id,
                ),
            }
        )
        _logger.info(
            "Refund request response for transaction wih reference %s:\n%s",
            self.reference, pprint.pformat(data)
        )
        # Handle the refund request response.
        notification_data = {}
        StripeController._include_refund_in_notification_data(data, notification_data)
        refund_tx._handle_notification_data('stripe', notification_data)

        return refund_tx

    def _send_capture_request(self, amount_to_capture=None):
        """ Override of `payment` to send a capture request to Stripe. """
        child_capture_tx = super()._send_capture_request(amount_to_capture=amount_to_capture)
        if self.provider_code != 'stripe':
            return child_capture_tx

        # Make the capture request to Stripe
        payment_intent = self.provider_id._stripe_make_request(
            f'payment_intents/{self.provider_reference}/capture'
        )
        _logger.info(
            "capture request response for transaction with reference %s:\n%s",
            self.reference, pprint.pformat(payment_intent)
        )

        # Handle the capture request response
        notification_data = {'reference': self.reference}
        StripeController._include_payment_intent_in_notification_data(
            payment_intent, notification_data
        )
        self._handle_notification_data('stripe', notification_data)

        return child_capture_tx

    def _send_void_request(self, amount_to_void=None):
        """ Override of `payment` to send a void request to Stripe. """
        child_void_tx = super()._send_void_request(amount_to_void=amount_to_void)
        if self.provider_code != 'stripe':
            return child_void_tx

        # Make the void request to Stripe
        payment_intent = self.provider_id._stripe_make_request(
            f'payment_intents/{self.provider_reference}/cancel'
        )
        _logger.info(
            "void request response for transaction with reference %s:\n%s",
            self.reference, pprint.pformat(payment_intent)
        )

        # Handle the void request response
        notification_data = {'reference': self.reference}
        StripeController._include_payment_intent_in_notification_data(
            payment_intent, notification_data
        )
        self._handle_notification_data('stripe', notification_data)

        return child_void_tx

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """ Override of payment to find the transaction based on Stripe data.

        :param str provider_code: The code of the provider that handled the transaction
        :param dict notification_data: The notification data sent by the provider
        :return: The transaction if found
        :rtype: recordset of `payment.transaction`
        :raise: ValidationError if inconsistent data were received
        :raise: ValidationError if the data match no transaction
        """
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'stripe' or len(tx) == 1:
            return tx

        reference = notification_data.get('reference')
        if reference:
            tx = self.search([('reference', '=', reference), ('provider_code', '=', 'stripe')])
        elif notification_data.get('event_type') == 'charge.refund.updated':
            # The webhook notifications sent for `charge.refund.updated` events only contain a
            # refund object that has no 'description' (the merchant reference) field. We thus search
            # the transaction by its provider reference which is the refund id for refund txs.
            refund_id = notification_data['object_id']  # The object is a refund.
            tx = self.search(
                [('provider_reference', '=', refund_id), ('provider_code', '=', 'stripe')]
            )
        else:
            raise ValidationError("Stripe: " + _("Received data with missing merchant reference"))

        if not tx:
            raise ValidationError(
                "Stripe: " + _("No transaction found matching reference %s.", reference)
            )
        return tx

    def _process_notification_data(self, notification_data):
        """ Override of `payment` to process the transaction based on Stripe data.

        Note: self.ensure_one()

        :param dict notification_data: The notification data build from information passed to the
                                       return route. Depending on the operation of the transaction,
                                       the entries with the keys 'payment_intent', 'setup_intent'
                                       and 'payment_method' can be populated with their
                                       corresponding Stripe API objects.
        :return: None
        :raise: ValidationError if inconsistent data were received
        """
        super()._process_notification_data(notification_data)
        if self.provider_code != 'stripe':
            return

        # Update the payment method.
        payment_method = notification_data.get('payment_method')
        if isinstance(payment_method, dict):  # capture/void/refund requests receive a string.
            payment_method_type = payment_method.get('type')
            if self.payment_method_id.code == payment_method_type == 'card':
                payment_method_type = notification_data['payment_method']['card']['brand']
            payment_method = self.env['payment.method']._get_from_code(payment_method_type)
            self.payment_method_id = payment_method or self.payment_method_id

        # Update the provider reference and the payment state.
        if self.operation == 'validation':
            self.provider_reference = notification_data['setup_intent']['id']
            status = notification_data['setup_intent']['status']
        elif self.operation == 'refund':
            self.provider_reference = notification_data['refund']['id']
            status = notification_data['refund']['status']
        else:  # 'online_direct', 'online_token', 'offline'
            self.provider_reference = notification_data['payment_intent']['id']
            status = notification_data['payment_intent']['status']
        if not status:
            raise ValidationError(
                "Stripe: " + _("Received data with missing intent status.")
            )
        if status in const.STATUS_MAPPING['draft']:
            pass
        elif status in const.STATUS_MAPPING['pending']:
            self._set_pending()
        elif status in const.STATUS_MAPPING['authorized']:
            if self.tokenize:
                self._stripe_tokenize_from_notification_data(notification_data)
            self._set_authorized()
        elif status in const.STATUS_MAPPING['done']:
            if self.tokenize:
                self._stripe_tokenize_from_notification_data(notification_data)

            self._set_done()

            # Immediately post-process the transaction if it is a refund, as the post-processing
            # will not be triggered by a customer browsing the transaction from the portal.
            if self.operation == 'refund':
                self.env.ref('payment.cron_post_process_payment_tx')._trigger()
        elif status in const.STATUS_MAPPING['cancel']:
            self._set_canceled()
        elif status in const.STATUS_MAPPING['error']:
            if self.operation != 'refund':
                last_payment_error = notification_data.get('payment_intent', {}).get(
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
                "received invalid payment status (%s) for transaction with reference %s",
                status, self.reference
            )
            self._set_error(_("Received data with invalid intent status: %s", status))

    def _stripe_tokenize_from_notification_data(self, notification_data):
        """ Create a new token based on the notification data.

        :param dict notification_data: The notification data built with Stripe objects.
                                       See `_process_notification_data`.
        :return: None
        """
        payment_method = notification_data.get('payment_method')
        if not payment_method:
            _logger.warning(
                "requested tokenization from notification data with missing payment method"
            )
            return

        mandate = None
        # Extract the Stripe objects from the notification data.
        if self.operation == 'online_direct':
            customer_id = notification_data['payment_intent']['customer']
            charges_data = notification_data['payment_intent']['charges']
            payment_method_details = charges_data['data'][0].get('payment_method_details')
            if payment_method_details:
                mandate = payment_method_details[payment_method_details['type']].get("mandate")
        else:  # 'validation'
            customer_id = notification_data['setup_intent']['customer']
        # Another payment method (e.g., SEPA) might have been generated.
        if not payment_method[payment_method['type']]:
            payment_methods = self.provider_id._stripe_make_request(
                f'customers/{customer_id}/payment_methods', method='GET'
            )
            _logger.info("Received payment_methods response:\n%s", pprint.pformat(payment_methods))
            payment_method = payment_methods['data'][0]

        # Create the token.
        token = self.env['payment.token'].create({
            'provider_id': self.provider_id.id,
            'payment_method_id': self.payment_method_id.id,
            'payment_details': payment_method[payment_method['type']].get('last4'),
            'partner_id': self.partner_id.id,
            'provider_ref': customer_id,
            'stripe_payment_method': payment_method['id'],
            'stripe_mandate': mandate,
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
