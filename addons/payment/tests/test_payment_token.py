# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.payment.tests.common import PaymentCommon


@tagged('-at_install', 'post_install')
class TestPaymentToken(PaymentCommon):

    def test_token_cannot_be_unarchived(self):
        """ Test that unarchiving disabled tokens is forbidden. """
        token = self._create_token(active=False)
        with self.assertRaises(UserError):
            token.active = True
