# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.payment_flutterwave.tests.common import FlutterwaveCommon


@tagged('post_install', '-at_install')
class TestPaymentAcquirer(FlutterwaveCommon):

    def test_incompatible_with_unsupported_currencies(self):
        compatible_acquirers = self.env['payment.acquirer']._get_compatible_acquirers(
            self.company_id, self.partner.id, self.amount, currency_id=self.env.ref('base.AFN').id
        )
        self.assertNotIn(self.flutterwave, compatible_acquirers)

    def test_incompatible_with_validation_transactions(self):
        compatible_acquirers = self.env['payment.acquirer']._get_compatible_acquirers(
            self.company_id, self.partner.id, 0., is_validation=True
        )
        self.assertNotIn(self.flutterwave, compatible_acquirers)

    def test_neutralize(self):
        self.env['payment.acquirer']._neutralize()
        self.assertEqual(self.acquirer.flutterwave_public_key, False)
        self.assertEqual(self.acquirer.flutterwave_secret_key, False)
        self.assertEqual(self.acquirer.flutterwave_webhook_secret, False)
