# -*- coding: utf-8 -*-
import psycopg2

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger


@tagged('post_install', '-at_install')
class TestAnalyticPlanOperations(TransactionCase):
    def test_delete_plan(self):
        plan = self.env['account.analytic.plan'].create({'name': 'Test Plan'})
        column = plan._column_name()

        # columns exists
        self.env.cr.execute(f"SELECT {column} FROM account_analytic_line LIMIT 1")

        plan.unlink()
        with self.assertRaises(psycopg2.errors.UndefinedColumn), mute_logger('odoo.sql_db'):
            # column has been deleted
            self.env.cr.execute(f"SELECT {column} FROM account_analytic_line LIMIT 1")

    def test_delete_plan_with_view(self):
        plan = self.env['account.analytic.plan'].create({'name': 'Test Plan'})
        column = plan._column_name()

        self.env['ir.ui.view'].create({
            'name': 'Manual view',
            'model': 'account.analytic.line',
            'type': 'search',
            'arch': f'<search><field name="{column}"/></search>',
        })

        # can't delete a plan still used in a view
        with self.assertRaisesRegex(UserError, 'still present in views'):
            plan.unlink()

    def test_validate_deleted_account(self):
        plan, mandatory_plan = self.env['account.analytic.plan'].create([{
            'name': 'Test Plan',
        }, {
            'name': 'Mandatory Plan',
            'default_applicability': 'mandatory',
        }])
        test_account, mandatory_account = self.env['account.analytic.account'].create([{
            'name': 'Test Account',
            'code': 'TAC',
            'plan_id': plan.id,
        }, {
            'name': 'Mandatory Account',
            'code': 'manda',
            'plan_id': mandatory_plan.id,
        }])
        distribution_model = self.env['account.analytic.distribution.model'].create({}).with_context(validate_analytic=True)

        # the configuration makes it raise an error
        distribution_model.analytic_distribution = {f"{test_account.id}": 100}
        with self.assertRaisesRegex(UserError, r'require a 100% analytic distribution'):
            distribution_model._validate_distribution()

        # once it is fixed, the error is not raised anymore
        distribution_model.analytic_distribution = {f"{test_account.id},{mandatory_account.id}": 100}
        distribution_model._validate_distribution()

        # even by keeping a deleted account, the validation still works
        test_account.unlink()
        plan.unlink()
        distribution_model._validate_distribution()
