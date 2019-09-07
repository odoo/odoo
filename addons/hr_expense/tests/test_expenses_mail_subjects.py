# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.hr_expense.tests.common import TestExpenseCommon


class TestExpenseSubject(TestExpenseCommon):
    """
    Check subject parsing while registering expense via mail.
    """

    def setUp(self):
        super(TestExpenseSubject, self).setUp()
        self.product_expense = self.env['product.product'].create({
            'name': "Phone bill",
            'can_be_expensed': True,
            'standard_price': 700,
            'list_price': 700,
            'type': 'consu',
            'default_code': 'EXP-PHONE'
        })

    def test_expense_subjects(self):
        employee = self.employee
        employee.user_id = self.user_employee
        parse_subject = self.env['hr.expense']._parse_expense_subject
        company_currency = employee.company_id.currency_id
        alternate_currency = self.env['res.currency'].create({'name': 'AAB', 'symbol': '#'})

        # Without Multi currency access
        subject = 'EXP-PHONE bar %s1205.91 electro wizard' % (company_currency.symbol,)

        product, price, currency_id, expense_description = parse_subject(subject, company_currency)
        self.assertEquals(expense_description, 'bar electro wizard', "Should be remove price and product from subject")
        self.assertAlmostEquals(price, 1205.91, "Price is not fetched correctly")
        self.assertEquals(currency_id, company_currency, "Should fetch currency correctly")
        self.assertEquals(product, self.product_expense, "Should fetch product correctly")

        # subject having other currency then company currency, it should ignore other currency then company currency
        subject = 'foo bar %s1406.91 royal giant' % (alternate_currency.symbol,)
        product, price, currency_id, expense_description = parse_subject(subject, company_currency)
        self.assertEquals(expense_description, 'foo bar %s royal giant' % (alternate_currency.symbol,), "Should be remove price and product from subject but not currency symbol")
        self.assertEquals(currency_id, company_currency, "Should fetch currency correctly")

        # With Multi currency access
        group_multi_currency = self.env.ref('base.group_multi_currency')
        self.user_employee.write({
            'groups_id': [(4, group_multi_currency.id)],
        })

        subject = 'EXP-PHONE foo bar %s2205.92 elite barbarians' % (company_currency.symbol,)  # with product code at start
        product, price, currency_id, expense_description = parse_subject(subject, company_currency)
        self.assertEquals(expense_description, 'foo bar elite barbarians', "Should be remove price and product from subject")
        self.assertAlmostEquals(price, 2205.92, "Price is not fetched correctly")
        self.assertEquals(currency_id, company_currency, "Should fetch currency correctly")
        self.assertEquals(product, self.product_expense, "Should fetch product correctly")

        # subject having other currency then company currency, it should accept other currency because multi currency is activated
        subject = 'EXP-PHONE %s2510.90 chhota bheem' % (alternate_currency.symbol,)
        product, price, currency_id, expense_description = parse_subject(subject, company_currency | alternate_currency)
        self.assertEquals(expense_description, 'chhota bheem', "Should be remove price and product from subject but not currency symbol")
        self.assertAlmostEquals(price, 2510.90, "Price is not fetched correctly")
        self.assertEquals(currency_id, alternate_currency, "Should fetch currency correctly")
        self.assertEquals(product, self.product_expense, "Should fetch product correctly")

        # subject without product and currency, should take company currency and default product
        subject = 'foo bar 109.96 spear goblins'
        product, price, currency_id, expense_description = parse_subject(subject, company_currency | alternate_currency)
        self.assertEquals(expense_description, 'foo bar spear goblins', "Should remove price")
        self.assertAlmostEquals(price, 109.96, "Price is not fetched correctly")
        self.assertIn(currency_id, company_currency | alternate_currency, "Should fetch company currency")
        self.assertFalse(product, "Should not have parsed any product")

        # subject with currency symbol at end
        subject = 'EXP-PHONE foo bar 2910.94%s inferno dragon' % (company_currency.symbol,)
        product, price, currency_id, expense_description = parse_subject(subject, company_currency | alternate_currency)
        self.assertEquals(expense_description, 'foo bar inferno dragon', "Should be remove price and product from subject")
        self.assertAlmostEquals(price, 2910.94, "Price is not fetched correctly")
        self.assertEquals(currency_id, company_currency, "Should fetch currency correctly")
        self.assertEquals(product, self.product_expense, "Should fetch product correctly")

        # subject with no amount and product
        subject = 'foo bar mega knight'
        product, price, currency_id, expense_description = parse_subject(subject, company_currency | alternate_currency)
        self.assertEquals(expense_description, 'foo bar mega knight', "Should be same as subject")
        self.assertAlmostEquals(price, 0.0, "Price is not fetched correctly")
        self.assertIn(currency_id, company_currency | alternate_currency, "Should fetch currency correctly")
        self.assertFalse(product, "Should fetch product correctly")

        # price with a comma
        subject = 'foo bar 291,56%s mega knight' % (company_currency.symbol,)
        product, price, currency_id, expense_description = parse_subject(subject, company_currency | alternate_currency)
        self.assertAlmostEquals(price, 291.56, "Price is not fetched correctly")
        self.assertEquals(currency_id, company_currency, "Should fetch currency correctly")

        # price without decimals
        subject = 'foo bar 291%s mega knight' % (company_currency.symbol,)
        product, price, currency_id, expense_description = parse_subject(subject, company_currency | alternate_currency)
        self.assertAlmostEquals(price, 291.0, "Price is not fetched correctly")

        subject = 'EXP-PHONE 2 foo bar 291.5%s mega knight' % (company_currency.symbol,)
        product, price, currency_id, expense_description = parse_subject(subject, company_currency | alternate_currency)
        print(price)
        self.assertAlmostEquals(price, 291.5, "Price is not fetched correctly")
