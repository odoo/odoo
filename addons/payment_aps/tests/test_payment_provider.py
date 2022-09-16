# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.payment_aps.tests.common import APSCommon


@tagged('post_install', '-at_install')
class TestPaymentProvider(APSCommon):

    def test_neutralize(self):
        self.env['payment.provider']._neutralize()
        self.assertEqual(self.provider.aps_merchant_identifier, False)
        self.assertEqual(self.provider.aps_access_code, False)
        self.assertEqual(self.provider.aps_sha_request, False)
        self.assertEqual(self.provider.aps_sha_response, False)
