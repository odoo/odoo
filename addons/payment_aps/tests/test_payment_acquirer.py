# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.payment_aps.tests.common import APSCommon


@tagged('post_install', '-at_install')
class TestPaymentAcquirer(APSCommon):

    def test_neutralize(self):
        self.env['payment.acquirer']._neutralize()
        self.assertEqual(self.acquirer.aps_merchant_identifier, False)
        self.assertEqual(self.acquirer.aps_access_code, False)
        self.assertEqual(self.acquirer.aps_sha_request, False)
        self.assertEqual(self.acquirer.aps_sha_response, False)
