# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.payment_razorpay.tests.common import RazorpayCommon


@tagged('post_install', '-at_install')
class TestPaymentAcquirer(RazorpayCommon):

    def test_incompatible_with_unsupported_currencies(self):
        """ Test that Razorpay acquirers are filtered out from compatible acquirers when the
        currency is not supported. """
        compatible_acquirers = self.env['payment.acquirer']._get_compatible_acquirers(
            self.company_id, self.partner.id, self.amount, currency_id=self.env.ref('base.AFN').id
        )
        self.assertNotIn(self.acquirer, compatible_acquirers)

    def test_signature_calculation_for_redirect_data(self):
        """ Test that the calculated signature matches the expected signature for redirect data. """
        calculated_signature = self.acquirer._razorpay_calculate_signature(
            self.redirect_notification_data, is_redirect=True
        )
        self.assertEqual(
            calculated_signature, '437b72e4e87362a39951b44487cf698410b074afdbed19ec44fffd32d2f863f3'
        )

    def test_neutralize(self):
        """ Test that the sensitive fields of the acquirer are correctly neutralized. """
        self.env['payment.acquirer']._neutralize()
        self.assertFalse(self.acquirer.razorpay_key_id)
        self.assertFalse(self.acquirer.razorpay_key_secret)
        self.assertFalse(self.acquirer.razorpay_webhook_secret)
