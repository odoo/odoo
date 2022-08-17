# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.payment_razorpay.tests.common import RazorpayCommon


@tagged('post_install', '-at_install')
class TestPaymentProvider(RazorpayCommon):

    def test_incompatible_with_unsupported_currencies(self):
        """ Test that Razorpay providers are filtered out from compatible providers when the
        currency is not supported. """
        compatible_providers = self.env['payment.provider']._get_compatible_providers(
            self.company_id, self.partner.id, self.amount, currency_id=self.env.ref('base.AFN').id
        )
        self.assertNotIn(self.provider, compatible_providers)

    def test_signature_calculation_for_redirect_data(self):
        """ Test that the calculated signature matches the expected signature for redirect data. """
        calculated_signature = self.provider._razorpay_calculate_signature(
            self.redirect_notification_data, is_redirect=True
        )
        self.assertEqual(
            calculated_signature, '437b72e4e87362a39951b44487cf698410b074afdbed19ec44fffd32d2f863f3'
        )

    def test_neutralize(self):
        """ Test that the sensitive fields of the provider are correctly neutralized. """
        self.env['payment.provider']._neutralize()
        self.assertFalse(self.provider.razorpay_key_id)
        self.assertFalse(self.provider.razorpay_key_secret)
        self.assertFalse(self.provider.razorpay_webhook_secret)
