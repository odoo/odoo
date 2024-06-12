# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from werkzeug import urls

from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tools import float_repr, mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_paypal.controllers.main import PaypalController
from odoo.addons.payment_paypal.tests.common import PaypalCommon


@tagged('post_install', '-at_install')
class PaypalTest(PaypalCommon, PaymentHttpCommon):

    def _get_expected_values(self):
        return_url = self._build_url(PaypalController._return_url)
        cancel_url = self._build_url(PaypalController._cancel_url)
        cancel_url_params = {
            'tx_ref': self.reference,
            'return_access_tkn': self._generate_test_access_token(self.reference),
        }
        return {
            'address1': 'Huge Street 2/543',
            'amount': str(self.amount),
            'business': self.paypal.paypal_email_account,
            'cancel_return': f'{cancel_url}?{urls.url_encode(cancel_url_params)}',
            'city': 'Sin City',
            'cmd': '_xclick',
            'country': 'BE',
            'currency_code': self.currency.name,
            'email': 'norbert.buyer@example.com',
            'first_name': 'Norbert',
            'item_name': f'{self.paypal.company_id.name}: {self.reference}',
            'item_number': self.reference,
            'last_name': 'Buyer',
            'lc': 'en_US',
            'notify_url': self._build_url(PaypalController._webhook_url),
            'return': return_url,
            'rm': '2',
            'zip': '1000',
        }

    @mute_logger('odoo.addons.payment.models.payment_transaction')
    def test_redirect_form_values(self):
        tx = self._create_transaction(flow='redirect')
        with patch(
            'odoo.addons.payment.utils.generate_access_token', new=self._generate_test_access_token
        ):
            processing_values = tx._get_processing_values()

        form_info = self._extract_values_from_html_form(processing_values['redirect_form_html'])
        self.assertEqual(
            form_info['action'],
            'https://www.sandbox.paypal.com/cgi-bin/webscr')

        expected_values = self._get_expected_values()
        self.assertDictEqual(
            expected_values,
            form_info['inputs'],
            "Paypal: invalid inputs specified in the redirect form.",
        )

    def test_feedback_processing(self):
        # Unknown transaction
        with self.assertRaises(ValidationError):
            self.env['payment.transaction']._handle_notification_data('paypal', self.notification_data)

        # Confirmed transaction
        tx = self._create_transaction('redirect')
        self.env['payment.transaction']._handle_notification_data('paypal', self.notification_data)
        self.assertEqual(tx.state, 'done')
        self.assertEqual(tx.provider_reference, self.notification_data['txn_id'])

        # Pending transaction
        self.reference = 'Test Transaction 2'
        tx = self._create_transaction('redirect')
        payload = dict(
            self.notification_data,
            item_number=self.reference,
            payment_status='Pending',
            pending_reason='multi_currency',
        )
        self.env['payment.transaction']._handle_notification_data('paypal', payload)
        self.assertEqual(tx.state, 'pending')
        self.assertEqual(tx.state_message, payload['pending_reason'])

    def test_parsing_pdt_validation_response_returns_notification_data(self):
        """ Test that the notification data are parsed from the content of a validation response."""
        response_content = 'SUCCESS\nkey1=val1\nkey2=val+2\n'
        notification_data = PaypalController._parse_pdt_validation_response(response_content)
        self.assertDictEqual(notification_data, {'key1': 'val1', 'key2': 'val 2'})

    def test_fail_to_parse_pdt_validation_response_if_not_successful(self):
        """ Test that no notification data are returned from parsing unsuccessful PDT validation."""
        response_content = 'FAIL\ndoes-not-matter'
        notification_data = PaypalController._parse_pdt_validation_response(response_content)
        self.assertIsNone(notification_data)

    @mute_logger('odoo.addons.payment_paypal.controllers.main')
    def test_webhook_notification_confirms_transaction(self):
        """ Test the processing of a webhook notification. """
        tx = self._create_transaction('redirect')
        url = self._build_url(PaypalController._webhook_url)
        with patch(
            'odoo.addons.payment_paypal.controllers.main.PaypalController'
            '._verify_webhook_notification_origin'
        ):
            self._make_http_post_request(url, data=self.notification_data)
        self.assertEqual(tx.state, 'done')

    @mute_logger('odoo.addons.payment_paypal.controllers.main')
    def test_webhook_notification_triggers_origin_check(self):
        """ Test that receiving a webhook notification triggers an origin check. """
        self._create_transaction('redirect')
        url = self._build_url(PaypalController._webhook_url)
        with patch(
            'odoo.addons.payment_paypal.controllers.main.PaypalController'
            '._verify_webhook_notification_origin'
        ) as origin_check_mock, patch(
            'odoo.addons.payment.models.payment_transaction.PaymentTransaction'
            '._handle_notification_data'
        ):
            self._make_http_post_request(url, data=self.notification_data)
            self.assertEqual(origin_check_mock.call_count, 1)
