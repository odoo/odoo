# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.tools import mute_logger

from .common import PayumoneyCommon
from ..controllers.main import PayUMoneyController
from odoo.addons.payment import utils as payment_utils


@tagged('post_install', '-at_install')
class PayumoneyTest(PayumoneyCommon):

    def test_compatible_acquirers(self):
        acquirers = self.env['payment.acquirer']._get_compatible_acquirers(
            partner_id=self.partner.id,
            company_id=self.company.id,
            currency_id=self.currency.id,
        )
        self.assertIn(self.payumoney, acquirers)

        acquirers = self.env['payment.acquirer']._get_compatible_acquirers(
            partner_id=self.partner.id,
            company_id=self.company.id,
            currency_id=self.currency_euro.id,
        )
        self.assertNotIn(self.payumoney, acquirers)

    def test_redirect_form_values(self):
        tx = self.create_transaction(flow='redirect')
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
