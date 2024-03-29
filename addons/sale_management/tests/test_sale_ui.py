# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests.common import tagged, HttpCase


@tagged('post_install', '-at_install')
class TestUi(AccountTestInvoicingCommon, HttpCase):

    def test_01_sale_tour(self):
        self.start_tour("/web", 'sale_tour', login="admin", step_delay=100)

    def test_02_sale_tour_company_onboarding_done(self):
        self.env["onboarding.onboarding.step"].action_validate_step("account.onboarding_onboarding_step_company_data")
        self.start_tour("/web", "sale_tour", login="admin", step_delay=100)

    def test_03_sale_quote_tour(self):
        self.env['res.partner'].create({'name': 'Agrolait', 'email': 'agro@lait.be'})
        self.start_tour("/web", 'sale_quote_tour', login="admin", step_delay=100)
