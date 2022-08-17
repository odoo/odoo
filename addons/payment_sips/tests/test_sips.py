# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from unittest.mock import patch

from freezegun import freeze_time
from werkzeug.exceptions import Forbidden

from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_sips.controllers.main import SipsController
from odoo.addons.payment_sips.models.payment_provider import SUPPORTED_CURRENCIES
from odoo.addons.payment_sips.tests.common import SipsCommon


@tagged('post_install', '-at_install')
class SipsTest(SipsCommon, PaymentHttpCommon):

    def test_compatible_providers(self):
        for curr in SUPPORTED_CURRENCIES:
            currency = self._prepare_currency(curr)
            providers = self.env['payment.provider']._get_compatible_providers(
                self.company.id, self.partner.id, self.amount, currency_id=currency.id
            )
            self.assertIn(self.sips, providers)

        unsupported_currency = self._prepare_currency('VEF')
        providers = self.env['payment.provider']._get_compatible_providers(
            self.company.id, self.partner.id, self.amount, currency_id=unsupported_currency.id
        )
        self.assertNotIn(self.sips, providers)

    # freeze time for consistent singularize_prefix behavior during the test
    @freeze_time("2011-11-02 12:00:21")
    def test_reference(self):
        tx = self._create_transaction(flow="redirect", reference="")
        self.assertEqual(tx.reference, "tx20111102120021",
            "Payulatam: transaction reference wasn't correctly singularized.")

    def test_redirect_form_values(self):
        self.patch(self, 'base_url', lambda: 'http://127.0.0.1:8069')
        self.patch(type(self.env['base']), 'get_base_url', lambda _: 'http://127.0.0.1:8069')

        tx = self._create_transaction(flow="redirect")

        with mute_logger('odoo.addons.payment.models.payment_transaction'):
            processing_values = tx._get_processing_values()
        form_info = self._extract_values_from_html_form(processing_values['redirect_form_html'])
        form_inputs = form_info['inputs']

        self.assertEqual(form_info['action'], self.sips.sips_test_url)
        self.assertEqual(form_inputs['InterfaceVersion'], self.sips.sips_version)
        return_url = self._build_url(SipsController._return_url)
        notify_url = self._build_url(SipsController._webhook_url)
        self.assertEqual(
            form_inputs['Data'],
            f'amount=111111|currencyCode=978|merchantId=dummy_mid|normalReturnUrl={return_url}|'
            f'automaticResponseUrl={notify_url}|transactionReference={self.reference}|'
            f'statementReference={self.reference}|keyVersion={self.sips.sips_key_version}|'
            f'returnContext={json.dumps(dict(reference=self.reference))}',
        )
        self.assertEqual(
            form_inputs['Seal'], '99d1d2d46a841de7fe313ac0b2d13a9e42cad50b444d35bf901879305818d9b2'
        )

    def test_feedback_processing(self):
        # Unknown transaction
        with self.assertRaises(ValidationError):
            self.env['payment.transaction']._handle_notification_data(
                'sips', self.notification_data
            )

        # Confirmed transaction
        tx = self._create_transaction('redirect')
        self.env['payment.transaction']._handle_notification_data('sips', self.notification_data)
        self.assertEqual(tx.state, 'done')
        self.assertEqual(tx.provider_reference, self.reference)

        # Cancelled transaction
        old_reference = self.reference
        self.reference = 'Test Transaction 2'
        tx = self._create_transaction('redirect')
        payload = dict(
            self.notification_data,
            Data=self.notification_data['Data'].replace(old_reference, self.reference)
                                               .replace('responseCode=00', 'responseCode=12')
        )
        self.env['payment.transaction']._handle_notification_data('sips', payload)
        self.assertEqual(tx.state, 'cancel')

    @mute_logger('odoo.addons.payment_sips.controllers.main')
    def test_webhook_notification_confirms_transaction(self):
        """ Test the processing of a webhook notification. """
        tx = self._create_transaction('redirect')
        url = self._build_url(SipsController._return_url)
        with patch(
            'odoo.addons.payment_sips.controllers.main.SipsController'
            '._verify_notification_signature'
        ):
            self._make_http_post_request(url, data=self.notification_data)
        self.assertEqual(tx.state, 'done')

    @mute_logger('odoo.addons.payment_sips.controllers.main')
    def test_webhook_notification_triggers_signature_check(self):
        """ Test that receiving a webhook notification triggers a signature check. """
        self._create_transaction('redirect')
        url = self._build_url(SipsController._webhook_url)
        with patch(
            'odoo.addons.payment_sips.controllers.main.SipsController'
            '._verify_notification_signature'
        ) as signature_check_mock, patch(
            'odoo.addons.payment.models.payment_transaction.PaymentTransaction'
            '._handle_notification_data'
        ):
            self._make_http_post_request(url, data=self.notification_data)
            self.assertEqual(signature_check_mock.call_count, 1)

    def test_accept_notification_with_valid_signature(self):
        """ Test the verification of a notification with a valid signature. """
        tx = self._create_transaction('redirect')
        self._assert_does_not_raise(
            Forbidden, SipsController._verify_notification_signature, self.notification_data, tx
        )

    @mute_logger('odoo.addons.payment_sips.controllers.main')
    def test_reject_notification_with_missing_signature(self):
        """ Test the verification of a notification with a missing signature. """
        tx = self._create_transaction('redirect')
        payload = dict(self.notification_data, Seal=None)
        self.assertRaises(Forbidden, SipsController._verify_notification_signature, payload, tx)

    @mute_logger('odoo.addons.payment_sips.controllers.main')
    def test_reject_notification_with_invalid_signature(self):
        """ Test the verification of a notification with an invalid signature. """
        tx = self._create_transaction('redirect')
        payload = dict(self.notification_data, Seal='dummy')
        self.assertRaises(Forbidden, SipsController._verify_notification_signature, payload, tx)

    def test_sips_neutralize(self):
        self.env['payment.provider']._neutralize()

        self.assertEqual(self.provider.sips_merchant_id, False)
        self.assertEqual(self.provider.sips_secret, False)
