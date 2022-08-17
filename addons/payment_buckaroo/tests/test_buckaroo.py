# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from werkzeug.exceptions import Forbidden

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_buckaroo.controllers.main import BuckarooController
from odoo.addons.payment_buckaroo.tests.common import BuckarooCommon


@tagged('post_install', '-at_install')
class BuckarooTest(BuckarooCommon, PaymentHttpCommon):

    def test_redirect_form_values(self):
        self.patch(self, 'base_url', lambda: 'http://127.0.0.1:8069')
        self.patch(type(self.env['base']), 'get_base_url', lambda _: 'http://127.0.0.1:8069')

        return_url = self._build_url(BuckarooController._return_url)
        expected_values = {
            'Brq_websitekey': self.buckaroo.buckaroo_website_key,
            'Brq_amount': str(self.amount),
            'Brq_currency': self.currency.name,
            'Brq_invoicenumber': self.reference,
            'Brq_signature': 'dacc220c3087edcc1200a38a6db0191c823e7f69',
            'Brq_return': return_url,
            'Brq_returncancel': return_url,
            'Brq_returnerror': return_url,
            'Brq_returnreject': return_url,
            'Brq_culture': 'en-US',
        }

        tx_sudo = self._create_transaction(flow='redirect')
        with mute_logger('odoo.addons.payment.models.payment_transaction'):
            processing_values = tx_sudo._get_processing_values()
        form_info = self._extract_values_from_html_form(processing_values['redirect_form_html'])

        self.assertEqual(form_info['action'], "https://testcheckout.buckaroo.nl/html/")
        self.assertDictEqual(expected_values, form_info['inputs'],
            "Buckaroo: invalid inputs specified in the redirect form.")

    @mute_logger('odoo.addons.payment_buckaroo.models.payment_transaction')
    def test_feedback_processing(self):
        notification_data = BuckarooController._normalize_data_keys(self.sync_notification_data)
        tx = self._create_transaction(flow='redirect')
        tx._handle_notification_data('buckaroo', notification_data)
        self.assertEqual(tx.state, 'done')
        self.assertEqual(tx.provider_reference, notification_data.get('brq_transactions'))
        tx._handle_notification_data('buckaroo', notification_data)
        self.assertEqual(tx.state, 'done', 'Buckaroo: validation did not put tx into done state')
        self.assertEqual(tx.provider_reference, notification_data.get('brq_transactions'))

        self.reference = 'Test Transaction 2'
        tx = self._create_transaction(flow='redirect')
        notification_data = BuckarooController._normalize_data_keys(dict(
            self.sync_notification_data,
            brq_invoicenumber=self.reference,
            brq_statuscode='2',
            brq_signature='b8e54e26b2b5a5e697b8ed5085329ea712fd48b2',
        ))
        self.env['payment.transaction']._handle_notification_data('buckaroo', notification_data)
        self.assertEqual(tx.state, 'error')

    @mute_logger('odoo.addons.payment_buckaroo.controllers.main')
    def test_webhook_notification_confirms_transaction(self):
        """ Test the processing of a webhook notification. """
        tx = self._create_transaction('redirect')
        url = self._build_url(BuckarooController._webhook_url)
        with patch(
            'odoo.addons.payment_buckaroo.controllers.main.BuckarooController'
            '._verify_notification_signature'
        ):
            self._make_http_post_request(url, data=self.async_notification_data)
        self.assertEqual(tx.state, 'done')

    @mute_logger('odoo.addons.payment_buckaroo.controllers.main')
    def test_webhook_notification_triggers_signature_check(self):
        """ Test that receiving a webhook notification triggers a signature check. """
        self._create_transaction('redirect')
        url = self._build_url(BuckarooController._return_url)
        with patch(
            'odoo.addons.payment_buckaroo.controllers.main.BuckarooController'
            '._verify_notification_signature'
        ) as signature_check_mock, patch(
            'odoo.addons.payment.models.payment_transaction.PaymentTransaction'
            '._handle_notification_data'
        ):
            self._make_http_post_request(url, data=self.async_notification_data)
            self.assertEqual(signature_check_mock.call_count, 1)

    def test_accept_notification_with_valid_signature(self):
        """ Test the verification of a notification with a valid signature. """
        tx = self._create_transaction('redirect')
        self._assert_does_not_raise(
            Forbidden,
            BuckarooController._verify_notification_signature,
            self.async_notification_data,
            self.async_notification_data['brq_signature'],
            tx,
        )

    @mute_logger('odoo.addons.payment_buckaroo.controllers.main')
    def test_reject_notification_with_missing_signature(self):
        """ Test the verification of a notification with a missing signature. """
        tx = self._create_transaction('redirect')
        self.assertRaises(
            Forbidden,
            BuckarooController._verify_notification_signature,
            self.async_notification_data,
            None,
            tx,
        )

    @mute_logger('odoo.addons.payment_buckaroo.controllers.main')
    def test_reject_notification_with_invalid_signature(self):
        """ Test the verification of a notification with an invalid signature. """
        tx = self._create_transaction('redirect')
        self.assertRaises(
            Forbidden,
            BuckarooController._verify_notification_signature,
            self.async_notification_data,
            'dummy',
            tx,
        )

    def test_signature_is_computed_based_on_lower_case_data_keys(self):
        """ Test that lower case keys are used to execute the case-insensitive sort. """
        computed_signature = self.provider._buckaroo_generate_digital_sign({
            'brq_a': '1',
            'brq_b': '2',
            'brq_c_first': '3',
            'brq_csecond': '4',
            'brq_D': '5',
        }, incoming=False)
        self.assertEqual(
            computed_signature,
            '937cca8f486b75e93df1e9811a5ebf43357fc3f2',
            msg="The signing string items should be ordered based on a lower-case copy of the keys",
        )

    def test_buckaroo_neutralize(self):
        self.env['payment.provider']._neutralize()

        self.assertEqual(self.provider.buckaroo_website_key, False)
        self.assertEqual(self.provider.buckaroo_secret_key, False)
