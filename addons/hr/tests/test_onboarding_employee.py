# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import HttpCase, tagged, users


@tagged('-at_install', 'post_install')
class TestOnboardingEmployee(HttpCase):
    @users('admin')
    def test_load_sample_data(self):
        """ Assert that the 'Load sample button' of the onboarding action helper is displayed and works
            It should only be displayed when on 'base.main_company', when the sample data have not been loaded
            and when the company still doesn't contain any employee
        """
        self.assertFalse(self.env['hr.employee'].has_demo_data(), "This test should be run when sample data still haven't been loaded")

        self.start_tour('/odoo', 'load_employee_sample_data_tour', login=self.env.user.login)
        employees = self.env["hr.employee"].search([['company_id', '=', self.env.ref('base.main_company').id]])
        self.assertEqual(len(employees), 3, "The 3 sample employees should've been loaded.")
