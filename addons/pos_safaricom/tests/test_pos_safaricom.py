from unittest.mock import MagicMock, patch

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestPosSafaricom(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company = cls.env.ref('base.main_company')
        cls.pos_config = cls.env['pos.config'].create({
            'name': 'Test POS Config',
        })

        # Create M-PESA Express payment method
        cls.mpesa_express = cls.env['pos.payment.method'].create({
            'name': 'M-PESA Express',
            'use_payment_terminal': 'safaricom',
            'safaricom_payment_type': 'mpesa_express',
            'safaricom_test_mode': True,
            'consumer_key': 'test_consumer_key',
            'consumer_secret': 'test_consumer_secret',
            'business_short_code': '174379',
            'passkey': 'test_passkey',
            'company_id': cls.company.id,
        })

        # Mock the URL registration to avoid external HTTP calls during setup
        with patch('odoo.addons.pos_safaricom.models.pos_payment_method.PosPaymentMethod.lipa_na_mpesa_register_urls'):
            # Create Lipa na M-PESA payment method
            cls.lipa_na_mpesa = cls.env['pos.payment.method'].create({
                'name': 'Lipa na M-PESA',
                'use_payment_terminal': 'safaricom',
                'safaricom_payment_type': 'lipa_na_mpesa',
                'safaricom_test_mode': True,
                'consumer_key': 'test_consumer_key',
                'consumer_secret': 'test_consumer_secret',
                'business_short_code': '174379',
                'company_id': cls.company.id,
            })

    @patch('requests.get')
    def test_bearer_token_success(self, mock_get):
        """Test successful OAuth token retrieval"""
        mock_response = MagicMock()
        mock_response.json.return_value = {'access_token': 'test_token_123'}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        token = self.mpesa_express.bearer_token()
        self.assertEqual(token, 'test_token_123')

        # Verify the request was made with correct auth
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        self.assertIn('auth', call_args.kwargs)

    @patch('requests.get')
    def test_bearer_token_missing_credentials(self, mock_get):
        """Test OAuth token retrieval with missing credentials"""
        payment_method = self.env['pos.payment.method'].create({
            'name': 'Test Missing Credentials',
            'use_payment_terminal': 'safaricom',
            'safaricom_payment_type': 'mpesa_express',
            'company_id': self.company.id,
        })

        with self.assertRaises(UserError) as context:
            payment_method.bearer_token()

        self.assertIn('Consumer Key and Consumer Secret are required', str(context.exception))

    @patch('requests.post')
    @patch('odoo.addons.pos_safaricom.models.pos_payment_method.PosPaymentMethod.bearer_token')
    def test_mpesa_express_payment_request(self, mock_bearer, mock_post):
        """Test M-PESA Express STK Push payment request"""
        mock_bearer.return_value = 'test_access_token'

        mock_response = MagicMock()
        mock_response.json.return_value = {
            'ResponseCode': '0',
            'CheckoutRequestID': 'ws_CO_123456789',
            'MerchantRequestID': '12345-67890-1',
            'CustomerMessage': 'Success. Request accepted for processing',
        }
        mock_post.return_value = mock_response

        data = {
            'amount': 100,
            'phone_number': '254712345678',
            'account_reference': 'Order123',
            'transaction_desc': 'Payment for Order123',
        }

        result = self.mpesa_express.mpesa_express_send_payment_request(data)

        self.assertFalse(result.get('success'))  # Not successful until customer confirms
        self.assertEqual(result.get('checkout_request_id'), 'ws_CO_123456789')
        self.assertEqual(result.get('merchant_request_id'), '12345-67890-1')

        # Verify API was called
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        payload = call_args.kwargs['json']
        self.assertEqual(payload['Amount'], 100)
        self.assertEqual(payload['PhoneNumber'], '254712345678')

    @patch('requests.post')
    @patch('odoo.addons.pos_safaricom.models.pos_payment_method.PosPaymentMethod.bearer_token')
    def test_generate_qr_code(self, mock_bearer, mock_post):
        """Test QR code generation for Lipa na M-PESA"""
        mock_bearer.return_value = 'test_access_token'

        mock_response = MagicMock()
        mock_response.json.return_value = {
            'QRCode': 'iVBORw0KGgoAAAANSUhEUgAA...base64_encoded_qr',
        }
        mock_post.return_value = mock_response

        data = {
            'ref': 'ORDER-001',
            'amount': 150,
        }

        result = self.lipa_na_mpesa.generate_qr_code(data)

        self.assertIsNotNone(result)
        self.assertIn('iVBORw0KGgoAAAANSUhEUgAA', result)

        # Verify API was called with correct parameters
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        payload = call_args.kwargs['json']
        self.assertEqual(payload['Amount'], 150)
        self.assertEqual(payload['RefNo'], 'ORDER-001')
