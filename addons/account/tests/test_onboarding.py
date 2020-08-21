# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests
from odoo.addons.account.tests.common import AccountTestInvoicingHttpCommon


@odoo.tests.tagged('post_install', '-at_install')
class TestUi(AccountTestInvoicingHttpCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='installed'):
        super().setUpClass(chart_template_ref)

    def test_01_account_tour(self):
        # This tour doesn't work with demo data on runbot
        self.start_tour("/web", 'account_tour', login="accountman")
