# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint
import time
from datetime import datetime

from dateutil.relativedelta import relativedelta

from odoo import _, api, models
from odoo.exceptions import UserError, ValidationError

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment_razorpay import const


_logger = logging.getLogger(__name__)


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
        res = super()._get_specific_processing_values(processing_values)
        if self.provider_code != 'razorpay':
            return res

        if self.operation in ('online_token', 'offline'):
            return {}

        customer_id = self._razorpay_create_customer()['id']
        order_id = self._razorpay_create_order(customer_id)['id']
        return {
            'razorpay_key_id': self.provider_id.razorpay_key_id,
            'razorpay_customer_id': customer_id,
            'is_tokenize_request': self.tokenize,
            'razorpay_order_id': order_id,
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
        _logger.info(
            "Sending '/customers' request for transaction with reference %s:\n%s",
            self.reference, pprint.pformat(payload)
        )
        customer_data = self.provider_id._razorpay_make_request('customers', payload=payload)
        _logger.info(
            "Response of '/customers' request for transaction with reference %s:\n%s",
            self.reference, pprint.pformat(customer_data)
        )
        return customer_data

    @api.model
    def _validate_phone_number(self, phone):
        """ Validate and format the phone number.

        :param str phone: The phone number to validate.
        :return str: The formatted phone number.
        :raise ValidationError: If the phone number is missing or incorrect.
        """
        if not phone and self.tokenize:
            raise ValidationError("Razorpay: " + _("The phone number is missing."))

        try:
            phone = self._phone_format(
                number=phone, country=self.partner_country_id, raise_exception=self.tokenize
            )
        except Exception:
            raise ValidationError("Razorpay: " + _("The phone number is invalid."))
        return phone

    def _razorpay_create_order(self, customer_id=None):
        """ Create and return an Order object to initiate the payment.

        :param str customer_id: The ID of the Customer object to assign to the Order for
                                non-subsequent payments.
        :return: The created Order.
        :rtype: dict
        """
        payload = self._razorpay_prepare_order_payload(customer_id=customer_id)
        _logger.info(
            "Sending '/orders' request for transaction with reference %s:\n%s",
            self.reference, pprint.pformat(payload)
        )
        order_data = self.provider_id._razorpay_make_request('orders', payload=payload)
        _logger.info(
            "Response of '/orders' request for transaction with reference %s:\n%s",
            self.reference, pprint.pformat(order_data)
        )
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
            **({'method': pm_code} if pm_code != 'wallets_india' else {}),
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
        :rtype: int
        """
        pm_code = (
            self.payment_method_id.primary_payment_method_id or self.payment_method_id
        ).code
        pm_max_amount = const.MANDATE_MAX_AMOUNT.get(pm_code, 100000)
        mandate_values = self._get_mandate_values()  # The linked document's values.
        if 'amount' in mandate_values and 'MRR' in mandate_values:
            max_amount = min(
                pm_max_amount, max(mandate_values['amount'] * 1.5, mandate_values['MRR'] * 5)
            )
        else:
            max_amount = pm_max_amount
        return max_amount

    def _send_payment_request(self):
        """ Override of `payment` to send a payment request to Razorpay.

        Note: self.ensure_one()

        :return: None
        :raise UserError: If the transaction is not linked to a token.
        """
        super()._send_payment_request()
        if self.provider_code != 'razorpay':
            return

        if not self.token_id:
            raise UserError("Razorpay: " + _("The transaction is not linked to a token."))

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
            _logger.info(
                "Sending '/payments/create/recurring' request for transaction with reference %s:\n%s",
                self.reference, pprint.pformat(payload)
            )
            recurring_payment_data = self.provider_id._razorpay_make_request(
                'payments/create/recurring', payload=payload
            )
            _logger.info(
                "Response of '/payments/create/recurring' request for transaction with reference "
                "%s:\n%s", self.reference, pprint.pformat(recurring_payment_data)
            )
            self._handle_notification_data('razorpay', recurring_payment_data)
        except ValidationError as e:
            if self.operation == 'offline':
                self._set_error(str(e))
            else:
                raise

    def _send_refund_request(self, amount_to_refund=None):
        """ Override of `payment` to send a refund request to Razorpay.

        Note: self.ensure_one()

        :param float amount_to_refund: The amount to refund.
        :return: The refund transaction created to process the refund request.
        :rtype: recordset of `payment.transaction`
        """
        refund_tx = super()._send_refund_request(amount_to_refund=amount_to_refund)
        if self.provider_code != 'razorpay':
            return refund_tx

        # Make the refund request to Razorpay.
        converted_amount = payment_utils.to_minor_currency_units(
            -refund_tx.amount, refund_tx.currency_id
        )  # The amount is negative for refund transactions.
        payload = {
            'amount': converted_amount,
            'notes': {
                'reference': refund_tx.reference,  # Allow retrieving the ref. from webhook data.
            },
        }
        _logger.info(
            "Payload of '/payments/<id>/refund' request for transaction with reference %s:\n%s",
            self.reference, pprint.pformat(payload)
        )
        response_content = refund_tx.provider_id._razorpay_make_request(
            f'payments/{self.provider_reference}/refund', payload=payload
        )
        _logger.info(
            "Response of '/payments/<id>/refund' request for transaction with reference %s:\n%s",
            self.reference, pprint.pformat(response_content)
        )
        response_content.update(entity_type='refund')
        refund_tx._handle_notification_data('razorpay', response_content)

        return refund_tx

    def _send_capture_request(self, amount_to_capture=None):
        """ Override of `payment` to send a capture request to Razorpay. """
        child_capture_tx = super()._send_capture_request(amount_to_capture=amount_to_capture)
        if self.provider_code != 'razorpay':
            return child_capture_tx

        converted_amount = payment_utils.to_minor_currency_units(self.amount, self.currency_id)
        payload = {'amount': converted_amount, 'currency': self.currency_id.name}
        _logger.info(
            "Payload of '/payments/<id>/capture' request for transaction with reference %s:\n%s",
            self.reference, pprint.pformat(payload)
        )
        response_content = self.provider_id._razorpay_make_request(
            f'payments/{self.provider_reference}/capture', payload=payload
        )
        _logger.info(
            "Response of '/payments/<id>/capture' request for transaction with reference %s:\n%s",
            self.reference, pprint.pformat(response_content)
        )

        # Handle the capture request response.
        self._handle_notification_data('razorpay', response_content)

        return child_capture_tx

    def _send_void_request(self, amount_to_void=None):
        """ Override of `payment` to explain that it is impossible to void a Razorpay transaction.
        """
        child_void_tx = super()._send_void_request(amount_to_void=amount_to_void)
        if self.provider_code != 'razorpay':
            return child_void_tx

        raise UserError(_("Transactions processed by Razorpay can't be manually voided from Odoo."))

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """ Override of `payment` to find the transaction based on razorpay data.

        :param str provider_code: The code of the provider that handled the transaction
        :param dict notification_data: The normalized notification data sent by the provider
        :return: The transaction if found
        :rtype: recordset of `payment.transaction`
        :raise: ValidationError if the data match no transaction
        """
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'razorpay' or len(tx) == 1:
            return tx

        entity_type = notification_data.get('entity_type', 'payment')
        if entity_type == 'payment':
            reference = notification_data.get('description')
            if not reference:
                raise ValidationError("Razorpay: " + _("Received data with missing reference."))
            tx = self.search([('reference', '=', reference), ('provider_code', '=', 'razorpay')])
        else:  # 'refund'
            notes = notification_data.get('notes')
            reference = isinstance(notes, dict) and notes.get('reference')
            if reference:  # The refund was initiated from Odoo.
                tx = self.search([('reference', '=', reference), ('provider_code', '=', 'razorpay')])
            else:  # The refund was initiated from Razorpay.
                # Find the source transaction based on its provider reference.
                source_tx = self.search([
                    ('provider_reference', '=', notification_data['payment_id']),
                    ('provider_code', '=', 'razorpay'),
                ])
                if source_tx:
                    # Manually create a refund transaction with a new reference.
                    tx = self._razorpay_create_refund_tx_from_notification_data(
                        source_tx, notification_data
                    )
                else:  # The refund was initiated for an unknown source transaction.
                    pass  # Don't do anything with the refund notification.
        if not tx:
            raise ValidationError(
                "Razorpay: " + _("No transaction found matching reference %s.", reference)
            )

        return tx

    def _razorpay_create_refund_tx_from_notification_data(self, source_tx, notification_data):
        """ Create a refund transaction based on Razorpay data.

        :param recordset source_tx: The source transaction for which a refund is initiated, as a
                                    `payment.transaction` recordset.
        :param dict notification_data: The notification data sent by the provider.
        :return: The newly created refund transaction.
        :rtype: recordset of `payment.transaction`
        :raise ValidationError: If inconsistent data were received.
        """
        refund_provider_reference = notification_data.get('id')
        amount_to_refund = notification_data.get('amount')
        if not refund_provider_reference or not amount_to_refund:
            raise ValidationError("Razorpay: " + _("Received incomplete refund data."))

        converted_amount = payment_utils.to_major_currency_units(
            amount_to_refund, source_tx.currency_id
        )
        return source_tx._create_child_transaction(
            converted_amount, is_refund=True, provider_reference=refund_provider_reference
        )

    def _process_notification_data(self, notification_data):
        """ Override of `payment` to process the transaction based on Razorpay data.

        Note: self.ensure_one()

        :param dict notification_data: The notification data sent by the provider
        :return: None
        """
        super()._process_notification_data(notification_data)
        if self.provider_code != 'razorpay':
            return

        if 'id' in notification_data:  # We have the full entity data (S2S request or webhook).
            entity_data = notification_data
        else:  # The payment data are not complete (redirect from checkout).
            # Fetch the full payment data.
            entity_data = self.provider_id._razorpay_make_request(
                f'payments/{notification_data["razorpay_payment_id"]}', method='GET'
            )
            _logger.info(
                "Response of '/payments' request for transaction with reference %s:\n%s",
                self.reference, pprint.pformat(entity_data)
            )

        # Update the provider reference.
        entity_id = entity_data.get('id')
        if not entity_id:
            raise ValidationError("Razorpay: " + _("Received data with missing entity id."))
        self.provider_reference = entity_id

        # Update the payment method.
        payment_method_type = entity_data.get('method', '')
        if payment_method_type == 'card':
            payment_method_type = entity_data.get('card', {}).get('network', '').lower()
        payment_method = self.env['payment.method']._get_from_code(
            payment_method_type, mapping=const.PAYMENT_METHODS_MAPPING
        )
        self.payment_method_id = payment_method or self.payment_method_id

        # Update the payment state.
        entity_status = entity_data.get('status')
        if not entity_status:
            raise ValidationError("Razorpay: " + _("Received data with missing status."))

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
                self._razorpay_tokenize_from_notification_data(entity_data)
            self._set_done()

            # Immediately post-process the transaction if it is a refund, as the post-processing
            # will not be triggered by a customer browsing the transaction from the portal.
            if self.operation == 'refund':
                self.env.ref('payment.cron_post_process_payment_tx')._trigger()
        elif entity_status in const.PAYMENT_STATUS_MAPPING['error']:
            _logger.warning(
                "The transaction with reference %s underwent an error. Reason: %s",
                self.reference, entity_data.get('error_description')
            )
            self._set_error(
                _("An error occurred during the processing of your payment. Please try again.")
            )
        else:  # Classify unsupported payment status as the `error` tx state.
            _logger.warning(
                "Received data for transaction with reference %s with invalid payment status: %s",
                self.reference, entity_status
            )
            self._set_error(
                "Razorpay: " + _("Received data with invalid status: %s", entity_status)
            )

    def _razorpay_tokenize_from_notification_data(self, notification_data):
        """ Create a new token based on the notification data.

        :param dict notification_data: The notification data built with Razorpay objects.
                                       See `_process_notification_data`.
        :return: None
        """
        pm_code = (self.payment_method_id.primary_payment_method_id or self.payment_method_id).code
        if pm_code == 'card':
            details = notification_data.get('card', {}).get('last4')
        elif pm_code == 'upi':
            temp_vpa = notification_data.get('vpa')
            details = temp_vpa[temp_vpa.find('@') - 1:]
        else:
            details = pm_code

        token = self.env['payment.token'].create({
            'provider_id': self.provider_id.id,
            'payment_method_id': self.payment_method_id.id,
            'payment_details': details,
            'partner_id': self.partner_id.id,
            # Razorpay requires both the customer ID and the token ID which are extracted from here.
            'provider_ref': f'{notification_data["customer_id"]},{notification_data["token_id"]}',
        })
        self.write({
            'token_id': token,
            'tokenize': False,
        })
        _logger.info(
            "Created token with id %(token_id)s for partner with id %(partner_id)s from "
            "transaction with reference %(ref)s",
            {
                'token_id': token.id,
                'partner_id': self.partner_id.id,
                'ref': self.reference,
            },
        )
