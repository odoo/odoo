# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.addons.hr_expense.tests.common import TestExpenseCommon
from odoo.addons.sale.tests.common import TestSaleCommon
from odoo.tests import tagged


@tagged('-at_install', 'post_install')
class TestReInvoice(TestExpenseCommon, TestSaleCommon):
    """
    Test that expenses, when linked to a sale order and invoiced are correctly re-invoiced on the sale order.
    It should cover the following rules:
        - Lines are never grouped together (even if re-invoiced at sale price and with a re-invoice delivered policy)
        - When posting the move of an expense, it creates the corresponding SOLs with the correct expense quantity
        - The amount of analytic account linked do not impact the quantities on the SOLs
        - The quantities ordered and delivered are reset to 0 when:
            - the expense sheet move has been reset to draft
            - the expense move is reversed
            - the expense move has been reset to draft
        - As it should be a one-to-one relation between model, we need to ensure that one expense only impacts one SOL
    The test tries to cover all the possible combinations of expense and invoicing policies, as well as the different actions
    """

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        new_sale_tax, new_purchase_tax = cls.env['account.tax'].create([{
            'name': 'Tax 12.499%',
            'amount': 12.499,
            'amount_type': 'percent',
            'type_tax_use': tax_type,
            'repartition_line_ids': [
                Command.create({'document_type': 'invoice', 'repartition_type': 'base'}),
                Command.create({
                    'document_type': 'invoice',
                    'repartition_type': 'tax',
                    'account_id': cls.company_data[f'default_account_tax_{tax_type}'].id
                }),
                Command.create({'document_type': 'refund', 'repartition_type': 'base'}),
                Command.create({
                    'document_type': 'refund',
                    'repartition_type': 'tax',
                    'account_id': cls.company_data[f'default_account_tax_{tax_type}'].id
                }),
            ],
        } for tax_type in ('sale', 'purchase')])

        cls.company_data.update({
            'service_order_sales_price': cls.env['product.product'].with_company(cls.company_data['company']).create({
                'name': 'service_order_sales_price',
                'categ_id': cls.company_data['product_category'].id,
                'standard_price': 0.,
                'list_price': 280.39,
                'type': 'service',
                'weight': 0.01,
                'uom_id': cls.env.ref('uom.product_uom_unit').id,
                'uom_po_id': cls.env.ref('uom.product_uom_unit').id,
                'default_code': 'FURN_99991',
                'invoice_policy': 'order',
                'expense_policy': 'sales_price',
                'taxes_id': [Command.set([new_sale_tax.id])],
                'supplier_taxes_id': [Command.set([new_purchase_tax.id])],
                'can_be_expensed': True,
            }),
            'service_delivery_sales_price': cls.env['product.product'].with_company(cls.company_data['company']).create({
                'name': 'service_order_sales_price',
                'categ_id': cls.company_data['product_category'].id,
                'standard_price': 0.,
                'list_price': 280.39,
                'type': 'service',
                'weight': 0.01,
                'uom_id': cls.env.ref('uom.product_uom_unit').id,
                'uom_po_id': cls.env.ref('uom.product_uom_unit').id,
                'default_code': 'FURN_99992',
                'invoice_policy': 'delivery',
                'expense_policy': 'sales_price',
                'taxes_id': [Command.set([new_sale_tax.id])],
                'supplier_taxes_id': [Command.set([new_purchase_tax.id])],
                'can_be_expensed': True,
            }),
            'service_delivery_cost_price': cls.env['product.product'].with_company(cls.company_data['company']).create({
                'name': 'service_delivery_cost_price',
                'categ_id': cls.company_data['product_category'].id,
                'standard_price': 235.28,
                'list_price': 280.39,
                'type': 'service',
                'weight': 0.01,
                'uom_id': cls.env.ref('uom.product_uom_unit').id,
                'uom_po_id': cls.env.ref('uom.product_uom_unit').id,
                'default_code': 'FURN_99993',
                'invoice_policy': 'delivery',
                'expense_policy': 'cost',
                'taxes_id': [Command.set([new_sale_tax.id])],
                'supplier_taxes_id': [Command.set([new_purchase_tax.id])],
                'can_be_expensed': True,
            }),
            'service_order_cost_price': cls.env['product.product'].with_company(cls.company_data['company']).create({
                'name': 'service_order_cost_price',
                'categ_id': cls.company_data['product_category'].id,
                'standard_price': 235.28,
                'list_price': 280.39,
                'type': 'service',
                'weight': 0.01,
                'uom_id': cls.env.ref('uom.product_uom_unit').id,
                'uom_po_id': cls.env.ref('uom.product_uom_unit').id,
                'default_code': 'FURN_99994',
                'invoice_policy': 'order',
                'expense_policy': 'cost',
                'taxes_id': [Command.set([new_sale_tax.id])],
                'supplier_taxes_id': [Command.set([new_purchase_tax.id])],
                'can_be_expensed': True,
            }),
        })
        # create SO line and confirm SO (with only one line)
        cls.expense_sale_order = cls.env['sale.order'].with_context(mail_notrack=True, mail_create_nolog=True).create({
            'partner_id': cls.partner_a.id,
            'partner_invoice_id': cls.partner_a.id,
            'partner_shipping_id': cls.partner_a.id,
            'order_line': [Command.create({
                'name': 'expense_employee: expense_1 invoicing=order, expense=sales_price',
                # Using the same name as one of the expense
                'product_id': cls.company_data['product_order_sales_price'].id,
                'product_uom_qty': 3.0,
                'price_unit': cls.company_data['product_order_sales_price'].standard_price,
            })],
        })
        cls.expense_sale_order.action_confirm()

        # Create an expense sheet with 6 expenses, covering all the expense & invoicing policies combinaisons
        cls.sale_expenses = cls.env['hr.expense'].create([
            {
                # exp_order_sale_1
                'name': 'expense_1 invoicing=order, expense=sales_price',
                'date': '2016-01-01',
                'product_id': cls.company_data['service_order_sales_price'].id,
                'total_amount': 100.34,
                'analytic_distribution': {cls.analytic_account_1.id: 100},
                'employee_id': cls.expense_employee.id,
                'sale_order_id': cls.expense_sale_order.id,
            },
            {
                # exp_order_sale_2
                'name': 'expense_2 invoicing=order, expense=sales_price',
                'date': '2016-01-02',
                'product_id': cls.company_data['service_order_sales_price'].id,
                'total_amount': 100.21,
                'employee_id': cls.expense_employee.id,
                'sale_order_id': cls.expense_sale_order.id,
            },
            {
                # exp_deliv_sale_3
                'name': 'expense_3 invoicing=delivery, expense=sales_price',
                'date': '2016-01-03',
                'product_id': cls.company_data['service_delivery_sales_price'].id,
                'total_amount': 10012.49,
                'analytic_distribution': {cls.analytic_account_1.id: 100},
                'employee_id': cls.expense_employee.id,
                'sale_order_id': cls.expense_sale_order.id,
            },
            {
                # exp_deliv_sale_4
                'name': 'expense_4 invoicing=delivery, expense=sales_price',
                'date': '2016-01-03',
                'product_id': cls.company_data['service_delivery_sales_price'].id,
                'analytic_distribution': {cls.analytic_account_1.id: 100},
                'total_amount': 10012.49,
                'employee_id': cls.expense_employee.id,
                'sale_order_id': cls.expense_sale_order.id,
            },
            {
                # exp_deliv_cost_5
                'name': 'expense_5 invoicing=delivery, expense=cost',
                'date': '2016-01-03',
                'product_id': cls.company_data['service_delivery_cost_price'].id,
                'quantity': 5,
                'employee_id': cls.expense_employee.id,
                'sale_order_id': cls.expense_sale_order.id,
            },
            {
                # exp_order_cost_6
                'name': 'expense_6 invoicing=order, expense=cost',
                'date': '2016-01-03',
                'product_id': cls.company_data['service_order_cost_price'].id,
                'quantity': 6,
                'employee_id': cls.expense_employee.id,
                'sale_order_id': cls.expense_sale_order.id,
            },
        ]).sorted()
        cls.sale_expense_sheet = cls.env['hr.expense.sheet'].create({
            'name': 'Reset expense test',
            'employee_id': cls.expense_employee.id,
            'journal_id': cls.company_data['default_journal_purchase'].id,
            'accounting_date': '2017-01-01',
            'expense_line_ids': [Command.set(cls.sale_expenses.ids)],
        })
        cls.sale_expense_sheet._do_approve()

    def test_expenses_reinvoice_case_1_create_moves(self):
        """
        CASE 1: Creation of the expense sheets moves. The sale order lines are created.
        """
        # pylint: disable=bad-whitespace
        self.sale_expense_sheet.action_sheet_move_create()

        self.assertRecordValues(self.expense_sale_order.order_line, [
            # [0] Line not created from a re-invoiced, should never be changed
            {'qty_delivered': 0.0, 'product_uom_qty': 3.0, 'is_expense': False, 'name': 'expense_employee: expense_1 invoicing=order, expense=sales_price'},
            # [1-6] SHEET 1 Lines: created with the correct quantities and linked to the expense
            {'qty_delivered': 6.0, 'product_uom_qty': 6.0, 'is_expense':  True, 'name': 'expense_employee: expense_6 invoicing=order, expense=cost'},  # noqa: E272
            {'qty_delivered': 5.0, 'product_uom_qty': 5.0, 'is_expense':  True, 'name': 'expense_employee: expense_5 invoicing=delivery, expense=cost'},  # noqa: E272
            {'qty_delivered': 1.0, 'product_uom_qty': 1.0, 'is_expense':  True, 'name': 'expense_employee: expense_4 invoicing=delivery, expense=sales_price'},  # noqa: E272
            {'qty_delivered': 1.0, 'product_uom_qty': 1.0, 'is_expense':  True, 'name': 'expense_employee: expense_3 invoicing=delivery, expense=sales_price'},  # noqa: E272
            {'qty_delivered': 1.0, 'product_uom_qty': 1.0, 'is_expense':  True, 'name': 'expense_employee: expense_2 invoicing=order, expense=sales_price'},  # noqa: E272
            {'qty_delivered': 1.0, 'product_uom_qty': 1.0, 'is_expense':  True, 'name': 'expense_employee: expense_1 invoicing=order, expense=sales_price'},  # noqa: E272
        ])

    def test_expenses_reinvoice_case_2_reset_sheet_to_draft(self):
        """
        CASE 2: Reset to draft of the expense sheet, the quantities of the corresponding SOL are set to 0
        """
        # CASE 1 steps
        self.sale_expense_sheet.action_sheet_move_create()

        # CASE 2 steps
        self.sale_expense_sheet.action_reset_expense_sheets()

        self.assertRecordValues(self.expense_sale_order.order_line, [
            # [0] Line not created from a re-invoiced, should never be changed
            {'qty_delivered': 0.0, 'product_uom_qty': 3.0, 'name': 'expense_employee: expense_1 invoicing=order, expense=sales_price'},
            # [1-6] SHEET Lines: quantities are reset to 0 and expenses are unlinked
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'name': 'expense_employee: expense_6 invoicing=order, expense=cost'},
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'name': 'expense_employee: expense_5 invoicing=delivery, expense=cost'},
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'name': 'expense_employee: expense_4 invoicing=delivery, expense=sales_price'},
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'name': 'expense_employee: expense_3 invoicing=delivery, expense=sales_price'},
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'name': 'expense_employee: expense_2 invoicing=order, expense=sales_price'},
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'name': 'expense_employee: expense_1 invoicing=order, expense=sales_price'},
        ])

    def test_expenses_reinvoice_case_3_recreate_move_after_reset(self):
        """
        CASE 3: Re-Approve and Re-Post the expense sheet after a reset, creating new SOLs with the correct quantities
        """
        # CASE 1 steps
        self.sale_expense_sheet.action_sheet_move_create()

        # CASE 2 steps
        self.sale_expense_sheet.action_reset_expense_sheets()

        # CASE 3 steps
        self.sale_expense_sheet._do_approve()
        self.sale_expense_sheet.action_sheet_move_create()

        self.assertRecordValues(self.expense_sale_order.order_line, [
            # [0] Line not created from a re-invoiced, should never be changed
            {'qty_delivered': 0.0, 'product_uom_qty': 3.0, 'name': 'expense_employee: expense_1 invoicing=order, expense=sales_price'},
            # [1-6] SHEET CASE 2 Lines: no change
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'name': 'expense_employee: expense_6 invoicing=order, expense=cost'},
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'name': 'expense_employee: expense_5 invoicing=delivery, expense=cost'},
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'name': 'expense_employee: expense_4 invoicing=delivery, expense=sales_price'},
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'name': 'expense_employee: expense_3 invoicing=delivery, expense=sales_price'},
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'name': 'expense_employee: expense_2 invoicing=order, expense=sales_price'},
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'name': 'expense_employee: expense_1 invoicing=order, expense=sales_price'},
            # [7-12] SHEET CASE 3 Lines: created with the correct quantities and linked to the expense
            {'qty_delivered': 6.0, 'product_uom_qty': 6.0, 'name': 'expense_employee: expense_6 invoicing=order, expense=cost'},
            {'qty_delivered': 5.0, 'product_uom_qty': 5.0, 'name': 'expense_employee: expense_5 invoicing=delivery, expense=cost'},
            {'qty_delivered': 1.0, 'product_uom_qty': 1.0, 'name': 'expense_employee: expense_4 invoicing=delivery, expense=sales_price'},
            {'qty_delivered': 1.0, 'product_uom_qty': 1.0, 'name': 'expense_employee: expense_3 invoicing=delivery, expense=sales_price'},
            {'qty_delivered': 1.0, 'product_uom_qty': 1.0, 'name': 'expense_employee: expense_2 invoicing=order, expense=sales_price'},
            {'qty_delivered': 1.0, 'product_uom_qty': 1.0, 'name': 'expense_employee: expense_1 invoicing=order, expense=sales_price'},
        ])

    def test_expenses_reinvoice_case_4_reset_sheet_move_to_draft(self):
        """
        CASE 4: Reset to draft of the expense sheet's move, the quantities of the corresponding SOL are set to 0
        """
        # CASE 1 steps
        self.sale_expense_sheet.action_sheet_move_create()

        # CASE 4 steps
        self.sale_expense_sheet.account_move_ids.button_draft()

        self.assertRecordValues(self.expense_sale_order.order_line, [
            # [0] Line not created from a re-invoiced, should never be changed
            {'qty_delivered': 0.0, 'product_uom_qty': 3.0, 'name': 'expense_employee: expense_1 invoicing=order, expense=sales_price'},
            # [1-6] SHEET Lines: quantities are reset to 0 and expenses are unlinked
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'name': 'expense_employee: expense_6 invoicing=order, expense=cost'},
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'name': 'expense_employee: expense_5 invoicing=delivery, expense=cost'},
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'name': 'expense_employee: expense_4 invoicing=delivery, expense=sales_price'},
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'name': 'expense_employee: expense_3 invoicing=delivery, expense=sales_price'},
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'name': 'expense_employee: expense_2 invoicing=order, expense=sales_price'},
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'name': 'expense_employee: expense_1 invoicing=order, expense=sales_price'},
        ])

    def test_expenses_reinvoice_case_5_repost_sheet_move_after_reset_to_draft(self):
        """
        CASE 5: Re-Post the expense sheet's move, creating new SOLs with the correct quantities
        """
        # CASE 1 steps
        self.sale_expense_sheet.action_sheet_move_create()

        # CASE 4 steps
        self.sale_expense_sheet.account_move_ids.button_draft()

        # CASE 5 steps
        self.sale_expense_sheet.account_move_ids.action_post()

        self.assertRecordValues(self.expense_sale_order.order_line, [
            # [0] Line not created from a re-invoiced, should never be changed
            {'qty_delivered': 0.0, 'product_uom_qty': 3.0, 'name': 'expense_employee: expense_1 invoicing=order, expense=sales_price'},
            # [1-6] SHEET CASE 4 Lines: no change
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'name': 'expense_employee: expense_6 invoicing=order, expense=cost'},
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'name': 'expense_employee: expense_5 invoicing=delivery, expense=cost'},
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'name': 'expense_employee: expense_4 invoicing=delivery, expense=sales_price'},
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'name': 'expense_employee: expense_3 invoicing=delivery, expense=sales_price'},
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'name': 'expense_employee: expense_2 invoicing=order, expense=sales_price'},
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'name': 'expense_employee: expense_1 invoicing=order, expense=sales_price'},
            # [7-12] SHEET CASE 5 Lines: created with the correct quantities and linked to the expense
            {'qty_delivered': 6.0, 'product_uom_qty': 6.0, 'name': 'expense_employee: expense_6 invoicing=order, expense=cost'},
            {'qty_delivered': 5.0, 'product_uom_qty': 5.0, 'name': 'expense_employee: expense_5 invoicing=delivery, expense=cost'},
            {'qty_delivered': 1.0, 'product_uom_qty': 1.0, 'name': 'expense_employee: expense_4 invoicing=delivery, expense=sales_price'},
            {'qty_delivered': 1.0, 'product_uom_qty': 1.0, 'name': 'expense_employee: expense_3 invoicing=delivery, expense=sales_price'},
            {'qty_delivered': 1.0, 'product_uom_qty': 1.0, 'name': 'expense_employee: expense_2 invoicing=order, expense=sales_price'},
            {'qty_delivered': 1.0, 'product_uom_qty': 1.0, 'name': 'expense_employee: expense_1 invoicing=order, expense=sales_price'},
        ])

    def test_expenses_reinvoice_case_6_reverse_expense_move(self):
        """
        CASE 6: Reverse the expense sheet's move, the quantities of the corresponding SOL are reset to 0
        """
        # CASE 1 steps
        self.sale_expense_sheet.action_sheet_move_create()

        # CASE 6 steps
        self.sale_expense_sheet.account_move_ids._reverse_moves()

        self.assertRecordValues(self.expense_sale_order.order_line, [
            # [0] Line not created from a re-invoiced, should never be changed
            {'qty_delivered': 0.0, 'product_uom_qty': 3.0, 'name': 'expense_employee: expense_1 invoicing=order, expense=sales_price'},
            # [1-6] SHEET Lines: quantities are reset to 0 and expenses are unlinked
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'name': 'expense_employee: expense_6 invoicing=order, expense=cost'},
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'name': 'expense_employee: expense_5 invoicing=delivery, expense=cost'},
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'name': 'expense_employee: expense_4 invoicing=delivery, expense=sales_price'},
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'name': 'expense_employee: expense_3 invoicing=delivery, expense=sales_price'},
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'name': 'expense_employee: expense_2 invoicing=order, expense=sales_price'},
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'name': 'expense_employee: expense_1 invoicing=order, expense=sales_price'},
        ])

    def test_expenses_reinvoice_case_7_ensure_one2one_relationship(self):
        """
        CASE 7: Test that two exact same sols are not reset to 0 when the expense of one of them is resetting the quantities to 0
        """
        original_expenses = self.sale_expenses
        self.sale_expense_sheet.write({
            'expense_line_ids': [Command.link(expense.copy().id) for expense in original_expenses],  # Duplicates of the expenses IN the reset sheet
            'accounting_date': '2017-01-01',  # To avoid "duplicate vendor reference raised" in the move
        })
        self.sale_expense_sheet._do_approve()
        self.sale_expense_sheet.action_sheet_move_create()
        sheet_2 = self.sale_expense_sheet.copy({
            'expense_line_ids': [Command.set([expense.copy().id for expense in original_expenses])],  # Duplicates of the expenses OUTSIDE the reset sheet
            'accounting_date': '2017-01-02',
        })
        sheet_2._do_approve()
        sheet_2.action_sheet_move_create()
        self.assertRecordValues(self.expense_sale_order.order_line, [
            # [0] Line not created from a re-invoiced, should never be changed
            {'qty_delivered': 0.0, 'product_uom_qty': 3.0, 'name': 'expense_employee: expense_1 invoicing=order, expense=sales_price'},
            # [1-12] SHEET 1 Lines: Created with the correct quantities
            {'qty_delivered': 6.0, 'product_uom_qty': 6.0, 'name': 'expense_employee: expense_6 invoicing=order, expense=cost'},
            {'qty_delivered': 5.0, 'product_uom_qty': 5.0, 'name': 'expense_employee: expense_5 invoicing=delivery, expense=cost'},
            {'qty_delivered': 1.0, 'product_uom_qty': 1.0, 'name': 'expense_employee: expense_4 invoicing=delivery, expense=sales_price'},
            {'qty_delivered': 1.0, 'product_uom_qty': 1.0, 'name': 'expense_employee: expense_3 invoicing=delivery, expense=sales_price'},
            {'qty_delivered': 1.0, 'product_uom_qty': 1.0, 'name': 'expense_employee: expense_2 invoicing=order, expense=sales_price'},
            {'qty_delivered': 1.0, 'product_uom_qty': 1.0, 'name': 'expense_employee: expense_1 invoicing=order, expense=sales_price'},
            {'qty_delivered': 6.0, 'product_uom_qty': 6.0, 'name': 'expense_employee: expense_6 invoicing=order, expense=cost'},
            {'qty_delivered': 5.0, 'product_uom_qty': 5.0, 'name': 'expense_employee: expense_5 invoicing=delivery, expense=cost'},
            {'qty_delivered': 1.0, 'product_uom_qty': 1.0, 'name': 'expense_employee: expense_4 invoicing=delivery, expense=sales_price'},
            {'qty_delivered': 1.0, 'product_uom_qty': 1.0, 'name': 'expense_employee: expense_3 invoicing=delivery, expense=sales_price'},
            {'qty_delivered': 1.0, 'product_uom_qty': 1.0, 'name': 'expense_employee: expense_2 invoicing=order, expense=sales_price'},
            {'qty_delivered': 1.0, 'product_uom_qty': 1.0, 'name': 'expense_employee: expense_1 invoicing=order, expense=sales_price'},
            # [13-18] SHEET 2 Lines: Created with the correct quantities
            {'qty_delivered': 6.0, 'product_uom_qty': 6.0, 'name': 'expense_employee: expense_6 invoicing=order, expense=cost'},
            {'qty_delivered': 5.0, 'product_uom_qty': 5.0, 'name': 'expense_employee: expense_5 invoicing=delivery, expense=cost'},
            {'qty_delivered': 1.0, 'product_uom_qty': 1.0, 'name': 'expense_employee: expense_4 invoicing=delivery, expense=sales_price'},
            {'qty_delivered': 1.0, 'product_uom_qty': 1.0, 'name': 'expense_employee: expense_3 invoicing=delivery, expense=sales_price'},
            {'qty_delivered': 1.0, 'product_uom_qty': 1.0, 'name': 'expense_employee: expense_2 invoicing=order, expense=sales_price'},
            {'qty_delivered': 1.0, 'product_uom_qty': 1.0, 'name': 'expense_employee: expense_1 invoicing=order, expense=sales_price'},
        ])

        self.sale_expense_sheet.account_move_ids.button_draft()

        self.assertRecordValues(self.expense_sale_order.order_line, [
            # [0] Line not created from a re-invoiced, should never be changed
            {'qty_delivered': 0.0, 'product_uom_qty': 3.0, 'name': 'expense_employee: expense_1 invoicing=order, expense=sales_price'},
            # [1-12] SHEET 1 Lines: quantities are reset to 0 and expenses are unlinked (because they are the oldest)
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'name': 'expense_employee: expense_6 invoicing=order, expense=cost'},
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'name': 'expense_employee: expense_5 invoicing=delivery, expense=cost'},
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'name': 'expense_employee: expense_4 invoicing=delivery, expense=sales_price'},
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'name': 'expense_employee: expense_3 invoicing=delivery, expense=sales_price'},
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'name': 'expense_employee: expense_2 invoicing=order, expense=sales_price'},
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'name': 'expense_employee: expense_1 invoicing=order, expense=sales_price'},
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'name': 'expense_employee: expense_6 invoicing=order, expense=cost'},
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'name': 'expense_employee: expense_5 invoicing=delivery, expense=cost'},
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'name': 'expense_employee: expense_4 invoicing=delivery, expense=sales_price'},
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'name': 'expense_employee: expense_3 invoicing=delivery, expense=sales_price'},
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'name': 'expense_employee: expense_2 invoicing=order, expense=sales_price'},
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'name': 'expense_employee: expense_1 invoicing=order, expense=sales_price'},
            # [13-18] SHEET 2 Lines: Not caught by the reset
            {'qty_delivered': 6.0, 'product_uom_qty': 6.0, 'name': 'expense_employee: expense_6 invoicing=order, expense=cost'},
            {'qty_delivered': 5.0, 'product_uom_qty': 5.0, 'name': 'expense_employee: expense_5 invoicing=delivery, expense=cost'},
            {'qty_delivered': 1.0, 'product_uom_qty': 1.0, 'name': 'expense_employee: expense_4 invoicing=delivery, expense=sales_price'},
            {'qty_delivered': 1.0, 'product_uom_qty': 1.0, 'name': 'expense_employee: expense_3 invoicing=delivery, expense=sales_price'},
            {'qty_delivered': 1.0, 'product_uom_qty': 1.0, 'name': 'expense_employee: expense_2 invoicing=order, expense=sales_price'},
            {'qty_delivered': 1.0, 'product_uom_qty': 1.0, 'name': 'expense_employee: expense_1 invoicing=order, expense=sales_price'},
        ])

    def test_expenses_reinvoice_analytic_distribution(self):
        """Test expense line with multiple analytic accounts is reinvoiced correctly"""

        (self.company_data['product_order_sales_price'] + self.company_data['product_delivery_sales_price']).write({
            'can_be_expensed': True,
        })

        # create SO line and confirm SO (with only one line)
        sale_order = self.env['sale.order'].with_context(mail_notrack=True, mail_create_nolog=True).create({
            'partner_id': self.partner_a.id,
            'partner_invoice_id': self.partner_a.id,
            'partner_shipping_id': self.partner_a.id,
            'order_line': [Command.create({
                'name': self.company_data['product_order_sales_price'].name,
                'product_id': self.company_data['product_order_sales_price'].id,
                'product_uom_qty': 2.0,
                'price_unit': 1000.0,
            })],
        })
        sale_order.action_confirm()

        expense_sheet = self.env['hr.expense.sheet'].create({
            'name': 'First Expense for employee',
            'employee_id': self.expense_employee.id,
            'journal_id': self.company_data['default_journal_purchase'].id,
            'accounting_date': '2017-01-01',
            'expense_line_ids': [
                Command.create({
                    'name': 'expense_1',
                    'date': '2016-01-01',
                    'product_id': self.company_data['product_order_sales_price'].id,
                    'quantity': 2,
                    'analytic_distribution': {self.analytic_account_1.id: 50, self.analytic_account_2.id: 50},
                    'employee_id': self.expense_employee.id,
                    'sale_order_id': sale_order.id,
                }),
            ],
        })

        expense_sheet.action_approve_expense_sheets()
        expense_sheet.action_sheet_move_create()

        self.assertRecordValues(sale_order.order_line, [
            # Original SO line:
            {
                'qty_delivered': 0.0,
                'product_uom_qty': 2.0,
                'is_expense': False,
            },
            # Expense lines:
            {
                'qty_delivered': 2.0,
                'product_uom_qty': 2.0,
                'is_expense': True,
            },
        ])

    def test_expense_reinvoice_tax_multine_line(self):
        """
        Tests that when a tax has multine distribution, the creation of an expense can go forward without issues
        """
        multi_distribution_tax = self.env['account.tax'].create({
            'name': 'Tax 10.00%',
            'amount': 10.00,
            'amount_type': 'percent',
            'type_tax_use': 'purchase',
            'invoice_repartition_line_ids': [
                Command.create({
                    'repartition_type': 'base',
                    'use_in_tax_closing': False,
                }),
                Command.create({
                    'repartition_type': 'tax',
                    'factor_percent': 70,
                    'use_in_tax_closing': False,
                }),
                Command.create({
                    'repartition_type': 'tax',
                    'factor_percent': 30,
                    'account_id': self.company_data['default_account_tax_purchase'].id,
                    'use_in_tax_closing': True,
                }),
            ],
            'refund_repartition_line_ids': [
                Command.create({
                    'repartition_type': 'base',
                    'use_in_tax_closing': False,
                }),
                Command.create({
                    'repartition_type': 'tax',
                    'factor_percent': 70,
                    'use_in_tax_closing': False,
                }),
                Command.create({
                    'repartition_type': 'tax',
                    'factor_percent': 30,
                    'account_id': self.company_data['default_account_tax_purchase'].id,
                    'use_in_tax_closing': True,
                }),
            ],
        })
        (self.company_data['product_order_sales_price'] + self.company_data['product_delivery_sales_price']).write({
            'can_be_expensed': True,
        })

        # create SO line and confirm SO (with only one line)
        sale_order = self.env['sale.order'].with_context(mail_notrack=True, mail_create_nolog=True).create({
            'partner_id': self.partner_a.id,
            'partner_invoice_id': self.partner_a.id,
            'partner_shipping_id': self.partner_a.id,
            'order_line': [Command.create({
                'name': self.company_data['product_order_sales_price'].name,
                'product_id': self.company_data['product_order_sales_price'].id,
                'product_uom_qty': 1.0,
                'price_unit': 1000.0,
            })],
        })
        sale_order.action_confirm()

        expense_sheet = self.env['hr.expense.sheet'].create({
            'name': 'First Expense for employee',
            'employee_id': self.expense_employee.id,
            'journal_id': self.company_data['default_journal_purchase'].id,
            'accounting_date': '2017-01-01',
            'expense_line_ids': [
                Command.create({
                    'name': 'expense_1',
                    'date': '2016-01-01',
                    'product_id': self.company_data['product_order_sales_price'].id,
                    'quantity': 1,
                    'employee_id': self.expense_employee.id,
                    'sale_order_id': sale_order.id,
                    'tax_ids': multi_distribution_tax.ids,
                }),
            ],
        })

        expense_sheet.action_approve_expense_sheets()
        expense_sheet.action_sheet_move_create()

        self.assertRecordValues(sale_order.order_line, [
            # Original SO line:
            {
                'qty_delivered': 0.0,
                'product_uom_qty': 1.0,
                'is_expense': False,
            },
            # Expense lines:
            {
                'qty_delivered': 1.0,
                'product_uom_qty': 1.0,
                'is_expense': True,
            },
        ])
