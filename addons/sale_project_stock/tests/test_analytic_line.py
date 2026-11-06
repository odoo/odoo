# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, fields
from odoo.tests import tagged

from odoo.addons.stock.tests.common import TestStockCommon


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestAnalyticLine(TestStockCommon):

    _test_user_groups = None  # FIXME list needed groups

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['account.chart.template']._load('generic_coa', cls.env.company, install_demo=False)
        cls.analytic_plan, _other_plans = cls.env['account.analytic.plan']._get_all_plans()
        cls.analytic_account = cls.env['account.analytic.account'].create({
            'name': 'Project - AA',
            'code': 'AA-2030',
            'plan_id': cls.analytic_plan.id,
        })
        cls.project = cls.env['project.project'].create({
            'name': 'Project',
            'account_id': cls.analytic_account.id,
            'allow_billable': True,
        })
        cls.product1, cls.product2 = cls.env['product.product'].create([
            {
                'name': 'product1',
                'standard_price': 100.0,
            },
            {
                'name': 'product2',
                'standard_price': 200.0,
            },
        ])

    def test_analytic_line_billable_type(self):
        """ This test ensure that when the user is creating stock move for a task with the 'from WH' and 'to WH' action,
        the analytic line generated have the correct billable_type and category_report. """
        picking_out, picking_in = self.PickingObj.create([{
            'picking_type_id': self.picking_type_out.id,
            'project_id': self.project.id,
        }, {
            'picking_type_id': self.picking_type_in.id,
            'project_id': self.project.id,
        }])
        self.picking_type_out.analytic_costs = True
        self.picking_type_in.analytic_costs = True
        self.MoveObj.create([{
                'uom_id': self.uom_unit.id,
                'picking_id': picking_out.id,
                'product_id': self.product1.id,
                'product_uom_qty': 3,
            }, {
                'uom_id': self.uom_unit.id,
                'picking_id': picking_in.id,
                'product_id': self.product2.id,
                'product_uom_qty': 5,
            },
        ])
        picking_out.action_confirm()
        picking_out.button_validate()
        picking_in.action_confirm()
        picking_in.button_validate()

        self.assertEqual('16_picking_entry_negative', picking_out.move_ids.analytic_account_line_ids.billable_type)
        self.assertEqual('costs', picking_out.move_ids.analytic_account_line_ids.category_report)
        self.assertEqual('15_picking_entry_positive', picking_in.move_ids.analytic_account_line_ids.billable_type)
        self.assertEqual('revenues', picking_in.move_ids.analytic_account_line_ids.category_report)

    def test_margins_customer_invoice_cogs(self):
        """ Check that invoicing a product valued in real time reports its cost in the project
        margins, without its stock counterpart.

        The cost of goods sold of a customer invoice moves the product value from the stock
        account to the expense account. Only the expense is a cost of the project, the stock
        counterpart must not be reported as a revenue.
        """
        self.product1.write({
            'is_storable': True,
            'standard_price': 60.0,
            'categ_id': self.env.ref('product.product_category_goods').id,
        })
        self.product1.categ_id.write({'property_valuation': 'real_time', 'property_cost_method': 'standard'})
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [Command.create({
                'product_id': self.product1.id,
                'price_unit': 100.0,
                'tax_ids': [Command.clear()],
                'analytic_distribution': {str(self.analytic_account.id): 100},
            })],
        })
        invoice.action_post()
        cogs_lines = invoice.line_ids.filtered(lambda line: line.display_type == 'cogs')
        cogs_expense_line = cogs_lines.filtered(lambda line: line.account_id.internal_group == 'expense')
        self.assertEqual(len(cogs_lines), 2)

        margins_lines = self.env['account.analytic.line'].search(self.project.action_real_margin()['domain'])
        self.assertRecordValues(margins_lines.sorted('amount'), [
            {'move_line_id': cogs_expense_line.id, 'amount': -60.0, 'category_report': 'costs'},
            {'move_line_id': invoice.invoice_line_ids.id, 'amount': 100.0, 'category_report': 'revenues'},
        ])

    def test_margins_vendor_bill_price_difference(self):
        """ Check that billing a standard cost product above its standard price charges the
        whole bill to the project margins.

        The price difference is booked on the bill as a stock correction balanced by a price
        difference expense. Unlike the stock counterpart of the cost of goods sold, this
        correction is part of the purchase cost and must be kept in the margins.
        """
        self.env.company.anglo_saxon_accounting = True
        price_diff_account = self.env['account.account'].create({
            'name': 'Price Difference',
            'code': '600099',
            'account_type': 'expense',
        })
        self.product1.write({
            'is_storable': True,
            'standard_price': 60.0,
            'categ_id': self.env.ref('product.product_category_goods').id,
        })
        self.product1.categ_id.write({
            'property_valuation': 'real_time',
            'property_cost_method': 'standard',
            'property_price_difference_account_id': price_diff_account.id,
        })
        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner.id,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [Command.create({
                'product_id': self.product1.id,
                'price_unit': 70.0,
                'tax_ids': [Command.clear()],
                'analytic_distribution': {str(self.analytic_account.id): 100},
            })],
        })
        bill.action_post()
        cogs_lines = bill.line_ids.filtered(lambda line: line.display_type == 'cogs')
        price_diff_line = cogs_lines.filtered(lambda line: line.account_id == price_diff_account)
        self.assertEqual(len(cogs_lines), 2)

        margins_lines = self.env['account.analytic.line'].search(self.project.action_real_margin()['domain'])
        self.assertRecordValues(margins_lines.sorted('amount'), [
            {'move_line_id': bill.invoice_line_ids.id, 'amount': -70.0},
            {'move_line_id': price_diff_line.id, 'amount': -10.0},
            {'move_line_id': (cogs_lines - price_diff_line).id, 'amount': 10.0},
        ])
