# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import ValidationError
from odoo.addons.stock.tests.common import TestStockCommon


class TestAnalytics(TestStockCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.plan1, cls.plan2 = cls.env['account.analytic.plan'].create([{'name': 'Plan 1'}, {'name': 'Plan 2'}])
        cls.plan1_name = cls.plan1._column_name()
        cls.plan2_name = cls.plan2._column_name()
        cls.analytic_account1, cls.analytic_account2 = cls.env['account.analytic.account'].create([
            {
                'name': 'Account 1',
                'plan_id': cls.plan1.id,
            },
            {
                'name': 'Account 2',
                'plan_id': cls.plan2.id,
            },
        ])
        cls.project = cls.env['project.project'].create({
            'name': 'Project',
            cls.plan1_name: cls.analytic_account1.id,
            cls.plan2_name: cls.analytic_account2.id,
        })
        # Remove the analytic account auto-generated when creating a timesheetable project if it exists
        cls.project.account_id = False
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

    def test_analytic_lines_generation_delivery(self):
        picking_out = self.PickingObj.create({
            'picking_type_id': self.picking_type_out,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location,
            'project_id': self.project.id,
        })
        picking_out.picking_type_id.analytic_costs = True
        move_values = {
            'product_uom': self.uom_unit.id,
            'picking_id': picking_out.id,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location,
        }
        self.MoveObj.create([
            {
                **move_values,
                'name': 'Move 1',
                'product_id': self.product1.id,
                'product_uom_qty': 3,
            },
            {
                **move_values,
                'name': 'Move 2',
                'product_id': self.product2.id,
                'product_uom_qty': 5,
            },
        ])
        picking_out.action_confirm()
        picking_out.button_validate()

        analytic_lines = picking_out.move_ids.analytic_account_line_ids

        analytic_line1 = analytic_lines.filtered(lambda a: a.product_id == self.product1)
        self.assertEqual(analytic_line1.amount, -300.0)
        self.assertEqual(analytic_line1[self.plan1_name], self.analytic_account1)
        self.assertEqual(analytic_line1[self.plan2_name], self.analytic_account2)

        analytic_line2 = analytic_lines.filtered(lambda a: a.product_id == self.product2)
        self.assertEqual(analytic_line2.amount, -1000.0)
        self.assertEqual(analytic_line2[self.plan1_name], self.analytic_account1)
        self.assertEqual(analytic_line2[self.plan2_name], self.analytic_account2)

    def test_analytic_lines_generation_receipt(self):
        picking_in = self.PickingObj.create({
            'picking_type_id': self.picking_type_in,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location,
            'project_id': self.project.id,
        })
        picking_in.picking_type_id.analytic_costs = True
        move_values = {
            'product_uom': self.uom_unit.id,
            'picking_id': picking_in.id,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location,
        }
        self.MoveObj.create([
            {
                **move_values,
                'name': 'Move 1',
                'product_id': self.product1.id,
                'product_uom_qty': 3,
            },
            {
                **move_values,
                'name': 'Move 2',
                'product_id': self.product2.id,
                'product_uom_qty': 5,
            },
        ])
        picking_in.action_confirm()
        picking_in.button_validate()

        analytic_lines = picking_in.move_ids.analytic_account_line_ids

        analytic_line1 = analytic_lines.filtered(lambda a: a.product_id == self.product1)
        self.assertEqual(analytic_line1.amount, 300.0)
        self.assertEqual(analytic_line1[self.plan1_name], self.analytic_account1)
        self.assertEqual(analytic_line1[self.plan2_name], self.analytic_account2)

        analytic_line2 = analytic_lines.filtered(lambda a: a.product_id == self.product2)
        self.assertEqual(analytic_line2.amount, 1000.0)
        self.assertEqual(analytic_line2[self.plan1_name], self.analytic_account1)
        self.assertEqual(analytic_line2[self.plan2_name], self.analytic_account2)

    def test_mandatory_analytic_plan_picking(self):
        self.env['account.analytic.applicability'].create({
            'business_domain': 'stock_picking',
            'analytic_plan_id': self.plan1.id,
            'applicability': 'mandatory',
        })
        picking_in = self.PickingObj.create({
            'picking_type_id': self.picking_type_in,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location,
            'project_id': self.project.id,
        })
        picking_in.picking_type_id.analytic_costs = True
        self.project[self.plan1_name] = False  # Remove the mandatory plan from the project linked to the picking
        self.MoveObj.create({
            'name': 'Move',
            'product_uom': self.uom_unit.id,
            'picking_id': picking_in.id,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location,
            'product_id': self.product2.id,
            'product_uom_qty': 5,
        })
        picking_in.action_confirm()
        with self.assertRaises(ValidationError):
            picking_in.button_validate()  # A missing mandatory plan is required on the project linked to the picking
