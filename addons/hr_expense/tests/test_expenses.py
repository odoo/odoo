# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import etree

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import Form, tagged

from odoo.addons.hr_expense.tests.common import TestExpenseCommon, account_less_only
from odoo.addons.mail.tests.common import mail_new_test_user


@tagged('-at_install', 'post_install')
class TestExpenses(TestExpenseCommon):
    #############################################
    #  Test Expense flows
    #############################################
    _test_user_groups = None  # FIXME list needed groups

    _test_independent_company_xmlid = 'base.test_company_with_branch'

    @account_less_only
    def test_expense_main_flow(self):
        """
        Test the main flows of expense
        This includes:
            - Approval flows for expense paid by company and employee up to the payment
            - price_unit, total_amount_currency and quantity computation
            - Cannot delete an analytic account if linked to an expense
        """

        expenses_by_employee = self.create_expenses([
            {
                'name': 'Employee PA 2*800',
                'employee_id': self.expense_employee.id,
                'product_id': self.product_a.id,
                'quantity': 2,
                'payment_mode': 'own_account',
                'company_id': self.company.id,
                'date': '2021-10-14',
                'analytic_distribution': {self.analytic_account_1.id: 100},
            }, {
                'name': 'Employee PB 160',
                'employee_id': self.expense_employee.id,
                'product_id': self.product_b.id,
                'payment_mode': 'own_account',
                'company_id': self.company.id,
                'date': '2021-10-13',
                'analytic_distribution': {self.analytic_account_2.id: 100},
            },
        ])
        expenses_by_company = self.create_expenses([
            {
                'name': 'Company PC 1000',
                'employee_id': self.expense_employee.id,
                'product_id': self.product_c.id,
                'total_amount_currency': 1000.00,
                'date': '2021-10-12',
                'payment_mode': 'company_account',
                'company_id': self.company.id,
            }, {
                'name': 'Company PB 160',
                'employee_id': self.expense_employee.id,
                'product_id': self.product_b.id,
                'payment_mode': 'company_account',
                'company_id': self.company.id,
                'date': '2021-10-11',
            },
        ])
        all_expenses = expenses_by_employee | expenses_by_company

        # Checking expense values at creation
        self.assertRecordValues(all_expenses, [
            {'name': 'Employee PA 2*800', 'total_amount_currency': 1600.00, 'price_unit':  800.00, 'state': 'draft'},
            {'name': 'Employee PB 160',   'total_amount_currency':  160.00, 'price_unit':  160.00, 'state': 'draft'},
            {'name': 'Company PC 1000',   'total_amount_currency': 1000.00, 'price_unit': 1000.00, 'state': 'draft'},
            {'name': 'Company PB 160',    'total_amount_currency':  160.00, 'price_unit':  160.00, 'state': 'draft'},
        ])

        # Submitting properly change states
        all_expenses.action_submit()
        self.assertRecordValues(all_expenses, [
            {'state': 'submitted'},
            {'state': 'submitted'},
            {'state': 'submitted'},
            {'state': 'submitted'},
        ])

        # Approving properly change states
        expenses_by_company.action_approve()
        expenses_by_employee.action_approve()
        self.assertRecordValues(all_expenses, [
            {'payment_mode': 'own_account',     'state': 'approved'},
            {'payment_mode': 'own_account',     'state': 'approved'},
            {'payment_mode': 'company_account', 'state': 'paid'},  # Already paid by the company
            {'payment_mode': 'company_account', 'state': 'paid'},
        ])

        expenses_by_employee.action_pay()

        first_expense_by_employee = expenses_by_employee[0]
        first_expense_by_company = expenses_by_company[0]

        # Trying to delete analytic accounts should be forbidden if linked to an expense
        with self.assertRaises(UserError):
            (self.analytic_account_1 | self.analytic_account_2).unlink()

        self.assertRecordValues(first_expense_by_employee | first_expense_by_company, [
            {'payment_mode': 'own_account',     'state': 'paid'},
            {'payment_mode': 'company_account', 'state': 'paid'},
        ])

        first_expense_by_employee.action_reset()
        self.assertEqual(first_expense_by_employee.state, 'draft')
        first_expense_by_employee.unlink()
        # Only possible if no expense linked to the account
        self.analytic_account_1.unlink()

    #############################################
    #  Test Multi-currency
    #############################################

    def test_expense_multi_currencies(self):
        """
        Checks that the currency rate is recomputed properly when the total in company currency is set to a new value
        """
        foreign_currency_1 = self.other_currency
        foreign_currency_2 = self.setup_other_currency('GBP', rounding=0.01, rates=([('2015-12-31', 1 / 1.52)]))

        foreign_expense_1, foreign_expense_2, foreign_expense_3 = self.create_expenses([{
                'name': 'foreign_expense_1',
                'payment_mode': 'company_account',
                'employee_id': self.expense_employee.id,
                'product_id': self.product_c.id,
                'total_amount_currency': 1000.00,
                'date': self.frozen_today,
                'company_id': self.company.id,
                'currency_id': foreign_currency_1.id,  # rate is 1:2
            },
            {
                'name': 'foreign_expense_2',
                'payment_mode': 'company_account',
                'employee_id': self.expense_employee.id,
                'product_id': self.product_c.id,
                'total_amount_currency': 1000.00,
                'date': self.frozen_today,
                'company_id': self.company.id,
                'currency_id': foreign_currency_2.id,  # rate is 1:1.52
            },
            {
                'name': 'foreign_expense_3',
                'payment_mode': 'company_account',
                'employee_id': self.expense_employee.id,
                'product_id': self.product_c.id,
                'total_amount_currency': 1000.00,
                'total_amount': 3000.00,
                'date': self.frozen_today,
                'company_id': self.company.id,
                'currency_id': foreign_currency_2.id,  # default rate is 1:1.52, should be overridden to 1:3
            },
        ]).sorted('name')
        all_expenses = foreign_expense_1 | foreign_expense_2 | foreign_expense_3
        self.assertRecordValues(all_expenses, [
            {'total_amount':  500.00, 'total_amount_currency': 1000.00, 'currency_rate': 0.50},
            {'total_amount': 1520.00, 'total_amount_currency': 1000.00, 'currency_rate': 1.52},
            {'total_amount': 3000.00, 'total_amount_currency': 1000.00, 'currency_rate': 3.00},
        ])

        # Manually changing rate on the two first expenses after creation to check they recompute properly
        # Back-end override
        foreign_expense_1.total_amount = 1000.00
        self.assertRecordValues(foreign_expense_1, [
            {'total_amount': 1000.00, 'total_amount_currency': 1000.00, 'currency_rate': 1.0},
        ])

        # Front-end override
        with Form(foreign_expense_2) as expense_form:
            expense_form.total_amount = 2000.00
        self.assertRecordValues(foreign_expense_2, [
            {'total_amount': 2000.00, 'total_amount_currency': 1000.00, 'currency_rate': 2.0},
        ])

    #############################################
    #  Test Corner Cases
    #############################################

    def test_expense_company_dates(self):
        expenses = self.create_expenses([
            {
                'name': 'Car Travel Expenses',
                'employee_id': self.expense_employee.id,
                'product_id': self.product_c.id,
                'total_amount': 350.00,
                'payment_mode': 'company_account',
                'date': '2024-01-01',
            },
            {
                'name': 'Lunch expense',
                'employee_id': self.expense_employee.id,
                'product_id': self.product_c.id,
                'total_amount': 90.00,
                'payment_mode': 'company_account',
                'date': '2024-01-12',
            },
        ]).sorted()  # By date desc

        expenses.action_submit()
        expenses.action_approve()

        self.assertRecordValues(expenses, [
            {'date': fields.Date.from_string('2024-01-12'), 'total_amount':  90.00, 'state': 'paid'},
            {'date': fields.Date.from_string('2024-01-01'), 'total_amount': 350.00, 'state': 'paid'},
        ])

    def test_corner_case_defaults_values_from_product(self):
        """ As soon as you set a product, the expense name, and uom are set according to the product. """
        # Disable multi-uom
        self.env.ref('base.group_user').implied_ids -= self.env.ref('uom.group_uom')
        self.expense_user_employee.group_ids -= self.env.ref('uom.group_uom')

        # Use the expense employee
        Expense = self.env['hr.expense'].with_user(self.expense_user_employee)

        # Make sure the multi-uom is correctly disabled for the user creating the expense
        self.assertFalse(Expense.env.user.has_group('uom.group_uom'))

        # Use a product not using the default uom "Unit(s)"
        product = Expense.env.ref('hr_expense.expense_product_mileage')

        expense_form = Form(Expense)
        expense_form.product_id = product
        expense = expense_form.save()
        self.assertEqual(expense.name, product.display_name)
        self.assertEqual(expense.product_uom_id, product.uom_id)

    @account_less_only
    def test_corner_case_expense_submitted_cannot_be_zero(self):
        """
        Test that the expenses are not submitted if the total amount is 0.0 nor able to be edited that way
        unless unlinking it from the expense.
        """
        expense = self.create_expenses({'total_amount': 0.0, 'total_amount_currency': 0.0})

        # CASE 1: FORBIDS Trying to submit an expense with a total_amount(_currency) of 0.0
        with self.assertRaises(UserError):
            expense.action_submit()

        # CASE 2: FORBIDS Trying to change the total_amount(_currency) to 0.0 when the expense is submitted to the manager
        expense.total_amount_currency = 1000
        expense.action_submit()
        with self.assertRaises(UserError):
            expense.total_amount_currency = 0.0
        with self.assertRaises(UserError):
            expense.total_amount = 0.0

        # CASE 3: FORBIDS Trying to change the total_amount(_currency) to 0.0 when the expense is approved
        expense.action_approve()
        with self.assertRaises(UserError):
            expense.total_amount_currency = 0.0
        with self.assertRaises(UserError):
            expense.total_amount = 0.0

        # CASE 4: FORBIDS Trying to change the total_amount(_currency) to 0.0 when the expense is paid
        expense.action_pay()
        with self.assertRaises(UserError):
            expense.total_amount_currency = 0.0
        with self.assertRaises(UserError):
            expense.total_amount = 0.0

        # CASE 5: ALLOWS Changing the total_amount(_currency) to 0.0 when the expense is reset to draft
        expense.action_reset()
        expense.write({'total_amount_currency': 0.0, 'total_amount': 0.0})

        # CASE 6: FORBIDS Setting the amounts to 0 while submitting the expense
        expense.write({'total_amount_currency': 1000.0, 'total_amount': 1000.0})
        with self.assertRaises(UserError):
            expense.write({'total_amount_currency': 0.0, 'state': 'submitted'})
        with self.assertRaises(UserError):
            expense.write({'total_amount': 0.0, 'state': 'submitted'})

        # CASE 7: ALLOWS Setting the amounts to 0 while resetting the expense to draft
        expense.write({'total_amount_currency': 0.0, 'total_amount': 0.0, 'state': 'draft'})

    def test_foreign_currencies_total(self):
        """ Check that the dashboard computes amount properly in company currency """
        self.create_expenses([{
                'name': 'Company expense',
                'payment_mode': 'company_account',
                'total_amount_currency': 1000.00,
                'employee_id': self.expense_employee.id,
            },
            {
                'name': 'Employee expense',
                'payment_mode': 'own_account',
                'currency_id': self.other_currency.id,
                'total_amount_currency': 1000.00,
                'total_amount': 2000.00,
                'employee_id': self.expense_employee.id,
            },
        ])
        expense_data = self.env['hr.expense'].with_user(self.expense_user_employee).get_expense_dashboard()
        self.assertEqual(expense_data['draft']['amount'], 3000.00)

    def test_dashboard_cards_are_search_filters(self):
        """ Clicking on a card of the dashboard toggles the search filter named after the key of the card """
        search_view = self.env.ref('hr_expense.hr_expense_view_search')
        search_arch = etree.fromstring(self.env['hr.expense'].get_view(search_view.id, 'search')['arch'])
        self.assertLessEqual(set(self.env['hr.expense'].get_expense_dashboard()), set(search_arch.xpath('//filter/@name')))

    def test_update_expense_price_on_product_standard_price(self):
        """
        Tests that updating the standard price of a product will update all the un-submitted
        expenses using that product.
        """
        product = self.env['product.product'].create({
            'name': 'Product',
            'standard_price': 100.0,
        })
        expenses = expense_no_update, expense_update = self.create_expenses([
            {'name': name, 'product_id': product.id, 'total_amount': 100.0}
            for name in ('test no update', 'test update')
        ]).sorted('name')

        self.assertRecordValues(expenses.sorted('name'), [
            {'name': 'test no update', 'price_unit': 100.0, 'quantity': 1, 'total_amount': 100.0},
            {'name':    'test update', 'price_unit': 100.0, 'quantity': 1, 'total_amount': 100.0},
        ])
        expense_no_update.action_submit()  # No update when the expense is submitted

        product.standard_price = 200.0
        self.assertRecordValues(expenses.sorted('name'), [
            {'name': 'test no update', 'price_unit': 100.0, 'quantity': 1.0, 'total_amount': 100.0},
            {'name':    'test update', 'price_unit': 200.0, 'quantity': 1.0, 'total_amount': 200.0},  # total is updated
        ])

        expense_update.quantity = 5
        self.assertRecordValues(expenses.sorted('name'), [
            {'name': 'test no update', 'price_unit': 100.0, 'quantity': 1, 'total_amount':  100.0},
            {'name':    'test update', 'price_unit': 200.0, 'quantity': 5, 'total_amount': 1000.0},  # total is updated
        ])

        product.standard_price = 0.0
        self.assertRecordValues(expenses.sorted('name'), [
            {'name': 'test no update', 'price_unit':  100.0, 'quantity': 1, 'total_amount':  100.0},
            {'name':    'test update', 'price_unit': 1000.0, 'quantity': 1, 'total_amount': 1000.0},  # quantity & price_unit only are updated
        ])

        expenses.action_submit()  # This expense should not be updated any more
        product.standard_price = 300.0
        self.assertRecordValues(expenses.sorted('name'), [
            {'name': 'test no update', 'price_unit':  100.0, 'quantity': 1, 'total_amount':  100.0},
            {'name':    'test update', 'price_unit': 1000.0, 'quantity': 1, 'total_amount': 1000.0},  # no update
        ])

    def test_expense_multi_company(self):
        main_company = self.company
        other_company = self.company_2
        self.expense_employee.sudo().company_id = other_company

        # The expense employee is able to create an expense for company_2.
        # product_a needs a standard_price in company_2
        self.product_a.with_context(allowed_company_ids=self.company_2.ids).standard_price = 100

        Expense = self.env['hr.expense'].with_user(self.expense_user_employee).with_context(allowed_company_ids=other_company.ids)
        expense_approve = Expense.create([{
            'name': 'First Expense for employee',
            'employee_id': self.expense_employee.id,
            'date': '2016-01-01',
            'product_id': self.product_a.id,
            'quantity': 1200.0,
        }])
        expense_refuse = Expense.create([{
            'name': 'Second Expense for employee',
            'employee_id': self.expense_employee.id,
            'date': '2016-01-01',
            'product_id': self.product_a.id,
            'quantity': 1000.0,
        }])
        expenses = expense_approve | expense_refuse
        self.assertRecordValues(expenses, [
            {'company_id': self.company_2.id},
            {'company_id': self.company_2.id},
        ])

        # The expense employee is able to submit the expense.
        expenses.with_user(self.expense_user_employee).action_submit()

        # An expense manager is not able to approve nor refuse without access to company_2.
        with self.assertRaises(UserError):
            expense_approve \
                .with_user(self.expense_user_manager) \
                .with_context(allowed_company_ids=main_company.ids, company_id=main_company.id) \
                .action_approve()

        with self.assertRaises(UserError):
            expense_refuse \
                .with_user(self.expense_user_manager) \
                .with_context(allowed_company_ids=main_company.ids) \
                ._do_refuse('failed')

        # An expense manager is able to approve/refuse with access to company_2.
        expense_approve \
            .with_user(self.expense_user_manager) \
            .with_context(allowed_company_ids=other_company.ids) \
            .action_approve()
        expense_refuse \
            .with_user(self.expense_user_manager) \
            .with_context(allowed_company_ids=other_company.ids) \
            ._do_refuse('failed')

    def test_expense_set_total_amount_to_0(self):
        """ Checks that amount fields are correctly updating when setting total_amount to 0 """
        expense = self.create_expenses({
            'product_id': self.product_c.id,
            'total_amount_currency': 100.0,
        })
        expense.total_amount_currency = 0.0
        self.assertTrue(expense.company_currency_id.is_zero(expense.total_amount))

    def test_expense_set_quantity_to_0(self):
        """ Checks that amount fields except for unit_amount are correctly updating when setting quantity to 0 """
        expense = self.create_expenses({
            'product_id': self.product_b.id,
            'quantity': 10
        })
        expense.quantity = 0
        self.assertTrue(expense.currency_id.is_zero(expense.total_amount_currency))
        self.assertEqual(expense.company_currency_id.compare_amounts(expense.price_unit, self.product_b.standard_price), 0)

    def test_remove_company_id_from_hr_expense(self):
        expense = self.create_expenses({
                'name': 'Company PC 1000',
                'employee_id': self.expense_employee.id,
                'product_id': self.product_c.id,
                'total_amount_currency': 1000.00,
                'date': '2021-10-12',
                'payment_mode': 'company_account',
                'company_id': self.company.id,
            })
        form = Form(expense)
        form.company_id = self.env['res.company']
        self.assertEqual(form.is_editable, False)
        form.company_id = self.env.company
        self.assertEqual(form.is_editable, True)

    def test_expense_team_approver_refuse_mixed_selection(self):
        """
        - Set up a team approver and a subordinate, creating one submitted expense for each.
        - Verify the approver cannot approve their own expense, but can approve the subordinate's.
        - Refuse both expenses together to ensure a `UserError` is raised with a reason only for the invalid expense
        (own expense), then verify the subordinate's expense opens the refusal wizard successfully.
        """
        team_approver = mail_new_test_user(
            self.env,
            login='expense_team_approver',
            groups='base.group_user,hr_expense.group_hr_expense_team_approver',
        )
        approver_employee = self.env['hr.employee'].sudo().create({
            'name': 'approver_employee',
            'user_id': team_approver.id,
            'expense_manager_id': self.expense_user_manager.id,
        })
        subordinate_employee = self.env['hr.employee'].sudo().create({
            'name': 'subordinate_employee',
            'parent_id': approver_employee.id,
        })
        own_expense = self.create_expenses({'name': 'Own expense', 'employee_id': approver_employee.id})
        subordinate_expense = self.create_expenses({'name': 'Subordinate expense', 'employee_id': subordinate_employee.id})
        expenses = own_expense + subordinate_expense
        expenses.action_submit()
        self.assertRecordValues(expenses, [{'state': 'submitted'}, {'state': 'submitted'}])

        own_expense_as_approver = own_expense.with_user(team_approver)
        subordinate_expense_as_approver = subordinate_expense.with_user(team_approver)
        self.assertFalse(own_expense_as_approver.can_approve)
        self.assertTrue(subordinate_expense_as_approver.can_approve)

        with self.assertRaises(UserError) as error:
            (own_expense_as_approver + subordinate_expense_as_approver).action_refuse()
        self.assertIn("Own expense: It is your own expense", error.exception.args[0])
        self.assertNotIn("Subordinate expense", error.exception.args[0])

        action = subordinate_expense_as_approver.action_refuse()
        self.assertEqual(action['res_model'], 'hr.expense.refuse.wizard')
