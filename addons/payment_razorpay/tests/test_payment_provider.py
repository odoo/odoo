# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import ValidationError
from odoo.tests import tagged

from odoo.addons.payment_razorpay.tests.common import RazorpayCommon


@tagged('post_install', '-at_install')
class TestPaymentProvider(RazorpayCommon):

    def test_allow_enabling_if_credentials_are_set(self):
        """ Test that enabling a Razorpay provider with credentials succeeds. """
        self._assert_does_not_raise(ValidationError, self.provider.write({'state': 'enabled'}))

    def test_prevent_enabling_if_credentials_are_not_set(self):
        """ Test that enabling a Razorpay provider without credentials raises a ValidationError. """
        self.provider.write({
            'razorpay_key_id': None,
            'razorpay_key_secret': None,
        })
        with self.assertRaises(ValidationError):
            self.provider.state = 'enabled'

    def test_incompatible_with_unsupported_currencies(self):
        """ Test that Razorpay providers are filtered out from compatible providers when the
        currency is not supported. """
        compatible_providers = self.env['payment.provider']._get_compatible_providers(
            self.company_id, self.partner.id, self.amount, currency_id=self.env.ref('base.AFN').id
        )
        self.assertNotIn(self.provider, compatible_providers)

    def test_razorpay_proxy_version_for_access_token(self):
        """Ensure that RazorPay access-token related endpoints are routed
        through proxy v2."""
        url = self.provider._build_request_url('/get_access_token', is_proxy_request=True)
        self.assertIn('/2/get_access_token', url)

    def test_razorpay_proxy_version_for_other_endpoints(self):
        """Ensure that non-token related RazorPay endpoints still use proxy v1."""
        url = self.provider._build_request_url('/payments', is_proxy_request=True)
        self.assertIn('/1/payments', url)
