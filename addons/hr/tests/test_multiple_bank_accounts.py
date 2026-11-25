# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.exceptions import ValidationError
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
class TestEmployeeBankAccount(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.country_id = cls.env.ref('base.us')
        cls.employee = cls.env['hr.employee'].create({'name': 'Paul'})
        cls.partner = cls.employee.work_contact_id

    def _create_account(self, account_number, partner=None):
        return self.env['res.partner.bank'].create({
            'account_number': account_number,
            'partner_id': (partner or self.partner).id,
        })

    def test_wrong_iban_refused(self):
        for account_number in (
            'BE68539007547035',  # wrong check digits
            'BE6853900754703',  # wrong length
            'BE12',
        ):
            with self.subTest(account_number=account_number), \
                    self.assertRaisesRegex(ValidationError, "The bank account of an employee must be a valid IBAN."):
                self._create_account(account_number)

    def test_other_account_numbers_accepted(self):
        for account_number in (
            'BE68 5390 0754 7034',  # valid IBAN
            'MA64 0115 1900 0001 2050 0053 4921',  # IBAN of a country without IBAN template
            '123456789',  # national number: checked by the payment reports
            '001-0514981-84',  # old Belgian number: refused by the Belgian localization only
        ):
            with self.subTest(account_number=account_number):
                self.assertTrue(self._create_account(account_number))

    def test_wrong_iban_of_another_partner_accepted(self):
        partner = self.env['res.partner'].create({'name': 'Not an employee'})
        self.assertTrue(self._create_account('BE68539007547035', partner))

    def test_edit_account_number(self):
        account = self._create_account('BE68539007547034')
        self.employee.bank_account_ids = [Command.link(account.id)]
        with self.assertRaisesRegex(ValidationError, "must be a valid IBAN"):
            account.account_number = 'BE68539007547035'

    def test_link_wrong_iban_to_employee(self):
        """An account created without the employee is checked once linked to the employee."""
        partner = self.env['res.partner'].create({'name': 'Joint account'})
        account = self._create_account('BE68539007547035', partner)
        with self.assertRaisesRegex(ValidationError, "must be a valid IBAN"):
            self.employee.bank_account_ids = [Command.link(account.id)]
        with self.assertRaisesRegex(ValidationError, "must be a valid IBAN"):
            self.env['hr.employee'].create({'name': 'Amina', 'bank_account_ids': [Command.link(account.id)]})

    def test_older_wrong_account_does_not_block(self):
        """Adding the right account of an employee is not blocked by the wrong one it replaces."""
        old_account = self._create_account('BE68539007547034')
        self.employee.bank_account_ids = [Command.link(old_account.id)]
        # an account entered before the check
        self.env.cr.execute("UPDATE res_partner_bank SET account_number = 'BE68539007547035' WHERE id = %s", [old_account.id])
        old_account.invalidate_recordset(['account_number'])
        new_account = self._create_account('BE71 0961 2345 6769')
        self.employee.bank_account_ids = [Command.link(new_account.id)]
        self.assertEqual(self.employee.bank_account_ids, old_account | new_account)

    def test_looks_like_iban(self):
        bank = self.env['res.partner.bank']
        self.assertTrue(bank._looks_like_iban('BE68 5390 0754 7034'))
        self.assertTrue(bank._looks_like_iban('MA64 0115 1900 0001 2050 0053 4921'))
        self.assertFalse(bank._looks_like_iban('MA65 0115 1900 0001 2050 0053 4921'))
        self.assertFalse(bank._looks_like_iban('001-0514981-84'))
        self.assertFalse(bank._looks_like_iban(False))


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

    def test_removing_the_percentage_account_keeps_a_valid_split(self):
        bank_x, bank_y = self.bank_accounts
        bank_z = self.env['res.partner.bank'].create({
            'account_number': 'BE62510007547061',
            'partner_id': self.employee.work_contact_id.id,
        })
        self.employee.bank_account_ids = [Command.set((self.bank_accounts + bank_z).ids)]
        self.employee.salary_distribution = {
            str(bank_y.id): {'sequence': 1, 'amount': 400.0, 'amount_is_percentage': False},
            str(bank_x.id): {'sequence': 2, 'amount': 300.0, 'amount_is_percentage': False},
            str(bank_z.id): {'sequence': 3, 'amount': 100.0, 'amount_is_percentage': True},
        }
        # Z is closed: X, the last account of the Salary Allocation, now gets the rest of the salary.
        bank_z.action_archive()
        self.assertEqual(self.employee.salary_distribution, {
            str(bank_y.id): {'sequence': 1, 'amount': 400.0, 'amount_is_percentage': False},
            str(bank_x.id): {'sequence': 2, 'amount': 100.0, 'amount_is_percentage': True},
        })
