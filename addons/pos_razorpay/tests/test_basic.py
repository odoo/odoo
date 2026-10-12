from unittest.mock import patch

from requests import Response

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged

DEMO_P2P_URL = 'https://demo.ezetap.com/api/3.0/p2padapter/'
DEMO_PAYMENT_URL = 'https://demo.ezetap.com/api/2.0/payment/'


@tagged('post_install', '-at_install')
class TestRazorpayPosRequest(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.currency_id = cls.env.ref('base.INR')
        cls.payment_method = cls.env['pos.payment.method'].create({
            'name': 'RazorPay',
            'type': 'bank',
            'payment_method_type': 'terminal',
            'payment_provider': 'razorpay',
            'razorpay_tid': 'my_razorpay_device_serial_no',
            'razorpay_allowed_payment_modes': 'card',
            'razorpay_username': 'my_razorpay_username',
            'razorpay_api_key': 'my_razorpay_api_key',
            'razorpay_test_mode': True,
        })

    def _mock_razorpay(self, payload):
        """ Patch the razorpay session and record the calls it makes. """
        calls = []

        def mock_post(session, url, **kwargs):
            calls.append({'url': url, 'json': kwargs.get('json', {})})
            response = Response()
            response.status_code = 200
            response._content = b'ok'
            response.json = lambda: payload
            return response

        return calls, patch(
            'odoo.addons.pos_razorpay.models.razorpay_pos_request.requests.Session.post', mock_post
        )

    def test_payment_request_sends_device_and_mode(self):
        calls, mocked = self._mock_razorpay({'success': True, 'p2pRequestId': 12345})
        with mocked:
            result = self.payment_method.razorpay_make_payment_request({
                'amount': 100,
                'referenceId': 'Hoot/ORDER0001',
            })

        self.assertEqual(result, {'success': True, 'p2pRequestId': '12345'})
        self.assertEqual(calls[0]['url'], f'{DEMO_P2P_URL}pay')
        self.assertEqual(calls[0]['json'], {
            'pushTo': {'deviceId': 'my_razorpay_device_serial_no|ezetap_android'},
            'mode': 'CARD',
            'username': 'my_razorpay_username',
            'appKey': 'my_razorpay_api_key',
            'amount': 100,
            'externalRefNumber': 'Hoot/ORDER0001',
        })

    def test_payment_request_reports_error_message(self):
        _calls, mocked = self._mock_razorpay({
            'success': False,
            'errorCode': 'EZETAP_0000387',
            'errorMessage': '`externalRefNumber` field is empty.',
        })
        with mocked:
            result = self.payment_method.razorpay_make_payment_request({'amount': 100})

        self.assertEqual(result, {'error': '`externalRefNumber` field is empty.'})

    def test_fetch_payment_status_authorized(self):
        calls, mocked = self._mock_razorpay({
            'success': True,
            'status': 'AUTHORIZED',
            'messageCode': 'P2P_DEVICE_TXN_DONE',
            'authCode': 'D12345',
            'cardLastFourDigit': '1234',
            'externalRefNumber': 'Hoot/ORDER0001',
            'txnId': '250102070624795E020088174',
            'paymentMode': 'CARD',
            'settlementStatus': 'PENDING',
        })
        with mocked:
            result = self.payment_method.razorpay_fetch_payment_status({'p2pRequestId': '250102'})

        self.assertEqual(calls[0]['url'], f'{DEMO_P2P_URL}status')
        self.assertEqual(calls[0]['json']['origP2pRequestId'], '250102')
        self.assertEqual(result['status'], 'AUTHORIZED')
        self.assertEqual(result['txnId'], '250102070624795E020088174')
        self.assertEqual(result['settlementStatus'], 'PENDING')

    def test_fetch_payment_status_still_on_device(self):
        _calls, mocked = self._mock_razorpay({'success': True, 'messageCode': 'P2P_DEVICE_RECEIVED'})
        with mocked:
            result = self.payment_method.razorpay_fetch_payment_status({'p2pRequestId': '250102'})

        self.assertEqual(result, {'status': 'RECEIVED'})

    def test_fetch_payment_status_cancelled_on_device(self):
        _calls, mocked = self._mock_razorpay({
            'success': True,
            'messageCode': 'P2P_DEVICE_CANCELED',
            'message': 'Transaction cancelled on the terminal',
        })
        with mocked:
            result = self.payment_method.razorpay_fetch_payment_status({'p2pRequestId': '250102'})

        self.assertEqual(result, {
            'error': 'Transaction cancelled on the terminal',
            'payment_messageCode': 'P2P_DEVICE_CANCELED',
        })

    def test_cancel_request_reports_success_as_error(self):
        calls, mocked = self._mock_razorpay({'success': True})
        with mocked:
            result = self.payment_method.razorpay_cancel_payment_request({'p2pRequestId': '250102'})

        self.assertEqual(calls[0]['url'], f'{DEMO_P2P_URL}cancel')
        self.assertNotIn('mode', calls[0]['json'])
        self.assertEqual(result, {'error': 'Razorpay POS transaction canceled successfully'})

    def test_refund_request_uses_void_endpoint(self):
        calls, mocked = self._mock_razorpay({
            'success': True,
            'status': 'VOIDED',
            'authCode': 'D12345',
            'txnId': '250102070624795E020088174',
        })
        with mocked:
            result = self.payment_method.razorpay_make_refund_request({
                'refund_type': 'void',
                'transaction_id': '250102070624795E020088174',
            })

        self.assertEqual(calls[0]['url'], f'{DEMO_PAYMENT_URL}void')
        self.assertEqual(calls[0]['json']['txnId'], '250102070624795E020088174')
        self.assertEqual(result['status'], 'VOIDED')

    def test_refund_request_uses_refund_endpoint(self):
        calls, mocked = self._mock_razorpay({
            'success': True,
            'status': 'REFUNDED',
            'externalRefNumber': 'Hoot/ORDER0001',
        })
        with mocked:
            result = self.payment_method.razorpay_make_refund_request({
                'refund_type': 'refund',
                'amount': 100,
                'transaction_id': '250102070624795E020088174',
                'externalRefNumber': 'Hoot/ORDER0001',
            })

        self.assertEqual(calls[0]['url'], f'{DEMO_PAYMENT_URL}unified/refund')
        self.assertEqual(calls[0]['json']['originalTransactionId'], '250102070624795E020088174')
        self.assertEqual(result['status'], 'REFUNDED')

    def test_terminal_requires_inr_company_currency(self):
        self.env.company.currency_id = self.env.ref('base.EUR')
        with self.assertRaises(UserError):
            self.env['pos.payment.method'].create({
                'name': 'RazorPay EUR',
                'type': 'bank',
                'payment_method_type': 'terminal',
                'payment_provider': 'razorpay',
            })
