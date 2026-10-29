# Part of Odoo. See LICENSE file for full copyright and licensing details.
import unittest
from datetime import datetime
from functools import wraps

from odoo import Command

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.product.tests.common import ProductCommon


def account_less_only(func):
    """ Skip a test of the flows without accounting when `account_hr_expense` is installed, as it extends them. The same
    flows are tested in `account_hr_expense` with the accounting entries.
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if self.env['ir.module.module']._get('account_hr_expense').state == 'installed':
            raise unittest.SkipTest("The flow is extended by account_hr_expense")
        return func(self, *args, **kwargs)
    return wrapper


class TestExpenseCommon(ProductCommon):
    """ Common fixtures of the expenses, without any accounting: this works without `account` installed.
    The accounting tests use `TestAccountExpenseCommon` of `account_hr_expense`, which adds the accounting fixtures on top.
    """

    _test_user_groups = None  # FIXME list needed groups

    @classmethod
    def setup_independent_company(cls, name='company_1_data', **create_values):
        # A company of its own, the main one holds the demo employees and currency rates (as the accounting common does)
        if cls._test_independent_company_xmlid:
            return cls.env.ref(cls._test_independent_company_xmlid)
        company = cls._create_company(name=name, **create_values)
        if 'account.chart.template' in cls.env:
            # With accounting installed (e.g. account_hr_expense), approving creates entries: the company needs a chart
            cls.env['account.chart.template'].try_loading('generic_coa', company=company, install_demo=False)  # noqa: OLS03001
        return company

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company_2 = cls._create_company(name='company_2')
        cls.other_currency = cls.setup_other_currency('HRK', rates=[
            ('1900-01-01', 1.0),
            ('2015-12-31', 3.0),
            ('2016-12-31', 2.0),
        ])

        group_expense_manager = cls.env.ref('hr_expense.group_hr_expense_manager')

        cls.expense_user_employee = mail_new_test_user(
            cls.env,
            name='expense_user_employee',
            login='expense_user_employee',
            email='expense_user_employee@example.com',
            notification_type='email',
            groups='base.group_user',
            company_ids=[Command.set(cls.env.companies.ids)],
        )
        cls.expense_user_manager = mail_new_test_user(
            cls.env,
            name='Expense manager',
            login='expense_manager_1',
            email='expense_manager_1@example.com',
            notification_type='email',
            groups='base.group_user,hr_expense.group_hr_expense_manager',
            company_ids=[Command.set(cls.env.companies.ids)],
        )

        cls.expense_user_manager_2 = mail_new_test_user(
            cls.env,
            name='Expense manager',
            login='expense_manager_2',
            email='expense_manager_2@example.com',
            notification_type='email',
            groups='base.group_user,hr_expense.group_hr_expense_manager',
            company_ids=[Command.set(cls.env.companies.ids)],
        )

        cls.expense_employee = cls.env['hr.employee'].sudo().create({
            'name': 'expense_employee',
            'user_id': cls.expense_user_employee.id,
            'expense_manager_id': cls.expense_user_manager.id,
            'work_contact_id': cls.expense_user_employee.partner_id.id,
        }).sudo(False)

        cls.expense_employee.user_partner_id.parent_id = cls.env.company.partner_id

        # Allow the current user to access the expenses.
        cls.env.user.group_ids |= group_expense_manager

        # Create analytic account
        cls.analytic_plan = cls.env['account.analytic.plan'].create({'name': 'Expense Plan Test'})
        cls.analytic_account_1 = cls.env['account.analytic.account'].create({
            'name': 'analytic_account_1',
            'plan_id': cls.analytic_plan.id,
        })
        cls.analytic_account_2 = cls.env['account.analytic.account'].create({
            'name': 'analytic_account_2',
            'plan_id': cls.analytic_plan.id,
        })

        cls.product_a, cls.product_b, cls.product_c = cls.env['product.product'].create([{
            'name': 'product_a',
            'default_code': 'product_a',
            'uom_id': cls.uom_unit.id,
            'list_price': 1000.0,
            'standard_price': 800.0,
            'can_be_expensed': True,
        }, {
            'name': 'product_b',
            'default_code': 'product_b',
            'uom_id': cls.uom_dozen.id,
            'list_price': 200.0,
            'standard_price': 160.0,
            'can_be_expensed': True,
        }, {
            'name': 'product_c with no cost',
            'default_code': 'product_c',
            'uom_id': cls.uom_dozen.id,
            'list_price': 200.0,
            'can_be_expensed': True,
        }])

        cls.frozen_today = datetime(year=2022, month=1, day=25, hour=0, minute=0, second=0)

    @classmethod
    def create_expenses(cls, values=None):
        if values is None or isinstance(values, dict):
            values = [values or {}]

        default_values = {
            'employee_id': cls.expense_employee.id,
            'date': cls.frozen_today.isoformat(),
            'company_id': cls.company.id,
            'currency_id': cls.currency.id,
        }

        default_product_values = {
            'product_id': cls.product_c.id,
            'total_amount_currency': 1000.00,
        }
        create_values = []
        for value_dict in values:
            if 'product_id' not in value_dict:
                default_values.update(default_product_values)
            value_dict = {**default_values, **(value_dict or {})}
            create_values.append(value_dict)
        return cls.env['hr.expense'].create(create_values).sorted()
