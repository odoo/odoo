# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.payment_sepa_direct_debit.tests.common import SepaDirectDebitCommon


@tagged('-at_install', 'post_install')
class TestPaymentToken(SepaDirectDebitCommon):

    def test_display_name_is_bank_account(self):
        """ Test that the display name is the full bank account without padding. """
        token = self._create_token(payment_details='BE01 2345 67890 1234')
        self.assertEqual(token._build_display_name(), 'BE01 2345 67890 1234')
