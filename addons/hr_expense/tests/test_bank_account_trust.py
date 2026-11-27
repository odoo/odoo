# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import Form, TransactionCase, new_test_user


class TestBankAccountTrust(TransactionCase):
    """ Lives here as _user_can_trust() only checks the group once account is installed. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.hr_officer = new_test_user(cls.env, login='hr_officer', groups='hr.group_hr_user')
        cls.accountant = new_test_user(cls.env, login='accountant', groups='hr.group_hr_user,account.group_validate_bank_account')
        cls.employee = cls.env['hr.employee'].create({'name': 'Employee'})
        cls.employee.bank_account_ids = [Command.create({
            'account_number': 'BE68539007547034',
            'partner_id': cls.employee.work_contact_id.id,
        })]

    def _get_trust_forms(self, user):
        wizard = self.env['hr.bank.account.allocation.wizard'].with_user(user).create({
            'employee_id': self.employee.id,
        })
        return Form(self.employee.with_user(user)), Form(wizard).allocation_ids.edit(0)

    def test_trust_toggles_readonly_without_validation_rights(self):
        employee_form, line_form = self._get_trust_forms(self.hr_officer)
        with self.assertRaises(AssertionError):
            employee_form.is_trusted_bank_account = True
        with self.assertRaises(AssertionError):
            line_form.trusted = True

    def test_trust_toggles_with_validation_rights(self):
        employee_form, line_form = self._get_trust_forms(self.accountant)
        employee_form.is_trusted_bank_account = True
        line_form.trusted = True
