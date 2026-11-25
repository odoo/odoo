# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import ValidationError
from odoo.fields import Command
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


class TestSalaryDistribution(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = cls.env['hr.employee'].create({'name': 'Johnny H.'})
        cls.bank_accounts = cls.env['res.partner.bank'].create([{
            'account_number': number,
            'partner_id': cls.employee.work_contact_id.id,
        } for number in ('BE71096123456769', 'BE68539007547034')])

    def test_split_checked_on_save(self):
        self.employee.bank_account_ids = [Command.set(self.bank_accounts.ids)]
        wizard = self.env['hr.bank.account.allocation.wizard'].create({'employee_id': self.employee.id})
        line_x, line_y = wizard.allocation_ids
        line_y.write({'amount': 400, 'amount_type': 'fixed'})
        line_x.write({'amount': 300, 'amount_type': 'fixed'})
        with self.assertRaisesRegex(ValidationError, "At least one bank account must receive a percentage of the remaining salary."):
            wizard.action_save()
        line_y.amount = 0
        line_x.write({'amount': 100, 'amount_type': 'percentage'})
        with self.assertRaisesRegex(ValidationError, "Each fixed amount must be greater than 0."):
            wizard.action_save()

    def test_fixed_amounts_follow_the_allocation_order(self):
        # X is the first bank account, but Y comes first in the Salary Allocation.
        bank_x, bank_y = self.bank_accounts
        bank_z = self.env['res.partner.bank'].create({
            'account_number': 'BE62510007547061',
            'partner_id': self.employee.work_contact_id.id,
        })
        self.employee.bank_account_ids = [Command.set((self.bank_accounts + bank_z).ids)]
        wizard = self.env['hr.bank.account.allocation.wizard'].create({'employee_id': self.employee.id})
        lines = wizard.allocation_ids.grouped('bank_account_id')
        lines[bank_y].write({'sequence': 1, 'amount': 400, 'amount_type': 'fixed'})
        lines[bank_x].write({'sequence': 2, 'amount': 300, 'amount_type': 'fixed'})
        lines[bank_z].write({'sequence': 3, 'amount': 100, 'amount_type': 'percentage'})
        wizard.action_save()
        self.assertEqual(self.employee.get_accounts_with_fixed_allocations().ids, [bank_y.id, bank_x.id])
