# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.stock.tests.common import TestStockCommon


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestAnalyticLine(TestStockCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
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
