# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.project_hr_expense.tests.test_project_profitability import TestProjectHrExpenseProfitabilityCommon
from odoo.addons.sale.tests.common import TestSaleCommon
from odoo.addons.sale_project.tests.test_project_profitability import TestProjectProfitabilityCommon


@tagged('-at_install', 'post_install')
class TestProjectSaleExpenseProfitability(TestProjectProfitabilityCommon, TestProjectHrExpenseProfitabilityCommon, TestSaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product_c.write({
            'expense_policy': 'sales_price',
        })

    def test_project_profitability(self):
        project = self.env['project.project'].create({'name': 'new project'})
        project._create_analytic_account()
        account = project.account_id
        # Create a new company with the foreign currency.
        foreign_company = self.company_data_2['company']
        foreign_company.currency_id = self.foreign_currency
        foreign_partner = self.env['res.partner'].create({
            'name': 'Foreign Employee address',
            'company_id': foreign_company.id,
        })
        foreign_employee = self.env['hr.employee'].create({
            'name': 'foreign_employee',
            'company_id': foreign_company.id,
            'work_contact_id': foreign_partner.id,
            'work_email': 'email@email',
        })

        expense = self.env['hr.expense'].create({
            'name': 'expense',
            'product_id': self.company_data['product_order_sales_price'].id,
            'total_amount_currency': self.company_data['product_order_sales_price'].list_price,
            'employee_id': self.expense_employee.id,
            'analytic_distribution': {account.id: 100},
            'sale_order_id': self.sale_order.id,
        })

        # See method definition in `project_hr_expense.tests.test_project_profitability`
        expense_sheet = self.check_project_profitability_before_creating_and_approving_expense_sheet(
            expense,
            project,
            self.project_profitability_items_empty)
        self.assertEqual(expense_sheet.state, 'approve')

        # Create an expense in a foreign company, the expense is linked to the AA of the project.
        so_foreign = self.env['sale.order'].create({
            'name': 'Sale order foreign',
            'partner_id': self.partner_a.id,
            'company_id': foreign_company.id,
        })
        so_foreign.currency_id = self.foreign_currency
        so_foreign.action_confirm()
        expense_foreign = self.env['hr.expense'].create({
            'name': 'Expense foreign',
            'employee_id': foreign_employee.id,
            'product_id': self.product_c.id, # Foreign currency product must have no cost
            'total_amount_currency': 350.00 * 0.5,  # 0.5 is the exchange rate
            'company_id': foreign_company.id,
            'analytic_distribution': {account.id: 100},
            'currency_id': self.foreign_currency.id,
            'sale_order_id': so_foreign.id,
        })
        expense_sheet_vals_list = expense_foreign._get_default_expense_sheet_values()
        expense_sheet_vals_list[0]['employee_journal_id'] = self.company_data_2['default_journal_purchase'].id
        expense_sheet_foreign = self.env['hr.expense.sheet'].create(expense_sheet_vals_list)
        expense_sheet_foreign.action_submit_sheet()
        self.assertEqual(expense_sheet_foreign.state, 'submit')
        expense_sheet_foreign.action_approve_expense_sheets()
        self.assertEqual(expense_sheet_foreign.state, 'approve')

        expense_profitability = project._get_expenses_profitability_items(False)
        sequence_per_invoice_type = project._get_profitability_sequence_per_invoice_type()
        self.assertIn('expenses', sequence_per_invoice_type)
        expense_sequence = sequence_per_invoice_type['expenses']
        billed = -expense.untaxed_amount_currency - expense_foreign.untaxed_amount_currency * 0.2  # -280.0 - 175.0 * 0.2 = -315.0

        self.assertDictEqual(
            expense_profitability.get('revenues', {}),
            {},
        )
        self.assertNotIn(
            'costs',
            expense_profitability,
            'No costs should be found since the sheets are not posted or done.',
        )

        expense_sheet.action_sheet_move_post()
        self.assertEqual(expense_sheet.state, 'post')
        self.assertRecordValues(self.sale_order.order_line, [
            # Original SO line:
            {
                'product_id': self.product_delivery_service.id,
                'qty_delivered': 0.0,
                'product_uom_qty': 10,
                'is_expense': False,
            },
            {
                'product_id': self.company_data['product_order_sales_price'].id,
                'qty_delivered': 1.0,
                'product_uom_qty': 1.0,
                'is_expense': True,
            },
        ])
        expense_sol = self.sale_order.order_line.filtered(lambda sol: sol.product_id == self.company_data['product_order_sales_price'])

        expense_profitability = project._get_expenses_profitability_items(False)
        self.assertDictEqual(
            expense_profitability.get('revenues', {}),
            {'id': 'expenses', 'sequence': expense_sequence, 'invoiced': 0.0, 'to_invoice': expense_sol.untaxed_amount_to_invoice},
        )
        self.assertDictEqual(
            expense_profitability['costs'],
            {'id': 'expenses', 'sequence': expense_sequence, 'billed': expense.currency_id.round(-expense.untaxed_amount_currency), 'to_bill': 0.0},
        )

        self.assertDictEqual(
            project._get_profitability_items(False),
            {
                'revenues': {
                    'data': [expense_profitability['revenues']],
                    'total': {k: v for k, v in expense_profitability['revenues'].items() if k in ['to_invoice', 'invoiced']},
                },
                'costs': {
                    'data': [expense_profitability['costs']],
                    'total': {k: v for k, v in expense_profitability['costs'].items() if k in ['to_bill', 'billed']},
                },
            }
        )

        expense_sheet_foreign.action_sheet_move_post()
        self.assertEqual(expense_sheet_foreign.state, 'post')
        expense_sol_foreign = so_foreign.order_line[0]
        expense_profitability = project._get_expenses_profitability_items(False)
        self.assertDictEqual(
            expense_profitability.get('revenues', {}),
            {'id': 'expenses', 'sequence': expense_sequence, 'invoiced': 0.0, 'to_invoice': expense_sol.untaxed_amount_to_invoice + expense_sol_foreign.untaxed_amount_to_invoice * 0.2},
        )
        self.assertDictEqual(
            expense_profitability['costs'],
            {'id': 'expenses', 'sequence': expense_sequence, 'billed': expense.currency_id.round(billed), 'to_bill': 0.0},
        )

        self.assertDictEqual(
            project._get_profitability_items(False),
            {
                'revenues': {
                    'data': [expense_profitability['revenues']],
                    'total': {k: v for k, v in expense_profitability['revenues'].items() if k in ['to_invoice', 'invoiced']},
                },
                'costs': {
                    'data': [expense_profitability['costs']],
                    'total': {k: v for k, v in expense_profitability['costs'].items() if k in ['to_bill', 'billed']},
                },
            }
        )
        invoice = self.env['sale.advance.payment.inv'] \
            .with_context({
                'active_model': 'sale.order',
                'active_id': self.sale_order.id,
            }).create({
                'advance_payment_method': 'delivered',
            })._create_invoices(self.sale_order)
        invoice.action_post()

        expense_profitability = project._get_expenses_profitability_items(False)
        self.assertDictEqual(
            expense_profitability.get('revenues', {}),
            {'id': 'expenses', 'sequence': expense_sequence, 'invoiced': expense_sol.untaxed_amount_invoiced, 'to_invoice': expense_sol_foreign.untaxed_amount_to_invoice * 0.2},
        )

        credit_note = invoice._reverse_moves()
        credit_note.action_post()

        expense_profitability = project._get_expenses_profitability_items(False)
        self.assertDictEqual(
            expense_profitability.get('revenues', {}),
            {'id': 'expenses', 'sequence': expense_sequence, 'invoiced': 0.0, 'to_invoice': expense_sol.untaxed_amount_to_invoice + expense_sol_foreign.untaxed_amount_to_invoice * 0.2},
        )

        self.sale_order._action_cancel()
        expense_profitability = project._get_expenses_profitability_items(False)
        self.assertDictEqual(
            expense_profitability.get('revenues', {}),
            {'id': 'expenses', 'sequence': expense_sequence, 'invoiced': 0.0, 'to_invoice': expense_sol_foreign.untaxed_amount_to_invoice * 0.2},
        )
        self.assertDictEqual(
            expense_profitability['costs'],
            {'id': 'expenses', 'sequence': expense_sequence, 'billed': expense.currency_id.round(billed), 'to_bill': 0.0},
        )

        expense_sheet.action_reset_expense_sheets()
        expense_profitability = project._get_expenses_profitability_items(False)
        self.assertDictEqual(
            expense_profitability.get('revenues', {}),
            {'id': 'expenses', 'sequence': expense_sequence, 'invoiced': 0.0, 'to_invoice': expense_sol_foreign.untaxed_amount_to_invoice * 0.2},
        )
        self.assertDictEqual(
            expense_profitability.get('costs', {}),
            {'id': 'expenses', 'sequence': expense_sequence, 'billed': expense.currency_id.round(-expense_foreign.untaxed_amount_currency * 0.2), 'to_bill': 0.0},
        )

        invoice = self.env['sale.advance.payment.inv'].with_context({
                'active_model': 'sale.order',
                'active_id': so_foreign.id,
            }).create({
                'advance_payment_method': 'delivered',
            })._create_invoices(so_foreign)
        invoice.action_post()
        expense_profitability = project._get_expenses_profitability_items(False)
        self.assertDictEqual(
            expense_profitability.get('revenues', {}),
            {'id': 'expenses', 'sequence': expense_sequence, 'invoiced': expense_sol_foreign.untaxed_amount_invoiced * 0.2, 'to_invoice': 0.0},
        )

        credit_note = invoice._reverse_moves()
        credit_note.action_post()

        expense_profitability = project._get_expenses_profitability_items(False)
        self.assertDictEqual(
            expense_profitability.get('revenues', {}),
            {'id': 'expenses', 'sequence': expense_sequence, 'invoiced': 0.0, 'to_invoice': expense_sol_foreign.untaxed_amount_to_invoice * 0.2},
        )

        so_foreign._action_cancel()
        expense_profitability = project._get_expenses_profitability_items(False)
        self.assertDictEqual(
            expense_profitability.get('revenues', {}),
            {},
        )
        self.assertDictEqual(
            expense_profitability['costs'],
            {'id': 'expenses', 'sequence': expense_sequence, 'billed': expense.currency_id.round(-expense_foreign.untaxed_amount_currency * 0.2), 'to_bill': 0.0},
        )

        expense_sheet_foreign.action_reset_expense_sheets()
        expense_profitability = project._get_expenses_profitability_items(False)
        self.assertDictEqual(
            expense_profitability.get('revenues', {}),
            {},
        )
        self.assertDictEqual(
            expense_profitability.get('costs', {}),
            {},
        )

    def test_project_profitability_2(self):
        """
        Test Case:
        ==========
        - Create an expense for a project.
        - post it's entry moves
        - create an invoice for the sale order linked to the expense
        - post the invoice
        - the project profitability should not include the Customer invoice
        linked to the expense in the revenues, as the Expenses will be there.
        """

        product_new_project_task = self.env['product.product'].create({
            'name': "Service, create task in new project",
            'standard_price': 30,
            'list_price': 90,
            'type': 'service',
            'default_code': 'SERV-ORDERED2',
            'service_tracking': 'task_in_project',
        })

        sale_order = self.env['sale.order'].with_context(tracking_disable=True).create({
            'partner_id': self.partner.id,
            'partner_invoice_id': self.partner.id,
            'partner_shipping_id': self.partner.id,
        })

        self.env['sale.order.line'].create({
            'product_id': product_new_project_task.id,
            'product_uom_qty': 1,
            'order_id': sale_order.id,
        })

        sale_order.action_confirm()
        project = sale_order.order_line.project_id

        expense = self.env['hr.expense'].create({
            'name': 'expense',
            'product_id': self.company_data['product_order_cost'].id,
            'total_amount': self.company_data['product_order_cost'].list_price,
            'employee_id': self.expense_employee.id,
            'analytic_distribution': {project.account_id.id: 100},
            'sale_order_id': sale_order.id,
        })

        expense_sheet_vals_list = expense._get_default_expense_sheet_values()
        expense_sheet = self.env['hr.expense.sheet'].create(expense_sheet_vals_list)
        expense_sheet.action_submit_sheet()
        expense_sheet.action_approve_expense_sheets()
        expense_sheet.action_sheet_move_post()

        invoice = sale_order._create_invoices()
        invoice.action_post()

        sale_items = project.sudo()._get_sale_order_items()
        domain = [
            ('order_id', 'in', sale_items.order_id.ids),
            '|',
                '|',
                    ('project_id', 'in', project.ids),
                    ('project_id', '=', False),
                ('id', 'in', sale_items.ids),
        ]

        revenue_items_from_sol = project._get_revenues_items_from_sol(domain, False)
        expense_profitability = project._get_expenses_profitability_items(False)
        project_profitability = project._get_profitability_items(False)
        # invoice linked to the expense should not be included in the revenues
        self.assertDictEqual(
            project_profitability.get('revenues', {}),
            {
                'data': [expense_profitability['revenues'], revenue_items_from_sol['data'][0]],
                'total': {'invoiced': expense_profitability['revenues']['invoiced'] + revenue_items_from_sol['total']['invoiced'], 'to_invoice': expense_profitability['revenues']['to_invoice'] + revenue_items_from_sol['total']['to_invoice']},
            },
        )
