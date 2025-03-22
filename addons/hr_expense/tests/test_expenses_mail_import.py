# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.hr_expense.tests.common import TestExpenseCommon
from odoo.tests import tagged


@tagged('-at_install', 'post_install')
class TestExpensesMailImport(TestExpenseCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.product_a.default_code = 'product_a'
        cls.product_b.default_code = 'product_b'

    def test_import_expense_from_email(self):
        message_parsed = {
            'message_id': "the-world-is-a-ghetto",
            'subject': '%s %s' % (self.product_a.default_code, self.product_a.standard_price),
            'email_from': self.expense_user_employee.email,
            'to': 'catchall@yourcompany.com',
            'body': "Don't you know, that for me, and for you",
            'attachments': [],
        }

        expense = self.env['hr.expense'].message_new(message_parsed)
        self.assertRecordValues(expense, [{
            'product_id': self.product_a.id,
            'total_amount': 800.0,
            'employee_id': self.expense_employee.id,
        }])

    def test_import_expense_from_email_several_employees(self):
        """When a user has several employees' profiles from different companies, the right record should be selected"""
        user = self.expense_user_employee
        company_2 = user.company_ids[1]
        user.company_id = company_2.id

        # Create a second employee linked to the user for another company
        company_2_employee = self.env['hr.employee'].create({
            'name': 'expense_employee_2',
            'company_id': company_2.id,
            'user_id': user.id,
            'work_email': user.email,
        })

        message_parsed = {
            'message_id': "the-world-is-a-ghetto",
            'subject': 'New expense',
            'email_from': user.email,
            'to': 'catchall@yourcompany.com',
            'body': "Don't you know, that for me, and for you",
            'attachments': [],
        }
        expense = self.env['hr.expense'].message_new(message_parsed)
        self.assertRecordValues(expense, [{
            'employee_id': company_2_employee.id,
        }])

    def test_import_expense_from_email_employee_without_user(self):
        """When an employee is not linked to a user, he has to be able to create expenses from email"""
        employee = self.expense_employee
        employee.user_id = False

        message_parsed = {
            'message_id': "the-world-is-a-ghetto",
            'subject': 'New expense',
            'email_from': employee.work_email,
            'to': 'catchall@yourcompany.com',
            'body': "Don't you know, that for me, and for you",
            'attachments': [],
        }

        expense = self.env['hr.expense'].message_new(message_parsed)
        self.assertRecordValues(expense, [{
            'employee_id': employee.id,
        }])

    def test_import_expense_from_email_no_product(self):
        message_parsed = {
            'message_id': "the-world-is-a-ghetto",
            'subject': 'no product code 800',
            'email_from': self.expense_user_employee.email,
            'to': 'catchall@yourcompany.com',
            'body': "Don't you know, that for me, and for you",
            'attachments': [],
        }

        expense = self.env['hr.expense'].message_new(message_parsed)

        self.assertRecordValues(expense, [{
            'product_id': False,
            'total_amount': 800.0,
            'employee_id': self.expense_employee.id,
        }])

    def test_import_expense_from_email_product_no_cost(self):
        """
            We have to compute a value for the total amount
            even if the product has no cost.
        """
        product_no_cost = self.env['product.product'].create({
            'name': 'Product No Cost',
            'standard_price': 0.0,
            'can_be_expensed': True,
            'default_code': 'product_no_cost',
        })
        message_parsed = {
            'message_id': "test",
            'subject': 'product_no_cost my description 100',
            'email_from': self.expense_user_employee.email,
            'to': 'catchall@yourcompany.com',
            'body': "test",
            'attachments': [],
        }
        expense = self.env['hr.expense'].message_new(message_parsed)
        self.assertRecordValues(expense, [{
            'product_id': product_no_cost.id,
            'total_amount': 100.0,
            'employee_id': self.expense_employee.id,
        }])

    def test_import_expense_from_mail_parsing_subjects(self):

        def assertParsedValues(subject, currencies, exp_description, exp_amount, exp_product):
            product, amount, currency_id, description = self.env['hr.expense']\
                .with_user(self.expense_user_employee)\
                ._parse_expense_subject(subject, currencies)

            self.assertEqual(product, exp_product)
            self.assertAlmostEqual(amount, exp_amount)
            self.assertEqual(description, exp_description)

        # Without Multi currency access
        assertParsedValues(
            "product_a bar $1205.91 electro wizard",
            self.company_data['currency'],
            "bar electro wizard",
            1205.91,
            self.product_a,
        )

        # subject having other currency then company currency, it should ignore other currency then company currency
        assertParsedValues(
            "foo bar %s1406.91 royal giant" % self.currency_data['currency'].symbol,
            self.company_data['currency'],
            "foo bar %s royal giant" % self.currency_data['currency'].symbol,
            1406.91,
            self.env['product.product'],
        )

        # With Multi currency access
        self.expense_user_employee.groups_id |= self.env.ref('base.group_multi_currency')

        assertParsedValues(
            "product_a foo bar $2205.92 elite barbarians",
            self.company_data['currency'],
            "foo bar elite barbarians",
            2205.92,
            self.product_a,
        )

        # subject having other currency then company currency, it should accept other currency because multi currency is activated
        assertParsedValues(
            "product_a %s2510.90 chhota bheem" % self.currency_data['currency'].symbol,
            self.company_data['currency'] + self.currency_data['currency'],
            "chhota bheem",
            2510.90,
            self.product_a,
        )

        # subject without product and currency, should take company currency and default product
        assertParsedValues(
            "foo bar 109.96 spear goblins",
            self.company_data['currency'] + self.currency_data['currency'],
            "foo bar spear goblins",
            109.96,
            self.env['product.product'],
        )

        # subject with currency symbol at end
        assertParsedValues(
            "product_a foo bar 2910.94$ inferno dragon",
            self.company_data['currency'] + self.currency_data['currency'],
            "foo bar inferno dragon",
            2910.94,
            self.product_a,
        )

        # subject with no amount and product
        assertParsedValues(
            "foo bar mega knight",
            self.company_data['currency'] + self.currency_data['currency'],
            "foo bar mega knight",
            0.0,
            self.env['product.product'],
        )

        # price with a comma
        assertParsedValues(
            "foo bar 291,56$ mega knight",
            self.company_data['currency'] + self.currency_data['currency'],
            "foo bar mega knight",
            291.56,
            self.env['product.product'],
        )

        # price without decimals
        assertParsedValues(
            "foo bar 291$ mega knight",
            self.company_data['currency'] + self.currency_data['currency'],
            "foo bar mega knight",
            291.0,
            self.env['product.product'],
        )

        assertParsedValues(
            "product_a foo bar 291.5$ mega knight",
            self.company_data['currency'] + self.currency_data['currency'],
            "foo bar mega knight",
            291.5,
            self.product_a,
        )
