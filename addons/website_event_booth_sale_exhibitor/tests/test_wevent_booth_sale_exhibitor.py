# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.account_payment.tests.common import AccountPaymentFlowCommon
from odoo.addons.website_event_booth_exhibitor.tests import test_wevent_booth_exhibitor


@tagged('post_install', '-at_install')
class TestWEventBoothSaleExhibitor(
    test_wevent_booth_exhibitor.TestWEventBoothExhibitorCommon, AccountPaymentFlowCommon
):

    def test_register(self):
        self._enable_complete_payment_flow()
        self._register_booth()
