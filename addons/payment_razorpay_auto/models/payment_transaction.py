# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint
import time

from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import fields, models, _
from odoo.exceptions import ValidationError, UserError


_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    razorpay_payment_method = fields.Selection(([('card', 'Card'), ('upi', 'UPI/QR')]), default=False)

    def _should_not_proccess_rendering_values_for_razorpay(self):
        return super()._should_not_proccess_rendering_values_for_razorpay() or self.tokenize

    # TO-DO: Move this method directly into payment_razorpay
    def _create_order(self, customer_id=False, is_payment_capture=False):
        # Initiate the payment and retrieve the related order id.
        # TO DO master: remove customer from context and add it into argument
        order_payload = self.with_context(razorpay_customer_id=customer_id)._razorpay_prepare_order_request_payload()
        if is_payment_capture:
            order_payload.update(payment_capture=True)
        _logger.info(
            "Payload of '/orders' request for transaction with reference %s:\n%s",
            self.reference, pprint.pformat(order_payload)
        )
        order_response = self.provider_id._razorpay_make_request(endpoint='orders', payload=order_payload)
        _logger.info(
            "Response of '/orders' request for transaction with reference %s:\n%s",
            self.reference, pprint.pformat(order_response)
        )
        return order_response

    def _get_specific_processing_values(self, processing_values):
        """ Override of `payment` to return razorpay-specific processing values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic and specific processing values of the
                                       transaction.
        :return: The dict of provider-specific processing values.
        :rtype: dict
        """
        res = super()._get_specific_processing_values(processing_values)
        if self.provider_code != 'razorpay' or not self.tokenize:
            return res

        # Retrive related customer
        partner = self.env['res.partner'].browse(processing_values.get('partner_id'))
        phone = self._validate_and_sanatize_phone_number(partner.phone)
        customer_payload = {
            'name': partner.name,
            'email': partner.email,
            'contact': phone,
            'fail_existing': '0',
        }
        _logger.info(
            "Payload of '/customers' request for transaction with reference %s:\n%s",
            self.reference, pprint.pformat(customer_payload)
        )
        customer_response = self.provider_id._razorpay_make_request(endpoint='customers', payload=customer_payload)
        _logger.info(
            "Response of '/customers' request for transaction with reference %s:\n%s",
            self.reference, pprint.pformat(customer_response)
        )
        data = {
            'razorpay_key_id': self.provider_id.razorpay_key_id,
            'customer_id': customer_response['id'],
            'is_tokenize_request': not self.provider_id._is_tokenization_required(),
        }
        order_response = self._create_order(customer_id=customer_response['id'])
        return {
            **data,
            'order_id': order_response['id'],
        }

    def _should_rendering_values_return_condition(self):
        return super()._should_rendering_values_return_condition() or self.tokenize

    def _get_razorpay_order_token_data(self):
        self.ensure_one()
        today = datetime.today()
        token_expiry_date = today + relativedelta(years=10) # default years error when we use UPI
        token_expiry_timeslamp = time.mktime(token_expiry_date.timetuple())
        return {
            "expire_at": token_expiry_timeslamp,
            "frequency": "as_presented",
        }

    def _razorpay_prepare_order_request_payload(self):
        payload = super()._razorpay_prepare_order_request_payload()
        if self.env.context.get('razorpay_customer_id'):
            if payload['currency'] != 'INR':
                ValidationError(_("Currency should be 'INR' to create a token in razorpay recurring"))
            payload.update({
                "token": self._get_razorpay_order_token_data(),
                'customer_id': self.env.context['razorpay_customer_id'],
                "method": self.razorpay_payment_method,
            })
        return payload

    def _razorpay_tokenize_from_notification_data(self, notification_data):
        """ Create a new token based on the notification data.

        :param dict notification_data: The notification data built with Razorpay objects.
                                       See `_process_notification_data`.
        :return: None
        """
        # Create the token.
        if self.razorpay_payment_method == 'card':
            payment_details = notification_data.get('card', {}).get('last4', 'dummy')
        elif self.razorpay_payment_method == 'upi':
            temp_vpa = notification_data.get('vpa', 'test@dummy')
            payment_details = temp_vpa[temp_vpa.find('@') - 1:]

        token = self.env['payment.token'].create({
            'provider_id': self.provider_id.id,
            'payment_details': payment_details,
            'partner_id': self.partner_id.id,
            'provider_ref': f"{notification_data['customer_id']},{notification_data['token_id']}",
            'verified': True,
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

    def _send_payment_request(self):
        """ Override of payment to send a payment request to Razorpay for reccuring payment with a token.

        Note: self.ensure_one()

        :return: None
        :raise: UserError if the transaction is not linked to a token
        """
        super()._send_payment_request()
        if self.provider_code != 'razorpay':
            return

        if not self.token_id:
            raise UserError("Razorpay: " + _("The transaction is not linked to a token."))

        order_response = self._create_order(is_payment_capture=True)
        # Create recurring payment
        phone = self._validate_and_sanatize_phone_number(self.partner_id.phone)
        customer_id, token_id = self.token_id.provider_ref.split(',')
        recurring_payment_payload = {
            'email': self.partner_id.email,
            'contact': phone,
            'amount': order_response['amount'],
            'currency': self.currency_id.name,
            'order_id': order_response['id'],
            'customer_id': customer_id,
            'token': token_id,
            'description': self.reference,
            'recurring': "1",
        }
        _logger.info(
            "Payload of '/payments/create/recurring' request for transaction with reference %s:\n%s",
            self.reference, pprint.pformat(recurring_payment_payload)
        )
        recurring_payment_response = self.provider_id._razorpay_make_request(
            endpoint='payments/create/recurring', payload=recurring_payment_payload
        )
        _logger.info(
            "Response of '/payments/create/recurring' request for transaction with reference %s:\n%s",
            self.reference, pprint.pformat(recurring_payment_response)
        )
