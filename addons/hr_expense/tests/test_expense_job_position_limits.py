# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import tagged

from odoo.addons.hr_expense.tests.common import TestExpenseCommon


@tagged('-at_install', 'post_install')
class TestExpenseJobPositionLimits(TestExpenseCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.job_junior = cls.env['hr.job'].sudo().create({'name': 'Junior Consultant'})
        cls.expense_employee.sudo().write({
            'job_id': cls.job_junior.id,
        })

    def _create_limit(self, product=None, jobs=None, amount=100.0, sequence=10):
        return self.env['hr.expense.product.job.position.limit'].create({
            'product_id': (product or self.product_c).id,
            'job_ids': [Command.set(jobs.ids)] if jobs else False,
            'limit_amount': amount,
            'sequence': sequence,
        })

    def test_expense_uses_job_position_specific_limit(self):
        self._create_limit(jobs=self.job_junior, amount=100.0)

        expense = self.create_expenses({
            'product_id': self.product_c.id,
            'total_amount_currency': 150.0,
            'payment_mode': 'own_account',
        })

        self.assertTrue(expense.has_expense_job_position_limit)
        self.assertEqual(expense.expense_job_position_limit_amount, 100.0)
        self.assertEqual(expense.expense_job_position_limit_amount_currency, 100.0)
        self.assertTrue(expense.is_expense_exceeding_job_position_limit)

        employee_expense = expense.with_user(self.expense_user_employee)

        self.assertTrue(employee_expense.is_own_expense)

    def test_expense_uses_limit_matching_any_selected_job_position(self):
        job_senior = self.env['hr.job'].sudo().create({'name': 'Senior Consultant'})
        self._create_limit(jobs=self.job_junior | job_senior, amount=100.0)

        expense = self.create_expenses({
            'product_id': self.product_c.id,
            'total_amount_currency': 150.0,
            'payment_mode': 'own_account',
        })

        self.assertTrue(expense.has_expense_job_position_limit)
        self.assertEqual(expense.expense_job_position_limit_amount, 100.0)
        self.assertTrue(expense.is_expense_exceeding_job_position_limit)

    def test_expense_generic_limit(self):
        self._create_limit(amount=80.0)

        expense = self.create_expenses({
            'product_id': self.product_c.id,
            'total_amount_currency': 100.0,
            'payment_mode': 'own_account',
        })

        self.assertTrue(expense.has_expense_job_position_limit)
        self.assertEqual(expense.expense_job_position_limit_amount, 80.0)
        self.assertTrue(expense.is_expense_exceeding_job_position_limit)

    def test_expense_product_job_position_limit_unique_generic_limit(self):
        self._create_limit(amount=80.0)

        with self.assertRaises(ValidationError):
            self._create_limit(amount=90.0)

    def test_expense_job_position_specific_limit_overrides_generic_limit(self):
        self._create_limit(amount=80.0)
        self._create_limit(jobs=self.job_junior, amount=120.0)

        expense = self.create_expenses({
            'product_id': self.product_c.id,
            'total_amount_currency': 100.0,
            'payment_mode': 'own_account',
        })

        self.assertTrue(expense.has_expense_job_position_limit)
        self.assertEqual(expense.expense_job_position_limit_amount, 120.0)
        self.assertFalse(expense.is_expense_exceeding_job_position_limit)

    def test_expense_uses_first_matching_job_position_limit_by_sequence(self):
        self._create_limit(jobs=self.job_junior, amount=200.0, sequence=20)
        self._create_limit(jobs=self.job_junior, amount=100.0, sequence=10)

        expense = self.create_expenses({
            'product_id': self.product_c.id,
            'total_amount_currency': 150.0,
            'payment_mode': 'own_account',
        })

        self.assertTrue(expense.has_expense_job_position_limit)
        self.assertEqual(expense.expense_job_position_limit_amount, 100.0)
        self.assertTrue(expense.is_expense_exceeding_job_position_limit)

    def test_expense_job_position_limit_ignored_for_company_paid_expense(self):
        self._create_limit(jobs=self.job_junior, amount=100.0)

        expense = self.create_expenses({
            'product_id': self.product_c.id,
            'total_amount_currency': 150.0,
            'payment_mode': 'company_account',
        })

        self.assertFalse(expense.has_expense_job_position_limit)
        self.assertEqual(expense.expense_job_position_limit_amount, 0.0)
        self.assertEqual(expense.expense_job_position_limit_amount_currency, 0.0)
        self.assertFalse(expense.is_expense_exceeding_job_position_limit)

    def test_cap_reimbursement_to_policy(self):
        self._create_limit(jobs=self.job_junior, amount=100.0)

        expense = self.create_expenses({
            'name': 'Breakfast',
            'product_id': self.product_c.id,
            'total_amount_currency': 150.0,
            'payment_mode': 'own_account',
            'analytic_distribution': {self.analytic_account_1.id: 100},
            'tax_ids': [Command.clear()],
        })
        expense.with_user(self.expense_user_employee).action_submit()

        self.assertTrue(expense.is_expense_exceeding_job_position_limit)

        expense.with_user(self.expense_user_manager).action_cap_reimbursement_to_policy()

        split_expenses = self.env['hr.expense'].search([
            ('split_expense_origin_id', '=', expense.id),
        ])
        self.assertEqual(len(split_expenses), 2)

        capped_expense = split_expenses.filtered(
            lambda exp: exp.currency_id.compare_amounts(exp.total_amount_currency, 100.0) == 0
        )
        exceeded_expense = split_expenses.filtered(
            lambda exp: exp.currency_id.compare_amounts(exp.total_amount_currency, 50.0) == 0
        )

        self.assertEqual(capped_expense, expense)
        self.assertRecordValues(capped_expense, [{
            'state': 'approved',
            'total_amount_currency': 100.0,
            'approval_state': 'approved',
        }])
        self.assertRecordValues(exceeded_expense, [{
            'state': 'refused',
            'total_amount_currency': 50.0,
            'approval_state': 'refused',
        }])

    def test_cap_reimbursement_to_policy_does_not_refuse_existing_split_siblings(self):
        self._create_limit(jobs=self.job_junior, amount=60.0)

        expense = self.create_expenses({
            'name': 'Hotel',
            'product_id': self.product_c.id,
            'total_amount_currency': 200.0,
            'payment_mode': 'own_account',
            'analytic_distribution': {self.analytic_account_1.id: 100},
            'tax_ids': [Command.clear()],
        })

        wizard = self.env['hr.expense.split.wizard'].browse(expense.action_split_wizard()['res_id'])
        wizard.action_split_expense()

        split_expenses = self.env['hr.expense'].search([
            ('split_expense_origin_id', '=', expense.id),
        ])
        self.assertEqual(len(split_expenses), 2)

        sibling_expense = split_expenses - expense
        self.assertRecordValues(sibling_expense, [{
            'state': 'draft',
            'total_amount_currency': 100.0,
        }])

        expense.with_user(self.expense_user_employee).action_submit()
        expense.with_user(self.expense_user_manager).action_cap_reimbursement_to_policy()

        all_split_expenses = self.env['hr.expense'].search([
            ('split_expense_origin_id', '=', expense.id),
        ])
        self.assertEqual(len(all_split_expenses), 3)

        exceeded_expense = all_split_expenses.filtered(
            lambda exp: exp != sibling_expense
            and exp.currency_id.compare_amounts(exp.total_amount_currency, 40.0) == 0
        )

        self.assertRecordValues(expense, [{
            'state': 'approved',
            'total_amount_currency': 60.0,
        }])
        self.assertRecordValues(exceeded_expense, [{
            'state': 'refused',
            'total_amount_currency': 40.0,
        }])
        self.assertRecordValues(sibling_expense, [{
            'state': 'draft',
            'total_amount_currency': 100.0,
        }])
