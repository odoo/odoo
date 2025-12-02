# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo import Command
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_paypal.controllers.main import PaypalController
from odoo.addons.payment_paypal.tests.common import PaypalCommon


@tagged('post_install', '-at_install')
class PaypalTest(PaypalCommon, PaymentHttpCommon):

    def test_processing_values(self):
        tx = self._create_transaction(flow='direct')
        with patch(
            'odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request',
            return_value={'id': self.order_id},
        ):
            processing_values = tx._get_processing_values()
        self.assertEqual(processing_values['order_id'], self.order_id)

    def test_order_payload_values_for_public_user(self):
        """ If a payment is made with the public user we need to make sure that the
            email address is not sent to PayPal and that we provide the country code of the company instead."""
        tx = self._create_transaction(flow='direct', partner_id=self.public_user.partner_id.id)
        payload = tx._paypal_prepare_order_payload()
        customer_payload = payload['payment_source']['paypal']
        self.assertTrue('email_address' not in customer_payload)
        self.assertEqual(customer_payload['address']['country_code'], self.company.country_id.code)

    @mute_logger('odoo.addons.payment_paypal.controllers.main')
    def test_complete_order_confirms_transaction(self):
        """ Test the processing of a webhook notification. """
        tx = self._create_transaction('direct')
        normalized_data = PaypalController._normalize_paypal_data(self, self.completed_order)
        self.env['payment.transaction']._process('paypal', normalized_data)
        self.assertEqual(tx.state, 'done')
        self.assertEqual(tx.provider_reference, normalized_data['id'])

    def test_feedback_processing(self):
        normalized_data = PaypalController._normalize_paypal_data(
            self, self.payment_data.get('resource'), from_webhook=True
        )

        # Confirmed transaction
        tx = self._create_transaction('direct')
        self.env['payment.transaction']._process('paypal', normalized_data)
        self.assertEqual(tx.state, 'done')
        self.assertEqual(tx.provider_reference, normalized_data['id'])

        # Pending transaction
        self.reference = 'Test Transaction 2'
        tx = self._create_transaction('direct')
        payload = {
            **normalized_data,
            'reference_id': self.reference,
            'status': 'PENDING',
            'pending_reason': 'multi_currency',
        }
        self.env['payment.transaction']._process('paypal', payload)
        self.assertEqual(tx.state, 'pending')
        self.assertEqual(tx.state_message, payload['pending_reason'])

    @mute_logger('odoo.addons.payment_paypal.controllers.main')
    def test_webhook_notification_confirms_transaction(self):
        """ Test the processing of a webhook notification. """
        tx = self._create_transaction('direct')
        url = self._build_url(PaypalController._webhook_url)
        with patch(
            'odoo.addons.payment_paypal.controllers.main.PaypalController'
            '._verify_notification_origin'
        ):
            self._make_json_request(url, data=self.payment_data)
        self.assertEqual(tx.state, 'done')

    @mute_logger('odoo.addons.payment_paypal.controllers.main')
    def test_webhook_notification_triggers_origin_check(self):
        """ Test that receiving a webhook notification triggers an origin check. """
        self._create_transaction('direct')
        url = self._build_url(PaypalController._webhook_url)
        with patch(
            'odoo.addons.payment_paypal.controllers.main.PaypalController'
            '._verify_notification_origin'
        ) as origin_check_mock, patch(
            'odoo.addons.payment.models.payment_transaction.PaymentTransaction._process'
        ):
            self._make_json_request(url, data=self.payment_data)
            self.assertEqual(origin_check_mock.call_count, 1)

    def test_provide_shipping_address(self):
        if 'sale.order' not in self.env:
            self.skipTest("Skipping shipping address test because sale is not installed.")

        product = self.env['product.product'].create({'name': "$5", 'list_price': 5.0})
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [Command.create({'product_id': product.id})],
        })
        tx = self._create_transaction(flow='direct', sale_order_ids=[Command.set(order.ids)])

        payload = tx._paypal_prepare_order_payload()
        self.assertEqual(
            payload['payment_source']['paypal']['experience_context']['shipping_preference'],
            'SET_PROVIDED_ADDRESS',
            "Address should be provided when possible",
        )
        self.assertDictEqual(payload['purchase_units'][0]['shipping']['address'], {
            'address_line_1': tx.partner_id.street,
            'address_line_2': tx.partner_id.street2,
            'postal_code': tx.partner_id.zip,
            'admin_area_2': tx.partner_id.city,
            'country_code': tx.partner_id.country_code,
        })

        # Set country to one where state is required
        self.partner.country_id = self.env.ref('base.us')
        payload = tx._paypal_prepare_order_payload()
        self.assertEqual(
            payload['payment_source']['paypal']['experience_context']['shipping_preference'],
            'NO_SHIPPING',
            "No shipping should be set if address values are incomplete",
        )
        self.assertNotIn('shipping', payload['purchase_units'][0])

        self.partner.child_ids = [Command.create({
            'name': tx.partner_id.name,
            'type': 'delivery',
            'street': "40 Wall Street",
            'city': "New York City",
            'zip': "10005",
            'state_id': self.env.ref('base.state_us_27').id,
            'country_id': tx.partner_id.country_id.id,
        })]
        shipping_partner = tx.sale_order_ids.partner_shipping_id = self.partner.child_ids
        payload = tx._paypal_prepare_order_payload()
        self.assertEqual(
            payload['payment_source']['paypal']['experience_context']['shipping_preference'],
            'SET_PROVIDED_ADDRESS',
            "Address should be provided when partner has a complete delivery address",
        )
        self.assertDictEqual(payload['purchase_units'][0]['shipping']['address'], {
            'address_line_1': shipping_partner.street,
            'postal_code': shipping_partner.zip,
            'admin_area_1': shipping_partner.state_id.code,
            'admin_area_2': shipping_partner.city,
            'country_code': shipping_partner.country_code,
        })
