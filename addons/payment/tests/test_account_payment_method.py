# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.payment.tests.common import PaymentCommon


@tagged('post_install', '-at_install')
class TestAccountPaymentMethod(PaymentCommon):

    def test_prevent_unlink_apml_with_active_acquirer(self):
        """ Deleting an account.payment.method.line that is related to a acquirer in 'test' or 'enabled' state
        should raise an error.
        """
        self.assertEqual(self.dummy_acquirer.state, 'test')
        with self.assertRaises(UserError):
            self.dummy_acquirer.journal_id.inbound_payment_method_line_ids.unlink()
