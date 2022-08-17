# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment_aps.controllers.main import APSController
from odoo.addons.payment_aps.tests.common import APSCommon


@tagged('post_install', '-at_install')
class TestPaymentTransaction(APSCommon):

    def test_reference_contains_only_valid_characters(self):
        """ Test that transaction references are made of only alphanumerics and/or '-' and '_'. """
        for prefix in (None, '', 'S0001', 'INV/20222/001', 'dummy ref'):
            reference = self.env['payment.transaction']._compute_reference('aps', prefix=prefix)
            self.assertRegex(reference, r'^[\w-]+$')

    def test_no_item_missing_from_rendering_values(self):
        """ Test that the rendered values are conform to the transaction fields. """
        tx = self._create_transaction(flow='redirect')

        converted_amount = payment_utils.to_minor_currency_units(self.amount, self.currency)
        expected_values = {
            'command': 'PURCHASE',
            'access_code': self.provider.aps_access_code,
            'merchant_identifier': self.provider.aps_merchant_identifier,
            'merchant_reference': tx.reference,
            'amount': str(converted_amount),
            'currency': self.currency.name,
            'language': tx.partner_lang[:2],
            'customer_email': tx.partner_id.email_normalized,
            'return_url': self._build_url(APSController._return_url),
            'signature': '8f4e295359a578f05fdc6c275829128e7b93440e6c7d13179c1e16cc579c6111',
            'api_url': self.provider._aps_get_api_url(),
        }
        self.assertDictEqual(tx._get_specific_rendering_values(None), expected_values)

    @mute_logger('odoo.addons.payment.models.payment_transaction')
    def test_no_input_missing_from_redirect_form(self):
        """ Test that the no key is not omitted from the rendering values. """
        tx = self._create_transaction(flow='redirect')
        expected_input_keys = [
            'command',
            'access_code',
            'merchant_identifier',
            'merchant_reference',
            'amount',
            'currency',
            'language',
            'customer_email',
            'signature',
            'return_url',
        ]
        processing_values = tx._get_processing_values()
        form_info = self._extract_values_from_html_form(processing_values['redirect_form_html'])
        self.assertEqual(form_info['action'], 'https://sbcheckout.payfort.com/FortAPI/paymentPage')
        self.assertEqual(form_info['method'], 'post')
        self.assertListEqual(list(form_info['inputs'].keys()), expected_input_keys)

    def test_processing_notification_data_confirms_transaction(self):
        """ Test that the transaction state is set to 'done' when the notification data indicate a
        successful payment. """
        tx = self._create_transaction(flow='redirect')
        tx._process_notification_data(self.notification_data)
        self.assertEqual(tx.state, 'done')
