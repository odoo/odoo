# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.hr_expense.tests.common import TestExpenseCommon
from odoo.tests import tagged


@tagged('-at_install', 'post_install')
class TestExpensesMailImport(TestExpenseCommon):
    def test_import_expense_from_email(self):
        # pylint: disable=bad-whitespace
        messages = ({
                        'message_id': "the-world-is-a-ghetto",
                        'subject': f'{self.product_a.default_code} {self.product_a.standard_price}',
                        'email_from': self.expense_user_employee.email,
                        'to': 'catchall@yourcompany.com',
                        'body': "Don't you know, that for me, and for you",
                        'attachments': [],
                    }, {
                        'message_id': "the-world-is-a-ghetto",
                        'subject': 'no product code 800',
                        'email_from': self.expense_user_employee.email,
                        'to': 'catchall@yourcompany.com',
                        'body': "Don't you know, that for me, and for you",
                        'attachments': [],
                    }, {
                        'message_id': "test",
                        'subject': 'product_c my description 100',
                        'email_from': self.expense_user_employee.email,
                        'to': 'catchall@yourcompany.com',
                        'body': "test",
                        'attachments': [],
                    }
        )
        expenses = self.env['hr.expense']
        for message in messages:
            expenses |= self.env['hr.expense'].message_new(message)

        self.assertRecordValues(expenses, [
            {'product_id': self.product_a.id, 'total_amount_currency': 800.0, 'employee_id': self.expense_employee.id},
            {'product_id': False,             'total_amount_currency': 800.0, 'employee_id': self.expense_employee.id},
            {'product_id': self.product_c.id, 'total_amount_currency': 100.0, 'employee_id': self.expense_employee.id},
        ])

    def test_import_expense_from_mail_parsing_subjects(self):
        def assertParsedValues(subject, currencies, exp_description, exp_amount, exp_product, exp_currency):
            product, amount, currency_id, description = self.env['hr.expense'] \
                .with_user(self.expense_user_employee) \
                ._parse_expense_subject(subject, currencies)

            self.assertEqual(product, exp_product)
            self.assertAlmostEqual(amount, exp_amount)
            self.assertEqual(description, exp_description)
            self.assertEqual(currency_id, exp_currency)

        # Without Multi currency access
        assertParsedValues(
            "product_a bar $1205.91 electro wizard",
            self.company_data['currency'],
            "bar electro wizard",
            1205.91,
            self.product_a,
            self.company_data['currency'],
        )

        # subject having other currency then company currency, it should ignore other currency then company currency
        assertParsedValues(
            f'foo bar {self.currency_data["currency"].symbol}1406.91 royal giant',
            self.company_data['currency'],
            f'foo bar {self.currency_data["currency"].symbol} royal giant',
            1406.91,
            self.env['product.product'],
            self.company_data['currency'],
        )

        # With Multi currency access
        self.expense_user_employee.groups_id |= self.env.ref('base.group_multi_currency')
        assertParsedValues(
            "product_a foo bar $2205.92 elite barbarians",
            self.company_data['currency'],
            "foo bar elite barbarians",
            2205.92,
            self.product_a,
            self.company_data['currency'],
        )
        # subject having other currency then company currency, it should accept other currency because multi currency is activated
        assertParsedValues(
            f'product_a {self.currency_data["currency"].symbol}2510.90 chhota bheem',
            self.company_data['currency'] + self.currency_data['currency'],
            "chhota bheem",
            2510.90,
            self.product_a,
            self.currency_data['currency'],
        )

        # subject without product and currency, should take company currency and default product
        assertParsedValues(
            "foo bar 109.96 spear goblins",
            self.company_data['currency'] + self.currency_data['currency'],
            "foo bar spear goblins",
            109.96,
            self.env['product.product'],
            self.company_data['currency'],
        )

        # subject with currency symbol at end
        assertParsedValues(
            "product_a foo bar 2910.94$ inferno dragon",
            self.company_data['currency'] + self.currency_data['currency'],
            "foo bar inferno dragon",
            2910.94,
            self.product_a,
            self.company_data['currency'],
        )

        # subject with no amount and product
        assertParsedValues(
            "foo bar mega knight",
            self.company_data['currency'] + self.currency_data['currency'],
            "foo bar mega knight",
            0.0,
            self.env['product.product'],
            self.company_data['currency'],
        )

        # price with a comma
        assertParsedValues(
            "foo bar 291,56$ mega knight",
            self.company_data['currency'] + self.currency_data['currency'],
            "foo bar mega knight",
            291.56,
            self.env['product.product'],
            self.company_data['currency'],
        )

        # price different decimals than currency
        assertParsedValues(
            "foo bar 291$ mega knight",
            self.company_data['currency'] + self.currency_data['currency'],
            "foo bar mega knight",
            291.0,
            self.env['product.product'],
            self.company_data['currency'],
        )
        assertParsedValues(
            "product_a foo bar 291.5$ mega knight",
            self.company_data['currency'] + self.currency_data['currency'],
            "foo bar mega knight",
            291.5,
            self.product_a,
            self.company_data['currency'],
        )
