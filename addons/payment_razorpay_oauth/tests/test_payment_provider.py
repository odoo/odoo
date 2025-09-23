# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.exceptions import ValidationError

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
