# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from freezegun import freeze_time

from odoo.fields import Command
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_asiapay import const
from odoo.addons.payment_asiapay.tests.common import AsiaPayCommon


@tagged('post_install', '-at_install')
class TestPaymentTransaction(AsiaPayCommon, PaymentHttpCommon):

    @freeze_time('2011-11-02 12:00:21')  # Freeze time for consistent singularization behavior.
    def test_reference_is_singularized(self):
        """ Test the singularization of reference prefixes. """
        reference = self.env['payment.transaction']._compute_reference(self.asiapay.code)
        self.assertEqual(reference, 'tx-20111102120021')

    @freeze_time('2011-11-02 12:00:21')  # Freeze time for consistent singularization behavior.
    def test_reference_is_computed_based_on_document_name(self):
        """ Test the computation of reference prefixes based on the provided invoice. """
        self._skip_if_account_payment_is_not_installed()

        invoice = self.env['account.move'].create({})
        reference = self.env['payment.transaction']._compute_reference(
            self.asiapay.code, invoice_ids=[Command.set([invoice.id])]
        )
        self.assertEqual(reference, 'MISC/2011/11/0001-20111102120021')

    @freeze_time('2011-11-02 12:00:21')  # Freeze time for consistent singularization behavior.
    def test_reference_is_stripped_at_max_length(self):
        """ Test that reference prefixes are stripped to have a length of at most 35 chars. """
        reference = self.env['payment.transaction']._compute_reference(
            self.asiapay.code, prefix='this is a long reference of more than 35 characters'
        )
        self.assertEqual(reference, 'this is a long refer-20111102120021')
        self.assertEqual(len(reference), 35)

    def test_no_item_missing_from_rendering_values(self):
        """ Test that the rendered values are conform to the transaction fields. """
        tx = self._create_transaction(flow='redirect')
        with patch(
            'odoo.addons.payment_asiapay.models.payment_provider.PaymentProvider'
            '._asiapay_calculate_signature', return_value='dummy_signature'
        ):
            rendering_values = tx._get_specific_rendering_values(None)
            self.assertDictEqual(
                rendering_values,
                {
                    'amount': tx.amount,
                    'api_url': tx.provider_id._asiapay_get_api_url(),
                    'currency_code': const.CURRENCY_MAPPING[tx.currency_id.name],
                    'language': const.LANGUAGE_CODES_MAPPING['en'],
                    'merchant_id': tx.provider_id.asiapay_merchant_id,
                    'mps_mode': 'SCP',
                    'payment_method': 'ALL',
                    'payment_type': 'N',
                    'reference': tx.reference,
                    'return_url': self._build_url('/payment/asiapay/return'),
                    'secure_hash': 'dummy_signature',
                }
            )

    @mute_logger('odoo.addons.payment.models.payment_transaction')
    def test_no_input_missing_from_redirect_form(self):
        """ Test that no key is omitted from the rendering values. """
        tx = self._create_transaction(flow='redirect')
        expected_input_keys = [
            'merchantId',
            'amount',
            'orderRef',
            'currCode',
            'mpsMode',
            'successUrl',
            'failUrl',
            'cancelUrl',
            'payType',
            'lang',
            'payMethod',
            'secureHash',
        ]
        processing_values = tx._get_processing_values()
        form_info = self._extract_values_from_html_form(processing_values['redirect_form_html'])
        self.assertEqual(form_info['action'], tx.provider_id._asiapay_get_api_url())
        self.assertEqual(form_info['method'], 'post')
        self.assertListEqual(list(form_info['inputs'].keys()), expected_input_keys)

    def test_processing_notification_data_confirms_transaction(self):
        """ Test that the transaction state is set to 'done' when the notification data indicate a
        successful payment. """
        tx = self._create_transaction(flow='redirect')
        tx._process_notification_data(self.webhook_notification_data)
        self.assertEqual(tx.state, 'done')
