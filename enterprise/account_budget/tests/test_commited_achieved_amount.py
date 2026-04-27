# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command
from .common import TestAccountBudgetCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestCommittedAchievedAmount(TestAccountBudgetCommon):

    def create_other_category_aal(self):
        self.env['account.analytic.line'].create({
            'name': 'aal 1',
            'date': '2019-01-10',
            self.project_column_name: self.analytic_account_partner_a.id,
            'amount': 200,
        })
        self.env['account.analytic.line'].create({
            'name': 'aal 2',
            'date': '2019-01-10',
            self.project_column_name: self.analytic_account_partner_b.id,
            'amount': 200,
        })
        self.env['account.analytic.line'].create({
            'name': 'aal 3',
            'date': '2019-01-10',
            self.project_column_name: self.analytic_account_partner_a.id,
            'amount': -100,
        })
        self.env['account.analytic.line'].create({
            'name': 'aal 4',
            'date': '2019-01-10',
            self.project_column_name: self.analytic_account_partner_b.id,
            'amount': -100,
        })

    def test_budget_revenue_committed_achieved_amount(self):
        plan_a_line, plan_b_line, plan_b_admin_line = self.budget_analytic_revenue.budget_line_ids
        self.assertEqual(plan_a_line.achieved_amount, 0)
        self.assertEqual(plan_b_line.achieved_amount, 0)
        self.assertEqual(plan_b_admin_line.achieved_amount, 0)
        bill = self.purchase_order.invoice_ids

        # Post Purchase order's bill also to make sure this doesn't affect the revenue budget
        (bill + self.out_invoice).action_post()

        self.env['purchase.order'].invalidate_model(['currency_rate'])
        self.env['purchase.order.line'].invalidate_model(['qty_received', 'qty_invoiced', 'price_unit'])
        self.env['budget.line'].invalidate_model(['achieved_amount', 'committed_amount'])
        self.create_other_category_aal()

        # 2 analytic lines with analytic_account_partner_a in an income account:
        # {invoice line[0]: 200, invoice line[1]: 400}
        # 1 positive analytic line with analytic_account_partner_a, "other" category and without a fiscal account:
        # {aal 1: 200}
        # Total Achieved = 800
        self.assertEqual(plan_a_line.achieved_amount, 800.0)
        # Committed should be same as budget type is revenue
        self.assertEqual(plan_a_line.committed_amount, 800.0)

        # 2 analytic lines with analytic_account_partner_b in an income account:
        # {invoice line[2]: 700, invoice line[3]: 600}
        # 1 positive analytic line with analytic_account_partner_b, "other" category and without a fiscal account:
        # {aal 2: 200}
        # Total Achieved = 1500
        self.assertEqual(plan_b_line.achieved_amount, 1500.0)
        # Committed should be same as budget type is revenue
        self.assertEqual(plan_b_line.committed_amount, 1500.0)

        # 1 analytic line with accounts analytic_account_partner_b and analytic_account_administratif
        # invoice line[3]: 600
        self.assertEqual(plan_b_admin_line.achieved_amount, 600.0)
        # Committed should be same as budget type is revenue
        self.assertEqual(plan_b_admin_line.committed_amount, 600.0)

    def test_budget_analytic_expense_committed_achieved_amount(self):
        plan_a_line, plan_b_line, plan_b_admin_line = self.budget_analytic_expense.budget_line_ids
        self.assertEqual(plan_a_line.achieved_amount, 0)
        self.assertEqual(plan_b_line.achieved_amount, 0)
        self.assertEqual(plan_b_admin_line.achieved_amount, 0)
        bill = self.purchase_order.invoice_ids
        bill.write({'invoice_date': '2019-01-10'})
        bill.action_post()

        self.env['purchase.order'].invalidate_model(['currency_rate'])
        self.env['purchase.order.line'].invalidate_model(['qty_received', 'qty_invoiced', 'price_unit'])
        self.env['budget.line'].invalidate_model(['achieved_amount', 'committed_amount'])
        self.create_other_category_aal()

        # 2 analytic lines with account analytic_account_partner_a in an expense account:
        # Bill line[0]: -100, line[1]: -300
        # 1 negative analytic line with analytic_account_partner_a, "other" category and without a fiscal account:
        # {aal 3: -100}
        # Total Achieved = 500
        self.assertEqual(plan_a_line.achieved_amount, 500.0)

        # Product A have 2 PO lines with account analytic_account_partner_a in an expense account:
        # - one for line[0] with 10 ordered at price 100
        # - one for line[1] with 10 ordered at price 100
        # Also, there's 1 negative analytic line with analytic_account_partner_a, "other" category and
        # without a fiscal account that is not linked to a PO (aal 3: -100)
        self.assertEqual(plan_a_line.committed_amount, 2100.0)

        # 2 analytic lines with account analytic_account_partner_b in an expense account:
        # Bill line[2]: -600, line[3]: -500
        # 1 negative analytic line with analytic_account_partner_b, "other" category and without a fiscal account:
        # {aal 4: -100}
        # Total Achieved = 1200
        self.assertEqual(plan_b_line.achieved_amount, 1200.0)

        # Product B have 2 PO lines with account analytic_account_partner_b in an expense account:
        # - one for line[2] with 10 ordered at price 100
        # - one for line[3] with 10 ordered at price 100
        # Also, there's 1 negative analytic line with analytic_account_partner_b, "other" category and
        # without a fiscal account that is not linked to a PO (aal 4: -100)
        self.assertEqual(plan_b_line.committed_amount, 2100.0)

        # 1 analytic line with accounts analytic_account_partner_b and analytic_account_administratif
        # in an expense account
        # Bill line[3]: -500,
        self.assertEqual(plan_b_admin_line.achieved_amount, 500.0)

        # Product B have 1 PO line line[3] with 10 ordered at price 100 with analytic_account_partner_b
        # and analytic_account_administratif in an expense account
        self.assertEqual(plan_b_admin_line.committed_amount, 1000.0)

        # A bill should impact the budget even if it is not linked to a PO
        no_po_bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-01-11',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'analytic_distribution': {self.analytic_account_partner_a.id: 100},
                    'quantity': 3,
                    'price_unit': 100,
                    'account_id': self.company_data['default_account_expense'].id,
                }),
            ]
        })
        no_po_bill.action_post()
        self.env['budget.line'].invalidate_model(['achieved_amount', 'committed_amount'])
        self.assertEqual(plan_a_line.achieved_amount, 800.0)
        self.assertEqual(plan_a_line.committed_amount, 2400.0)

    def test_budget_analytic_expense_committed_amount_draft_bill(self):
        """ Test that the committed amount stays correct while a PO has a bill which is still unposted.
        The amount should not be 0.
        """
        # Draft the test purchase order.
        self.purchase_order.button_draft()
        # Create a new purchase order
        purchase_order = self.env['purchase.order'].create({
            'partner_id': self.partner_a.id,
            'date_order': '2019-01-10',
            'order_line': [
                Command.create({
                    'product_id': self.product_a.id,
                    'product_qty': 1,
                    'analytic_distribution': {self.analytic_account_partner_a.id: 100},
                }),
            ]
        })
        purchase_order.button_confirm()
        purchase_order.order_line.qty_received = 1

        # The confirmed purchase order should impact the analytic line committed amount.
        plan_a_line = self.budget_analytic_expense.budget_line_ids[0]
        # One PO line with an amount of 100 should be committed.
        self.assertBudgetLine(plan_a_line, committed=100, achieved=0)

        # Create the bill for the PO but do not post it. Committed amount should still be 100.
        bill = self.env['account.move'].browse(purchase_order.action_create_invoice()['res_id'])
        bill.invoice_date = '2019-01-10'
        self.assertBudgetLine(plan_a_line, committed=100, achieved=0)

        # Finally we post the bill. Committed amount AND achieved amount should be 100.
        purchase_order.invoice_ids.action_post()
        self.assertBudgetLine(plan_a_line, committed=100, achieved=100)

    def test_budget_analytic_discount_and_included_tax_amounts(self):
        """ Test that the committed and achieved amounts do not include discounts and included taxes """
        # Draft the test purchase order.
        self.purchase_order.button_draft()
        # Adapt a tax for price_include testing
        self.tax_purchase_a.price_include = True
        self.tax_purchase_a.amount_type = 'division'
        # Create a new purchase order
        purchase_order = self.env['purchase.order'].create({
            'partner_id': self.partner_a.id,
            'date_order': '2019-01-10',
            'order_line': [
                Command.create({
                    'product_id': self.product_a.id,
                    'product_qty': 2,
                    'discount': 10,
                    'analytic_distribution': {self.analytic_account_partner_a.id: 100},
                    'taxes_id': self.tax_purchase_a.ids,
                }),
            ]
        })
        purchase_order.button_confirm()
        purchase_order.order_line.qty_received = 2

        # The confirmed purchase order should impact the analytic line committed amount.
        plan_a_line = self.budget_analytic_expense.budget_line_ids[0]
        # One PO line with an amount of 153 should be committed.
        self.assertBudgetLine(plan_a_line, committed=153, achieved=0)

        # Create the bill for the PO but do not post it. Committed amount should still be 153.
        bill = self.env['account.move'].browse(purchase_order.action_create_invoice()['res_id'])
        bill.invoice_date = '2019-01-10'
        self.assertBudgetLine(plan_a_line, committed=153, achieved=0)

        # Finally we post the bill. Committed amount AND achieved amount should be 153.
        purchase_order.invoice_ids.action_post()
        self.assertBudgetLine(plan_a_line, committed=153, achieved=153)

    def test_budget_multi_currency(self):
        currency = self.setup_other_currency('EUR')
        self.purchase_order.button_draft()
        purchase_order = self.env['purchase.order'].create({
            'partner_id': self.partner_a.id,
            'date_order': '2019-01-10',
            'currency_id': currency.id,
            'order_line': [
                Command.create({
                    'product_id': self.product_a.id,
                    'product_qty': 10,
                    'analytic_distribution': {self.analytic_account_partner_a.id: 100},
                }),
            ]
        })
        purchase_order.button_confirm()
        self.assertRecordValues(purchase_order, [{
            'currency_rate': 2,
            'amount_total': 2000,  # 10 * 100 * 2
        }])

        plan_a_line = self.budget_analytic_expense.budget_line_ids[0]
        self.assertBudgetLine(plan_a_line, committed=1000, achieved=0)

        purchase_order.order_line.qty_received = 2
        bill = self.env['account.move'].browse(purchase_order.action_create_invoice()['res_id'])
        self.assertRecordValues(bill, [{
            'currency_id': currency.id,
            'amount_total': 400,  # 2/10 of 2000, or 2 * 100 * 2
            'amount_total_signed': -200
        }])
        bill.invoice_date = '2019-01-10'
        bill.action_post()
        self.assertBudgetLine(plan_a_line, committed=1000, achieved=200)

    def test_budget_analytic_multiple_bills_from_po(self):
        """ Test with multiple bills linked to a PO. """
        # Draft the test purchase order.
        self.purchase_order.button_draft()
        # Create a new purchase order
        purchase_order = self.env['purchase.order'].create({
            'partner_id': self.partner_a.id,
            'date_order': '2019-01-10',
            'order_line': [
                Command.create({
                    'product_id': self.product_a.id,
                    'product_qty': 10,
                    'analytic_distribution': {self.analytic_account_partner_a.id: 100},
                }),
            ]
        })
        purchase_order.button_confirm()
        plan_a_line = self.budget_analytic_expense.budget_line_ids[0]
        self.assertBudgetLine(plan_a_line, committed=1000, achieved=0)

        # Create bill for 5 units
        purchase_order.order_line.qty_received = 5
        bill = self.env['account.move'].browse(purchase_order.action_create_invoice()['res_id'])
        bill.invoice_date = '2019-01-10'
        self.assertBudgetLine(plan_a_line, committed=1000, achieved=0)
        bill.action_post()
        self.assertBudgetLine(plan_a_line, committed=1000, achieved=500)

        # Create another bill for another 2 units
        purchase_order.order_line.qty_received = 7
        bill = self.env['account.move'].browse(purchase_order.action_create_invoice()['res_id'])
        bill.invoice_date = '2019-01-10'
        bill.action_post()
        self.assertBudgetLine(plan_a_line, committed=1000, achieved=700)

    def test_multiple_bills_from_po_multiple_uom(self):
        """ Test with multiple bills linked to a PO and multiple UoM. """
        self.purchase_order.button_draft()
        gravel_ton = self.env['product.product'].create({
            'name': 'Gravel 1T',
            'uom_id': self.env.ref('uom.product_uom_ton').id,
            'uom_po_id': self.env.ref('uom.product_uom_ton').id,
            'standard_price': 1000,
        })
        gravel_kilo = self.env['product.product'].create({
            'name': 'Gravel 1kg',
            'uom_id': self.env.ref('uom.product_uom_kgm').id,
            'uom_po_id': self.env.ref('uom.product_uom_kgm').id,
            'standard_price': 1,
        })
        # Create a new purchase order
        purchase_order = self.env['purchase.order'].create({
            'partner_id': self.partner_a.id,
            'date_order': '2019-01-10',
            'order_line': [
                Command.create({
                    'product_id': gravel_ton.id,
                    'product_qty': 3.5,
                    'analytic_distribution': {self.analytic_account_partner_a.id: 100},
                }),
            ]
        })
        purchase_order.button_confirm()
        plan_a_line = self.budget_analytic_expense.budget_line_ids[0]
        self.assertBudgetLine(plan_a_line, committed=3500, achieved=0)

        # Create bill for 2 tons
        purchase_order.order_line.qty_received = 2
        bill = self.env['account.move'].browse(purchase_order.action_create_invoice()['res_id'])
        bill.invoice_date = '2019-01-10'
        bill.action_post()
        self.assertBudgetLine(plan_a_line, committed=3500, achieved=2000)

        # Create another bill for 1500 kg
        purchase_order.order_line.qty_received = 3.5
        bill = self.env['account.move'].browse(purchase_order.action_create_invoice()['res_id'])
        bill.invoice_line_ids.write({
            'product_id': gravel_kilo.id,
            'quantity': 1500,
        })
        bill.invoice_date = '2019-01-10'
        self.assertBudgetLine(plan_a_line, committed=3500, achieved=2000)
        bill.action_post()
        self.assertBudgetLine(plan_a_line, committed=3500, achieved=3500)

    def test_budget_analytic_both_committed_achieved_amount(self):
        plan_a_line, plan_b_line, plan_b_admin_line = self.budget_analytic_both.budget_line_ids
        self.assertEqual(plan_a_line.achieved_amount, 0)
        self.assertEqual(plan_b_line.achieved_amount, 0)
        self.assertEqual(plan_b_admin_line.achieved_amount, 0)
        bill = self.purchase_order.invoice_ids
        bill.write({'invoice_date': '2019-01-10'})

        (bill + self.out_invoice).action_post()

        self.env['purchase.order'].invalidate_model(['currency_rate'])
        self.env['purchase.order.line'].invalidate_model(['qty_received', 'qty_invoiced', 'price_unit'])
        self.env['budget.line'].invalidate_model(['achieved_amount', 'committed_amount'])
        self.create_other_category_aal()

        # 3 Negative and 3 Positive analytic lines positive with account analytic_account_partner_a:
        # Bill line[0]: -100, line[1]: -300, Invoice line[0]: 200, line[1]: 400, aal 1: 200, aal 3: -100
        # Total Achieved = (-100 + (-300) + 200 + 400 + 200 + (-100)) = 300
        self.assertEqual(plan_a_line.achieved_amount, 300)

        # Product A have 2 PO lines, one for line[0] with 10 order and 1 received and one for line[1] with 10 order and 3 received with account analytic_account_partner_a
        # Committed = ((order - received) * price) + achieved = ((10-1) + (10-3)) * -100 + 300 = -1300
        self.assertEqual(plan_a_line.committed_amount, -1300)

        # 3 Negative and 3 Positive analytic lines positive with account analytic_account_partner_a:
        # Bill line[2]: -600, line[3]: -500, Out Invoice line[2]: 700, line[3]: 600, aal 2: 200, aal 4: -100
        # Total Achieved = ((-600) + (-500) + 700 + 600 + 200 + (-100)) = 300
        self.assertEqual(plan_b_line.achieved_amount, 300)

        # Product B have 2 PO lines, one for line[2] with 10 order and 6 received and one for line[3] with 10 order and 5 received with account analytic_account_partner_b
        # Committed = ((order - received) * price) + achieved = ((10-6) + (10-5)) * -100 + 300 = -600
        self.assertEqual(plan_b_line.committed_amount, -600)

        # 1 Negative and 1 Positive lines with accounts analytic_account_partner_b and analytic_account_administratif
        # Bill line[3]: -500 Out Bill line[3]: 600
        # Total Achieved = ((-500) + 600) = 100
        self.assertEqual(plan_b_admin_line.achieved_amount, 100)

        # Product B have 1 PO line line[3] with 10 order and 5 received with analytic_account_partner_b and analytic_account_administratif
        # Committed = ((order - received) * price) + achieved = ((10-5) * -100 + 100 = -400
        self.assertEqual(plan_b_admin_line.committed_amount, -400)

    def test_budget_analytic_expense_with_credit_note(self):
        """ Test that credit note are taken into account. """
        plan_a_line, plan_b_line, plan_b_admin_line = self.budget_analytic_expense.budget_line_ids
        self.assertBudgetLine(plan_a_line, committed=2000, achieved=0)
        self.assertBudgetLine(plan_b_line, committed=2000, achieved=0)
        self.assertBudgetLine(plan_b_admin_line, committed=1000, achieved=0)
        # Create a bill from PO
        bill = self.purchase_order.invoice_ids
        bill.write({'invoice_date': '2019-01-10'})
        bill.action_post()
        self.assertBudgetLine(plan_a_line, committed=2000, achieved=400)
        self.assertBudgetLine(plan_b_line, committed=2000, achieved=1100)
        self.assertBudgetLine(plan_b_admin_line, committed=1000, achieved=500)
        # Create a credit note
        reversal_wizard = self.env['account.move.reversal'].with_context(active_model='account.move', active_ids=bill.ids).create({
            'journal_id': bill.journal_id.id,
            'date': '2019-01-11'
        })
        reversal = reversal_wizard.reverse_moves()
        self.env['account.move'].browse(reversal['res_id']).action_post()
        self.assertBudgetLine(plan_a_line, committed=2000, achieved=0)
        self.assertBudgetLine(plan_b_line, committed=2000, achieved=0)
        self.assertBudgetLine(plan_b_admin_line, committed=1000, achieved=0)

    def test_budget_analytic_purchase_order_last_budget_day(self):
        """
        Test that the committed amount is well computed when a PO is created on the last day of the budget range.
        """
        plan_a_line, plan_b_line, plan_b_admin_line = self.budget_analytic_expense.budget_line_ids
        self.assertBudgetLine(plan_a_line, committed=2000, achieved=0)

        # Create a PO on the last day of the budget range
        purchase_order = self.env['purchase.order'].create({
            'partner_id': self.partner_a.id,
            'date_order': '2019-12-31 21:00:00',
            'order_line': [
                Command.create({
                    'product_id': self.product_a.id,
                    'product_qty': 10,
                    'analytic_distribution': {self.analytic_account_partner_a.id: 100},
                }),
            ],
        })
        purchase_order.button_confirm()

        self.assertBudgetLine(plan_a_line, committed=3000, achieved=0)

        # Ensure that PO from next day does not impact the budget
        purchase_order.button_cancel()
        purchase_order.button_draft()
        purchase_order.date_order = '2020-01-01 00:00:00'
        purchase_order.button_confirm()

        self.assertBudgetLine(plan_a_line, committed=2000, achieved=0)

    def test_budget_report_with_purchase_order(self):
        """ Test PO linked to analytic budget with budget_type = 'both' """
        # Draft the test purchase order.
        self.purchase_order.button_draft()
        # Create a new purchase order
        purchase_order = self.env['purchase.order'].create({
            'partner_id': self.partner_a.id,
            'date_order': '2019-01-10',
            'order_line': [
                Command.create({
                    'product_id': self.product_a.id,
                    'product_qty': 10,
                    'analytic_distribution': {self.analytic_account_partner_a.id: 100},
                }),
            ]
        })
        purchase_order.button_confirm()
        plan_a_line = self.budget_analytic_both.budget_line_ids[0]
        self.assertBudgetLine(plan_a_line, committed=-1000, achieved=0)

    def test_account_budget_company_shared(self):
        """
        Ensure that a shared budget aggregates values across companies,
        and that filtering by company scopes it correctly.
        """
        # === Create shared budget ===
        budget = self.env['budget.analytic'].create({
            'name': 'Budget Shared',
            'date_from': '2025-01-01',
            'date_to': '2025-12-31',
            'company_id': False,
            'budget_line_ids': [
                Command.create({
                    'budget_amount': 2000,
                    self.project_column_name: self.analytic_account_partner_a.id,
                }),
            ]
        })
        budget.action_budget_confirm()
        line = budget.budget_line_ids[0]

        # === Setup: Two companies ===
        company_a = self.env.ref('base.main_company')
        company_b = self.env['res.company'].search([('id', '!=', company_a.id)])[0]

        # Ensure test user has access to both companies
        self.env.user.write({
            'company_ids': [(6, 0, [company_a.id, company_b.id])],
            'company_id': company_a.id,
        })

        # === PO and Bill for Company A ===
        po_a = self.env['purchase.order'].create({
            'partner_id': self.partner_a.id,
            'company_id': company_a.id,
            'date_order': '2025-01-10',
            'order_line': [
                Command.create({
                    'product_id': self.product_a.id,
                    'product_qty': 1,
                    'price_unit': 1000,
                    'analytic_distribution': {self.analytic_account_partner_a.id: 100},
                }),
            ]
        })
        po_a.button_confirm()

        # === PO and Bill for Company B ===
        po_b = self.env['purchase.order'].create({
            'partner_id': self.partner_a.id,
            'company_id': company_b.id,
            'date_order': '2025-01-10',
            'order_line': [
                Command.create({
                    'product_id': self.product_a.id,
                    'product_qty': 1,
                    'price_unit': 1000,
                    'analytic_distribution': {self.analytic_account_partner_a.id: 100},
                }),
            ]
        })
        po_b.button_confirm()
        # === Check shared totals ===
        self.assertEqual(line.committed_amount, 2000.0, "Shared committed should be 2000")
        self.assertEqual(line.achieved_amount, 0.0, "Shared achieved should be 1000")

        po_a.order_line.qty_received = 0.5
        bill_a = self.env['account.move'].browse(po_a.action_create_invoice()['res_id'])
        bill_a.invoice_date = '2025-01-15'
        bill_a.sudo().action_post()

        po_b.order_line.qty_received = 0.5
        bill_b = self.env['account.move'].with_company(company_b).browse(po_b.action_create_invoice()['res_id'])
        bill_b.invoice_date = '2025-01-15'
        bill_b.action_post()

        self.env['budget.line'].invalidate_model(['committed_amount', 'achieved_amount'])
        # === Check shared totals ===
        self.assertEqual(line.committed_amount, 2000.0, "Shared committed should be 2000")
        self.assertEqual(line.achieved_amount, 1000.0, "Shared achieved should be 1000")

        # === Filter to Company A only ===
        budget.company_id = company_a.id
        self.env['budget.line'].invalidate_model(['committed_amount', 'achieved_amount'])

        # === Check filtered totals ===
        self.assertEqual(line.committed_amount, 1000.0, "Company A committed should be 1000")
        self.assertEqual(line.achieved_amount, 500.0, "Company A committed should be 1000")

    def test_budget_analytic_expense_committed_amount_negative_price(self):
        """ Test that po lines with negative unit price does not create committed amount
            in budget report
        """
        # Reset to draft the existing purchase order
        self.purchase_order.button_draft()
        purchase_order = self.env['purchase.order'].create({
            'partner_id': self.partner_a.id,
            'date_order': '2019-01-10',
            'order_line': [
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 100,
                    'analytic_distribution': {self.analytic_account_partner_a.id: 100},
                }),
                Command.create({
                    'product_id': self.product_b.id,
                    'price_unit': -10,
                    'analytic_distribution': {self.analytic_account_partner_a.id: 100},
                })],
        })
        purchase_order.button_confirm()
        purchase_order.write({
            'order_line': [
                Command.update(purchase_order.order_line[0].id, {'qty_received': 1}),
                Command.update(purchase_order.order_line[1].id, {'qty_received': 1}),
            ]
        })
        purchase_order.action_create_invoice()
        purchase_order.invoice_ids.write({'invoice_date': '2019-01-10'})
        purchase_order.invoice_ids.action_post()

        # The discount line should impact both amounts of the budget line
        plan_a_line = self.budget_analytic_expense.budget_line_ids[0]
        self.assertBudgetLine(plan_a_line, committed=90, achieved=90)

    def test_account_budget_overlapping_accounts(self):
        """
        Ensure that committed and achieved amounts in budget report are not collected
        twice when the analytic distribution contains both accounts defined in separate
        budget lines
        """

        # Create a budget with 2 lines having different plan and analytic account
        budget = self.env['budget.analytic'].create({
            'name': 'Test Budget',
            'date_from': '2025-01-01',
            'date_to': '2025-12-31',
            'budget_line_ids': [
                Command.create({
                    'budget_amount': 500,
                    self.project_column_name: self.analytic_account_partner_a.id,
                }),
                Command.create({
                    'budget_amount': 600,
                    self.department_column_name: self.analytic_account_administratif.id,
                }),
            ]
        })
        budget.action_budget_confirm()
        line = budget.budget_line_ids[0]

        # Create a bill having both analytic accounts assigned to the same line
        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2025-01-10',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'analytic_distribution': {
                        f'{self.analytic_account_partner_a.id}, {self.analytic_account_administratif.id}': 100,
                    },
                    'quantity': 1,
                    'price_unit': 100,
                    'account_id': self.company_data['default_account_expense'].id,
                }),
            ]
        })
        bill.action_post()

        self.assertBudgetLine(line, committed=100.0, achieved=100.0)

        # Ensure amount in budget line report is equal to line amount
        action = line.action_open_budget_entries()
        report_lines = self.env['budget.report'].search(action['domain'])
        self.assertEqual(sum(line.committed for line in report_lines), 100.0)
