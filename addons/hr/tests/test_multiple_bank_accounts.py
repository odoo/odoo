# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import HttpCase, tagged
from odoo.addons.hr.tests.common import TestHrCommon


@tagged('-at_install', 'post_install')
class TestEmployeeMultipleBanksUi(HttpCase):
    def test_employee_profile_tour(self):
        employee = self.env['hr.employee'].create({
            'name': 'Johnny H.',
        })
        self.start_tour("/odoo", 'hr_employee_multiple_bank_accounts_tour', login="admin", timeout=200)
        total = 0
        for ba in employee.bank_account_ids:
            ba_percentage = employee.salary_distribution[str(ba.id)]['amount']
            ba_is_percentage = employee.salary_distribution[str(ba.id)]['amount_is_percentage']
            self.assertEqual(ba_is_percentage, True)
            self.assertAlmostEqual(ba_percentage, 33.33, delta=0.011)
            total += ba_percentage
        self.assertAlmostEqual(total, 100.0, "Total must amount to 100.")


@tagged('-at_install', 'post_install')
class TestBankAccountAllocationWizard(TestHrCommon):
    def test_trust_bank_account_requires_rights(self):
        if 'account.move' not in self.env:
            self.skipTest("account is not installed")
        bank_account = self.env['res.partner.bank'].create({
            'acc_number': 'BE1234567890',
            'partner_id': self.employee.work_contact_id.id,
        })
        self.employee.bank_account_ids = [Command.link(bank_account.id)]
        wizard = self.env['hr.bank.account.allocation.wizard'].with_user(self.res_users_hr_officer).create({
            'employee_id': self.employee.id,
        })
        wizard.action_save()  # no trust change: allowed

        wizard.allocation_ids.trusted = True
        with self.assertRaises(UserError):
            wizard.action_save()
