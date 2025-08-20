# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
import time
from datetime import datetime

from dateutil.relativedelta import relativedelta
from werkzeug.urls import url_encode

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.urls import urljoin as url_join

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_razorpay import const
from odoo.addons.payment_razorpay.controllers.main import RazorpayController


_logger = get_payment_logger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _get_specific_processing_values(self, processing_values):
        """ Override of `payment` to return razorpay-specific processing values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic and specific processing values of the
                                       transaction.
        :return: The provider-specific processing values.
        :rtype: dict
        """
        if self.provider_code != 'razorpay':
            return super()._get_specific_processing_values(processing_values)

        if self.operation in ('online_token', 'offline'):
            return {}

        customer_id = self._razorpay_create_customer().get('id')
        order_id = self._razorpay_create_order(customer_id).get('id')

        return {
            'razorpay_key_id': self.provider_id.razorpay_key_id,
            'razorpay_public_token': self.provider_id.razorpay_public_token,
            'razorpay_customer_id': customer_id,
            'is_tokenize_request': self.tokenize,
            'razorpay_order_id': order_id,
            'callback_url': url_join(
                self.provider_id.get_base_url(),
                f'{RazorpayController._return_url}?{url_encode({"reference": self.reference})}'
            ),
            'redirect': self.payment_method_id.code in const.REDIRECT_PAYMENT_METHOD_CODES,
        }

    def _razorpay_create_customer(self):
        """ Create and return a Customer object.

        :return: The created Customer.
        :rtype: dict
        """
        payload = {
            'name': self.partner_name,
            'email': self.partner_email or '',
            'contact': self.partner_phone and self._validate_phone_number(self.partner_phone) or '',
            'fail_existing': '0',  # Don't throw an error if the customer already exists.
        }
        customer_data = {}
        try:
            customer_data = self._send_api_request('POST', 'customers', json=payload)
        except ValidationError as e:
            self._set_error(str(e))

        return customer_data

    @api.model
    def _validate_phone_number(self, phone):
        """ Validate and format the phone number.

        :param str phone: The phone number to validate.
        :returns: The formatted phone number.
        :rtype: str
        :raise ValidationError: If the phone number is missing or incorrect.
        """
        if not phone and self.tokenize:
            raise ValidationError(_("The phone number is missing."))

        try:
            phone = self._phone_format(
                number=phone, country=self.partner_country_id, raise_exception=self.tokenize
            )
        except Exception:
            raise ValidationError(_("The phone number is invalid."))
        return phone

    def _razorpay_create_order(self, customer_id=None):
        """ Create and return an Order object to initiate the payment.

        :param str customer_id: The ID of the Customer object to assign to the Order for
                                non-subsequent payments.
        :return: The created Order.
        :rtype: dict
        """
        payload = self._razorpay_prepare_order_payload(customer_id=customer_id)
        order_data = {}
        try:
            order_data = self._send_api_request('POST', 'orders', json=payload)
        except ValidationError as e:
            self._set_error(str(e))
        return order_data

    def _razorpay_prepare_order_payload(self, customer_id=None):
        """ Prepare the payload for the order request based on the transaction values.

        :param str customer_id: The ID of the Customer object to assign to the Order for
                                non-subsequent payments.
        :return: The request payload.
        :rtype: dict
        """
        converted_amount = payment_utils.to_minor_currency_units(self.amount, self.currency_id)
        pm_code = (self.payment_method_id.primary_payment_method_id or self.payment_method_id).code
        payload = {
            'amount': converted_amount,
            'currency': self.currency_id.name,
            **({'method': pm_code} if pm_code not in const.FALLBACK_PAYMENT_METHOD_CODES else {}),
        }
        if self.operation in ['online_direct', 'validation']:
            payload['customer_id'] = customer_id  # Required for only non-subsequent payments.
            if self.tokenize:
                payload['token'] = {
                    'max_amount': payment_utils.to_minor_currency_units(
                        self._razorpay_get_mandate_max_amount(), self.currency_id
                    ),
                    'expire_at': time.mktime(
                        (datetime.today() + relativedelta(years=10)).timetuple()
                    ),  # Don't expire the token before at least 10 years.
                    'frequency': 'as_presented',
                }
        else:  # 'online_token', 'offline'
            # Required for only subsequent payments.
            payload['payment_capture'] = not self.provider_id.capture_manually
        if self.provider_id.capture_manually:  # The related payment must be only authorized.
            payload.update({
                'payment': {
                    'capture': 'manual',
                    'capture_options': {
                        'manual_expiry_period': 7200,  # The default value for this required option.
                        'refund_speed': 'normal',  # The default value for this required option.
                    }
                },
            })
        return payload

    def _razorpay_get_mandate_max_amount(self):
        """ Return the eMandate's maximum amount to define.

        :return: The eMandate's maximum amount.
        :rtype: float
        """
        pm_code = (
            self.payment_method_id.primary_payment_method_id or self.payment_method_id
        ).code
        pm_max_amount_INR = const.MANDATE_MAX_AMOUNT.get(pm_code, 100000)
        pm_max_amount = self._razorpay_convert_inr_to_currency(pm_max_amount_INR, self.currency_id)
        mandate_values = self._get_mandate_values()  # The linked document's values.
        if 'amount' in mandate_values and 'MRR' in mandate_values:
            max_amount = min(
                pm_max_amount, max(mandate_values['amount'] * 1.5, mandate_values['MRR'] * 5)
            )
        else:
            max_amount = pm_max_amount
        return max_amount

    @api.model
    def _razorpay_convert_inr_to_currency(self, amount, currency_id):
        """ Convert the amount from INR to the given currency.

        :param float amount: The amount to converted, in INR.
        :param currency_id: The currency to which the amount should be converted.
        :return: The converted amount in the given currency.
        :rtype: float
        """
        inr_currency = self.env['res.currency'].with_context(active_test=False).search([
            ('name', '=', 'INR'),
        ], limit=1)
        return inr_currency._convert(amount, currency_id)

    def _send_payment_request(self):
        """Override of `payment` to send a payment request to Razorpay."""
        if self.provider_code != 'razorpay':
            return super()._send_payment_request()

        # Prevent multiple token payments for the same document within 36 hours. Another transaction
        # with the same token could be pending processing due to Razorpay waiting 24 hours.
        # See https://www.rbi.org.in/Scripts/NotificationUser.aspx?Id=11668.
        # Remove every character after the last "-", "-" included
        reference_prefix = re.sub(r'-(?!.*-).*$', '', self.reference) or self.reference
        earlier_pending_tx = self.search([
            ('provider_code', '=', 'razorpay'),
            ('state', '=', 'pending'),
            ('token_id', '=', self.token_id.id),
            ('operation', 'in', ['online_token', 'offline']),
            ('reference', '=like', f'{reference_prefix}%'),
            ('create_date', '>=', fields.Datetime.now() - relativedelta(hours=36)),
            ('id', '!=', self.id),
        ], limit=1)
        if earlier_pending_tx:
            self._set_error(_(
                "Your last payment %s will soon be processed. Please wait up to 24 hours before"
                " trying again, or use another payment method.", earlier_pending_tx.reference
            ))
            return

        try:
            order_data = self._razorpay_create_order()
            phone = self._validate_phone_number(self.partner_phone)
            customer_id, token_id = self.token_id.provider_ref.split(',')
            payload = {
                'email': self.partner_email,
                'contact': phone,
                'amount': order_data['amount'],
                'currency': self.currency_id.name,
                'order_id': order_data['id'],
                'customer_id': customer_id,
                'token': token_id,
                'description': self.reference,
                'recurring': '1',
            }
            recurring_payment_data = self._send_api_request(
                'POST', 'payments/create/recurring', json=payload
            )
        except ValidationError as e:
            self._set_error(str(e))
        else:
            self._process('razorpay', recurring_payment_data)

    def _send_refund_request(self):
        """Override of `payment` to send a refund request to Razorpay."""
        if self.provider_code != 'razorpay':
            return super()._send_refund_request()

        # Send the refund request to Razorpay.
        converted_amount = payment_utils.to_minor_currency_units(
            -self.amount, self.currency_id
        )  # The amount is negative for refund transactions.
        payload = {
            'amount': converted_amount,
            'notes': {
                'reference': self.reference,  # Allow retrieving the ref. from webhook data.
            },
        }
        response_content = self._send_api_request(
            'POST', f'payments/{self.provider_reference}/refund', json=payload
        )
        response_content.update(entity_type='refund')
        self._process('razorpay', response_content)

    def _send_capture_request(self):
        """Override of `payment` to send a capture request to Razorpay."""
        if self.provider_code != 'razorpay':
            return super()._send_capture_request()

        converted_amount = payment_utils.to_minor_currency_units(self.amount, self.currency_id)
        payload = {'amount': converted_amount, 'currency': self.currency_id.name}
        response_content = self._send_api_request(
            'POST', f'payments/{self.provider_reference}/capture', json=payload
        )

        # Process the capture request response.
        self._process('razorpay', response_content)

    def _send_void_request(self):
        """Override of `payment` to explain that it is impossible to void a Razorpay transaction."""
        if self.provider_code != 'razorpay':
            return super()._send_void_request()

        raise UserError(_("Transactions processed by Razorpay can't be manually voided from Odoo."))

    @api.model
    def _search_by_reference(self, provider_code, payment_data):
        """ Override of `payment` to find the transaction based on razorpay data.

        :param str provider_code: The code of the provider that handled the transaction
        :param dict payment_data: The normalized payment data sent by the provider
        :return: The transaction if found
        :rtype: payment.transaction
        :raise: ValidationError if the data match no transaction
        """
        if provider_code != 'razorpay':
            return super()._search_by_reference(provider_code, payment_data)

        entity_type = payment_data.get('entity_type', 'payment')
        tx = self
        if entity_type == 'payment':
            reference = payment_data.get('description')
            if not reference:
                _logger.warning("Received data with missing reference.")
                return tx
            tx = self.search([('reference', '=', reference), ('provider_code', '=', 'razorpay')])
        else:  # 'refund'
            notes = payment_data.get('notes')
            reference = isinstance(notes, dict) and notes.get('reference')
            if reference:  # The refund was initiated from Odoo.
                tx = self.search([('reference', '=', reference), ('provider_code', '=', 'razorpay')])
            else:  # The refund was initiated from Razorpay.
                # Find the source transaction based on its provider reference.
                source_tx = self.search([
                    ('provider_reference', '=', payment_data['payment_id']),
                    ('provider_code', '=', 'razorpay'),
                ])
                if source_tx:
                    # Manually create a refund transaction with a new reference.
                    tx = self._razorpay_create_refund_tx_from_payment_data(
                        source_tx, payment_data
                    )
                else:  # The refund was initiated for an unknown source transaction.
                    pass  # Don't do anything with the refund notification.
        return tx

    def _razorpay_create_refund_tx_from_payment_data(self, source_tx, payment_data):
        """ Create a refund transaction based on Razorpay data.

        :param recordset source_tx: The source transaction for which a refund is initiated, as a
                                    `payment.transaction` recordset.
        :param dict payment_data: The payment data sent by the provider.
        :return: The newly created refund transaction.
        :rtype: payment.transaction
        :raise ValidationError: If inconsistent data were received.
        """
        refund_provider_reference = payment_data.get('id')
        amount_to_refund = payment_data.get('amount')
        if not refund_provider_reference or not amount_to_refund:
            raise ValidationError(_("Received incomplete refund data."))

        converted_amount = payment_utils.to_major_currency_units(
            amount_to_refund, source_tx.currency_id
        )
        return source_tx._create_child_transaction(
            converted_amount, is_refund=True, provider_reference=refund_provider_reference
        )

    def _extract_amount_data(self, payment_data):
        """Override of payment to extract the amount and currency from the payment data."""
        if self.provider_code != 'razorpay':
            return super()._extract_amount_data(payment_data)

        # Amount and currency are not sent in the payment data when redirecting to the return route.
        if 'amount' not in payment_data or 'currency' not in payment_data:
            return

        amount = payment_utils.to_major_currency_units(
            payment_data['amount'], self.currency_id
        )
        return {
            'amount': amount,
            'currency_code': payment_data['currency'],
        }

    def _apply_updates(self, payment_data):
        """Override of `payment` to update the transaction based on the payment data."""
        if self.provider_code != 'razorpay':
            return super()._apply_updates(payment_data)

        if 'id' in payment_data:  # We have the full entity data (S2S request or webhook).
            entity_data = payment_data
        else:  # The payment data are not complete (Payments made by a token).
            # Fetch the full payment data.
            try:
                entity_data = self._send_api_request(
                    'GET', f'payments/{payment_data["razorpay_payment_id"]}'
                )
            except ValidationError as e:
                self._set_error(str(e))
                return

        # Update the provider reference.
        entity_id = entity_data.get('id')
        if not entity_id:
            self._set_error(_("Received data with missing entity id."))
            return

        # One reference can have multiple entity ids as Razorpay allows retry on payment failure.
        # Making sure the last entity id is the one we have in the provider reference.
        allowed_to_modify = self.state not in ('done', 'authorized')
        if allowed_to_modify:
            self.provider_reference = entity_id

        # Update the payment method.
        payment_method_type = entity_data.get('method', '')
        if payment_method_type == 'card':
            payment_method_type = entity_data.get('card', {}).get('network', '').lower()
        payment_method = self.env['payment.method']._get_from_code(
            payment_method_type, mapping=const.PAYMENT_METHODS_MAPPING
        )
        if allowed_to_modify and payment_method:
            self.payment_method_id = payment_method

        # Update the payment state.
        entity_status = entity_data.get('status')
        if not entity_status:
            self._set_error(_("Received data with missing status."))

        if entity_status in const.PAYMENT_STATUS_MAPPING['pending']:
            self._set_pending()
        elif entity_status in const.PAYMENT_STATUS_MAPPING['authorized']:
            if self.provider_id.capture_manually:
                self._set_authorized()
        elif entity_status in const.PAYMENT_STATUS_MAPPING['done']:
            if (
                not self.token_id
                and entity_data.get('token_id')
                and self.provider_id.allow_tokenization
            ):
                # In case the tokenization was requested on provider side not from odoo form.
                self.tokenize = True
            self._set_done()

            # Immediately post-process the transaction if it is a refund, as the post-processing
            # will not be triggered by a customer browsing the transaction from the portal.
            if self.operation == 'refund':
                self.env.ref('payment.cron_post_process_payment_tx')._trigger()
        elif entity_status in const.PAYMENT_STATUS_MAPPING['error']:
            _logger.warning(
                "The transaction %s underwent an error. Reason: %s",
                self.reference, entity_data.get('error_description')
            )
            self._set_error(
                _("An error occurred during the processing of your payment. Please try again.")
            )
        else:  # Classify unsupported payment status as the `error` tx state.
            _logger.warning(
                "Received data for transaction %s with invalid payment status: %s.",
                self.reference, entity_status
            )
            self._set_error(
                "Razorpay: " + _("Received data with invalid status: %s", entity_status)
            )

    def _extract_token_values(self, payment_data):
        """Override of `payment` to return token data based on Razorpay data.

        Note: self.ensure_one() from :meth: `_tokenize`

        :param dict payment_data: The payment data sent by the provider.
        :return: Data to create a token.
        :rtype: dict
        """
        if self.provider_code != 'razorpay':
            return super()._extract_token_values(payment_data)

        has_token_data = payment_data.get('token_id')
        if self.token_id or not self.provider_id.allow_tokenization or not has_token_data:
            return {}

        pm_code = (self.payment_method_id.primary_payment_method_id or self.payment_method_id).code
        if pm_code == 'card':
            details = payment_data.get('card', {}).get('last4')
        elif pm_code == 'upi':
            temp_vpa = payment_data.get('vpa')
            details = temp_vpa[temp_vpa.find('@') - 1:]
        else:
            details = pm_code
        return {
            'payment_details': details,
            # Razorpay requires both the customer ID and the token ID which are extracted from here.
            'provider_ref': f'{payment_data["customer_id"]},{payment_data["token_id"]}',
        }
