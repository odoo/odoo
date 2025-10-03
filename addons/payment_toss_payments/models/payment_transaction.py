# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
from uuid import uuid4

from odoo import api, models

from odoo.addons.payment.logging import get_payment_logger

_logger = get_payment_logger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _get_specific_processing_values(self, processing_values):
        """ Override of payment to return Toss-Payment-specific processing values. Adds
        'products_description', a short description of products for customers, to processing values
        sent to the payment form. The description is mandatory parameter for initializing Toss
        Payments SDK.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic processing values of the tradnsaction
        :return: The dict of provider-specific processing values
        :rtype: dict
        """
        if self.provider_code != 'tosspayments':
            return super()._get_specific_processing_values(processing_values)

        product_ids = []

        if 'invoice_ids' in self._fields:
            product_ids += [
                line.product_id
                for line in self.invoice_ids.invoice_line_ids
                if line.product_id
            ]
        if 'sale_order_ids' in self._fields:
            product_ids += [
                line.product_id
                for line in self.sale_order_ids.order_line
                if line.product_id
            ]

        if len(product_ids) > 0:
            products_description = product_ids[0].name
            if len(product_ids) > 1:
                products_description += self.env._(" and %s other item(s)", len(product_ids) - 1)
        else:
            # We should still pass non-empty string to initialize the payment wizard
            products_description = "Unnamed product"

        customer_key = self.partner_id.commercial_partner_id.tosspayments_customer_key
        if not customer_key:
            customer_key = uuid4()
            self.partner_id.commercial_partner_id.tosspayments_customer_key = customer_key

        return {
            'products_description': products_description,
            'partner_name': self.partner_name,
            'partner_email': self.partner_email,
            'partner_phone': self.partner_phone,
            'customer_key': customer_key,
        }

    @api.model
    def _extract_reference(self, provider_code, payment_data):
        """ Override of `payment` to extract reference from `payment_data` returned by the API.

        Note: `payment_data['orderId']` is base64 encoded `reference` value of the payment tx.
        """
        if provider_code != 'tosspayments':
            return super()._extract_reference(provider_code, payment_data)

        return base64.b64decode(payment_data['orderId'])

    def _extract_amount_data(self, payment_data):
        """ Override of `payment` to extract the amount and currency from the payment data. """
        if self.provider_code != 'tosspayments':
            return super()._extract_amount_data(payment_data)

        return {
            'amount': float(payment_data.get("totalAmount")),
            'currency_code': "KRW",
        }

    def _apply_updates(self, payment_data):
        """ Override of `payment` to extract the amount and currency from the payment data.

        Note: `self.ensure_one()` from :meth:`_process`

        :param dict payment_data: The payment data sent by the provider.
        :return: None
        """
        if self.provider_code != 'tosspayments':
            return super()._apply_updates(payment_data)

        # At the point when this method is called, the API request to the payment provider returned
        # a successful HTTP response. It can be assumed that payment_data['status'] == 'DONE' in any
        # case in our payment flow.
        status = payment_data.get('status')
        if status != 'DONE':
            _logger.error(
                "Skipping update for transaction %s: returned status is '%s', expected 'DONE'.",
                self.reference,
                status,
            )
            return None

        payment_key = payment_data.get('paymentKey')
        if not payment_key:
            _logger.error(
                "Skipping update for transaction %s: 'paymentKey' is missing or empty in returned"
                " response.",
                self.reference,
            )
            return None

        self.provider_reference = payment_key
        self.state = 'done'
        return None
