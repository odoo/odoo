# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import HttpCase, TransactionCase, tagged


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


@tagged('post_install', '-at_install')
class TestBankAccountEmployeeId(TransactionCase):

    def test_employee_id_matches_bank_account_ids_not_just_partner(self):
        employee = self.env['hr.employee'].create({'name': 'Bugs Bunny'})
        partner = employee.work_contact_id

        registered_account = self.env['res.partner.bank'].create({
            'acc_number': 'BE10000000000TEST1',
            'partner_id': partner.id,
        })
        unregistered_account = self.env['res.partner.bank'].create({
            'acc_number': 'BE10000000000TEST2',
            'partner_id': partner.id,
        })
        employee.bank_account_ids = [Command.set([registered_account.id])]

        self.assertEqual(
            registered_account.employee_id, employee,
            "A bank account that is in the employee's bank_account_ids should resolve employee_id to that employee.",
        )
        self.assertFalse(
            unregistered_account.employee_id,
            "A bank account that merely shares the employee's partner, but was never added to "
            "bank_account_ids, must not resolve employee_id to that employee.",
        )

        Bank = self.env['res.partner.bank']
        self.assertEqual(
            Bank.search([('employee_id', '=', employee.id)]), registered_account,
            "Searching on employee_id must return the same accounts that reading employee_id agrees with.",
        )
