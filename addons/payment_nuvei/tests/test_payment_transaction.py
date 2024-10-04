# Part of Odoo. See LICENSE file for full copyright and licensing details.
from unittest.mock import patch

from werkzeug import urls

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment import utils as payment_utils

from odoo.addons.payment_nuvei.controllers.main import NuveiController
from odoo.addons.payment_nuvei.tests.common import NuveiCommon


@tagged('post_install', '-at_install')
class TestPaymentTransaction(NuveiCommon):

    def _get_expected_values(self, tx):
        return_url = self._build_url(NuveiController._return_url)
        first_name, last_name = payment_utils.split_partner_name(tx.partner_name)

        webhook_url = self._build_url(NuveiController._webhook_url)
        cancel_url = self._build_url(NuveiController._cancel_url)
        cancel_url_params = {
            'tx_ref': tx.reference,
            'return_access_tkn': self._generate_test_access_token(tx.reference),
        }
        return {
            'address1': tx.partner_address,
            'city': tx.partner_city,
            'country': tx.partner_country_id.code,
            'currency': tx.currency_id.name,
            'email': tx.partner_email,
            'first_name': first_name,
            'item_amount_1': tx.amount,
            'item_name_1': tx.reference,
            'item_quantity_1': 1,
            'invoice_id': tx.reference,
            'last_name': last_name,
            'merchantLocale': tx.partner_lang,
            'merchant_id': self.provider.nuvei_merchant_identifier,
            'merchant_site_id': self.provider.nuvei_site_identifier,
            'payment_method_mode': 'filter',
            'payment_method': 'unknown',
            'phone1': tx.partner_phone,
            'time_stamp': tx.create_date.strftime('%Y-%m-%d.%H:%M:%S'),
            'total_amount': self.amount,
            'user_token_id': f'{tx.partner_id.id}|{tx.partner_name}',
            'version': '4.0.0',
            'zip': tx.partner_zip,
            'notify_url': webhook_url,
            'success_url': return_url,
            'error_url': return_url,
            'pending_url': return_url,
            'back_url': f'{cancel_url}?{urls.url_encode(cancel_url_params)}',
        }

    def test_no_item_missing_from_rendering_values(self):
        """ Test that the rendered values are conform to the transaction fields. """

        tx = self._create_transaction(flow='redirect')
        with patch(
            'odoo.addons.payment.utils.generate_access_token', new=self._generate_test_access_token
        ):
            processing_values = tx._get_specific_rendering_values(None)
        expected_values = self._get_expected_values(tx)
        self.assertDictEqual(processing_values['url_params'], expected_values)

    @mute_logger('odoo.addons.payment.models.payment_transaction')
    def test_no_input_missing_from_redirect_form(self):
        """ Test that the no key is not omitted from the rendering values. """
        tx = self._create_transaction(flow='redirect')
        expected_input_keys = [
            'checksum',
            'address1',
            'city',
            'country',
            'currency',
            'email',
            'first_name',
            'item_amount_1',
            'item_name_1',
            'item_quantity_1',
            'invoice_id',
            'last_name',
            'merchantLocale',
            'merchant_id',
            'merchant_site_id',
            'payment_method_mode',
            'payment_method',
            'phone1',
            'time_stamp',
            'total_amount',
            'user_token_id',
            'version',
            'zip',
            'notify_url',
            'success_url',
            'error_url',
            'pending_url',
            'back_url',
        ]
        expected_input_keys.sort()
        with patch(
            'odoo.addons.payment.utils.generate_access_token', new=self._generate_test_access_token
        ):
            processing_values = tx._get_processing_values()

        form_info = self._extract_values_from_html_form(processing_values['redirect_form_html'])
        self.assertEqual(form_info['action'], 'https://ppp-test.safecharge.com/ppp/purchase.do')
        self.assertEqual(form_info['method'], 'post')
        input_keys = list(form_info['inputs'].keys())
        input_keys.sort()
        self.assertListEqual(input_keys, expected_input_keys)

    def test_processing_notification_data_confirms_transaction(self):
        """ Test that the transaction state is set to 'done' when the notification data indicate a
        successful payment. """
        tx = self._create_transaction(flow='redirect')
        tx._process_notification_data(self.notification_data)
        self.assertEqual(tx.state, 'done')
