# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import Forbidden

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_payumoney.controllers.main import PayUMoneyController
from odoo.addons.payment_payumoney.tests.common import PayumoneyCommon


@tagged('post_install', '-at_install')
class PayUMoneyTest(PayumoneyCommon, PaymentHttpCommon):

    def test_compatible_providers(self):
        providers = self.env['payment.provider']._get_compatible_providers(
            self.company.id, self.partner.id, self.amount, currency_id=self.currency.id
        )
        self.assertIn(self.payumoney, providers)

        providers = self.env['payment.provider']._get_compatible_providers(
            self.company.id, self.partner.id, self.amount, currency_id=self.currency_euro.id
        )
        self.assertNotIn(self.payumoney, providers)

    def test_redirect_form_values(self):
        tx = self._create_transaction(flow='redirect')
        with mute_logger('odoo.addons.payment.models.payment_transaction'):
            processing_values = tx._get_processing_values()

        form_info = self._extract_values_from_html_form(processing_values['redirect_form_html'])
        first_name, last_name = payment_utils.split_partner_name(self.partner.name)
        return_url = self._build_url(PayUMoneyController._return_url)
        expected_values = {
            'key': self.payumoney.payumoney_merchant_key,
            'txnid': self.reference,
            'amount': str(self.amount),
            'productinfo': self.reference,
            'firstname': first_name,
            'lastname': last_name,
            'email': self.partner.email,
            'phone': self.partner.phone,
            'surl': return_url,
            'furl': return_url,
            'service_provider': 'payu_paisa',
        }
        expected_values['hash'] = self.payumoney._payumoney_generate_sign(
            expected_values, incoming=False,
        )
        self.assertEqual(form_info['action'],
            'https://sandboxsecure.payu.in/_payment')
        self.assertDictEqual(form_info['inputs'], expected_values,
            "PayUMoney: invalid inputs specified in the redirect form.")

    def test_accept_notification_with_valid_signature(self):
        """ Test the verification of a notification with a valid signature. """
        tx = self._create_transaction('redirect')
        self._assert_does_not_raise(
            Forbidden,
            PayUMoneyController._verify_notification_signature,
            self.notification_data,
            tx,
        )

    @mute_logger('odoo.addons.payment_payumoney.controllers.main')
    def test_reject_notification_with_missing_signature(self):
        """ Test the verification of a notification with a missing signature. """
        tx = self._create_transaction('redirect')
        payload = dict(self.notification_data, hash=None)
        self.assertRaises(
            Forbidden, PayUMoneyController._verify_notification_signature, payload, tx
        )

    @mute_logger('odoo.addons.payment_payumoney.controllers.main')
    def test_reject_notification_with_invalid_signature(self):
        """ Test the verification of a notification with an invalid signature. """
        tx = self._create_transaction('redirect')
        payload = dict(self.notification_data, hash='dummy')
        self.assertRaises(
            Forbidden, PayUMoneyController._verify_notification_signature, payload, tx
        )
