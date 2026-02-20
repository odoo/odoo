from unittest.mock import patch

from odoo import Command
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo.addons.pos_safaricom.models.pos_payment_method import PosPaymentMethod
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestSafaricomHttpCommon(TestPointOfSaleHttpCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Mock bearer_token method to avoid actual API calls during setup
        def mock_bearer_token(self):
            """Mock bearer token to return test token without API call"""
            return 'test_token_123'

        # Mock lipa_na_mpesa_register_urls to avoid URL registration API call
        def mock_register_urls(self):
            """Mock URL registration to prevent actual API call during payment method creation"""
            pass

        # Patch the methods that make external API calls
        with patch.object(PosPaymentMethod, 'bearer_token', mock_bearer_token), \
             patch.object(PosPaymentMethod, 'lipa_na_mpesa_register_urls', mock_register_urls):

            # Create M-PESA Express payment method
            mpesa_express_method = cls.env['pos.payment.method'].create({
                'name': 'M-PESA Express',
                'journal_id': cls.bank_journal.id,
                'use_payment_terminal': 'safaricom',
                'safaricom_payment_type': 'mpesa_express',
                'safaricom_test_mode': True,
                'consumer_key': 'test-consumer-key',
                'consumer_secret': 'test-consumer-secret',
                'business_short_code': '174379',
                'passkey': 'test-passkey',
            })

            # Create Lipa na M-PESA payment method
            lipa_na_mpesa_method = cls.env['pos.payment.method'].create({
                'name': 'Lipa na M-PESA',
                'journal_id': cls.bank_journal.id,
                'use_payment_terminal': 'safaricom',
                'safaricom_payment_type': 'lipa_na_mpesa',
                'safaricom_test_mode': True,
                'consumer_key': 'test-consumer-key',
                'consumer_secret': 'test-consumer-secret',
                'business_short_code': '174379',
            })

        payment_methods = cls.main_pos_config.payment_method_ids | mpesa_express_method | lipa_na_mpesa_method
        cls.main_pos_config.write({'payment_method_ids': [Command.set(payment_methods.ids)]})

    def test_mpesa_express_request_data(self):
        """Test M-PESA Express payment request with correct data format"""
        def mocked_mpesa_express_send_payment_request(self, data):
            # Verify amount is an integer
            if not isinstance(data['amount'], int):
                raise TypeError(f"Expected 'amount' to be an integer, but got {data['amount']}.")

            # Verify phone number format
            phone = data.get('phone_number', '')
            if not phone.startswith('254') or len(phone) != 12:
                raise ValueError(f"Invalid phone number format: {phone}")

            # Return mock successful response
            return {
                'success': False,
                'checkout_request_id': 'CO_TEST_123',
                'merchant_request_id': 'TEST-MR-123',
                'message': 'Request accepted for processing',
            }

        with patch.object(PosPaymentMethod, 'mpesa_express_send_payment_request', mocked_mpesa_express_send_payment_request):
            self.main_pos_config.open_ui()
            self.start_tour("/pos/ui/%d" % self.main_pos_config.id, 'MpesaExpressTour', login="accountman")
