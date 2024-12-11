from odoo.tests import tagged, HttpCase
from odoo import tools
@tagged('post_install', '-at_install')
class TestOnboardingToursOnRunbot(HttpCase):

    @tools.mute_logger('odoo.http')
    def test_onboarding_tours_on_runbot(self):
        if self.env['ir.module.module']._get('account_accountant').state != 'installed':
            self.skipTest("account_accountant module is not installed")
        domain = [("name", "not in", (
            "purchase_tour", #bug
            "hr_expense_extract_tour", #scenario not works
        ))]
        # domain = [("name", "=", "hr_expense_extract_tour")]
        # domain = []
        tours = self.env['web_tour.tour'].search(domain)	
        for tour in tours:
            self.start_tour(tour.url, tour.name, login='admin')
