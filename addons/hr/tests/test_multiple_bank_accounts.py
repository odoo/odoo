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
