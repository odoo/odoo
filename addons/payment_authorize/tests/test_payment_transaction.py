# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.payment_authorize.tests.common import AuthorizeCommon


@tagged('post_install', '-at_install')
class TestPaymentTransaction(AuthorizeCommon):

    def test_search_by_reference_finds_transaction_from_webhook_data(self):
        """Test that a transaction is correctly found from webhook data using invoiceNumber."""
        tx = self._create_transaction('direct')
        found_tx = self.env['payment.transaction']._search_by_reference(
            'authorize', self.webhook_authcapture_data
        )
        self.assertEqual(tx, found_tx)
