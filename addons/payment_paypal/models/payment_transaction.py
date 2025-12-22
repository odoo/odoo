# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint

from odoo import _, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment_paypal import utils as paypal_utils
from odoo.addons.payment_paypal.const import PAYMENT_STATUS_MAPPING

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    # See https://developer.paypal.com/docs/api-basics/notifications/ipn/IPNandPDTVariables/
    # this field has no use in Odoo except for debugging
    paypal_type = fields.Char(string="PayPal Transaction Type")

    def _get_specific_processing_values(self, processing_values):
        """ Override of `payment` to return the Paypal-specific processing values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic and specific processing values of the
                                       transaction.
        :return: The dict of provider-specific processing values
        :rtype: dict
        """
        res = super()._get_specific_processing_values(processing_values)
        if self.provider_code != 'paypal':
            return res

        payload = self._paypal_prepare_order_payload()

        _logger.info(
            "Sending '/checkout/orders' request for transaction with reference %s:\n%s",
            self.reference, pprint.pformat(payload)
        )
        idempotency_key = payment_utils.generate_idempotency_key(
            self, scope='payment_request_order'
        )
        order_data = self.provider_id._paypal_make_request(
            '/v2/checkout/orders', json_payload=payload, idempotency_key=idempotency_key
        )
        _logger.info(
            "Response of '/checkout/orders' request for transaction with reference %s:\n%s",
            self.reference, pprint.pformat(order_data)
        )
        return {'order_id': order_data['id']}

    def _paypal_prepare_order_payload(self):
        """ Prepare the payload for the Paypal create order request.

        :return: The requested payload to create a Paypal order.
        :rtype: dict
        """
        partner_first_name, partner_last_name = payment_utils.split_partner_name(self.partner_name)
        if self.partner_id.is_public:
            invoice_address_vals = {'address': {'country_code': self.company_id.country_code}}
            shipping_address_vals = {}
        else:
            invoice_address_vals = paypal_utils.format_partner_address(self.partner_id)
            shipping_address_vals = paypal_utils.format_shipping_address(self)
        shipping_preference = 'SET_PROVIDED_ADDRESS' if shipping_address_vals else 'NO_SHIPPING'

        # See https://developer.paypal.com/docs/api/orders/v2/#orders_create!ct=application/json
        payload = {
            'intent': 'CAPTURE',
            'purchase_units': [
                {
                    'reference_id': self.reference,
                    'description': f'{self.company_id.name}: {self.reference}',
                    'amount': {
                        'currency_code': self.currency_id.name,
                        'value': self.amount,
                    },
                    'payee':  {
                        'display_data': {
                            'brand_name': self.provider_id.company_id.name,
                        },
                        'email_address': paypal_utils.get_normalized_email_account(self.provider_id)
                    },
                    **shipping_address_vals,
                },
            ],
            'payment_source': {
                'paypal': {
                    'experience_context': {
                        'shipping_preference': shipping_preference,
                    },
                    'name': {
                        'given_name': partner_first_name,
                        'surname': partner_last_name,
                    },
                    **invoice_address_vals,
                },
            },
        }
        # PayPal does not accept None set to fields and to avoid users getting errors when email
        # is not set on company we will add it conditionally since its not a required field.
        if company_email := self.provider_id.company_id.email:
            payload['purchase_units'][0]['payee']['display_data']['business_email'] = company_email

        return payload

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """ Override of `payment` to find the transaction based on Paypal data.

        :param str provider_code: The code of the provider that handled the transaction.
        :param dict notification_data: The notification data sent by the provider.
        :return: The transaction if found.
        :rtype: payment.transaction
        :raise ValidationError: If the data match no transaction.
        """
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'paypal' or len(tx) == 1:
            return tx

        reference = notification_data.get('reference_id')
        tx = self.search([('reference', '=', reference), ('provider_code', '=', 'paypal')])
        if not tx:
            raise ValidationError(
                "PayPal: " + _("No transaction found matching reference %s.", reference)
            )
        return tx

    def _process_notification_data(self, notification_data):
        """ Override of `payment` to process the transaction based on Paypal data.

        Note: self.ensure_one()

        :param dict notification_data: The notification data sent by the provider.
        :return: None
        :raise ValidationError: If inconsistent data were received.
        """
        super()._process_notification_data(notification_data)
        if self.provider_code != 'paypal':
            return

        if not notification_data:
            self._set_canceled(state_message=_("The customer left the payment page."))
            return

        amount = notification_data.get('amount').get('value')
        currency_code = notification_data.get('amount').get('currency_code')
        assert amount and currency_code, "PayPal: missing amount or currency"
        assert self.currency_id.compare_amounts(float(amount), self.amount) == 0, \
            "PayPal: mismatching amounts"
        assert currency_code == self.currency_id.name, "PayPal: mismatching currency codes"

        # Update the provider reference.
        txn_id = notification_data.get('id')
        txn_type = notification_data.get('txn_type')
        if not all((txn_id, txn_type)):
            raise ValidationError(
                "PayPal: " + _(
                    "Missing value for txn_id (%(txn_id)s) or txn_type (%(txn_type)s).",
                    txn_id=txn_id, txn_type=txn_type
                )
            )
        self.provider_reference = txn_id
        self.paypal_type = txn_type

        # Force PayPal as the payment method if it exists.
        self.payment_method_id = self.env['payment.method'].search(
            [('code', '=', 'paypal')], limit=1
        ) or self.payment_method_id

        # Update the payment state.
        payment_status = notification_data.get('status')

        if payment_status in PAYMENT_STATUS_MAPPING['pending']:
            self._set_pending(state_message=notification_data.get('pending_reason'))
        elif payment_status in PAYMENT_STATUS_MAPPING['done']:
            self._set_done()
        elif payment_status in PAYMENT_STATUS_MAPPING['cancel']:
            self._set_canceled()
        else:
            _logger.info(
                "received data with invalid payment status (%s) for transaction with reference %s",
                payment_status, self.reference
            )
            self._set_error(
                "PayPal: " + _("Received data with invalid payment status: %s", payment_status)
            )
