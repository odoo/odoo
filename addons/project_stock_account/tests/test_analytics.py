# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.analytic.tests.common import AnalyticCommon
from odoo.addons.project.tests.test_project_base import TestProjectCommon
from odoo.addons.stock.tests.common import TestStockCommon
from odoo.exceptions import ValidationError


class TestAnalytics(TestStockCommon, TestProjectCommon, AnalyticCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._enable_project_manager(cls.user_stock_user)
        cls._enable_analytic_accounting(cls.user_stock_user)
        cls._enable_project_manager(cls.user_stock_manager)
        cls._enable_analytic_accounting(cls.user_stock_manager)
        cls.plan1_name = cls.analytic_plan_1._column_name()
        cls.plan2_name = cls.analytic_plan_2._column_name()
        cls.analytic_account1, cls.analytic_account2 = cls.env['account.analytic.account'].create([
            {
                'name': 'Account 1',
                'plan_id': cls.analytic_plan_1.id,
                'company_id': cls.stock_company.id,
            },
            {
                'name': 'Account 2',
                'plan_id': cls.analytic_plan_2.id,
                'company_id': cls.stock_company.id,
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
            'picking_type_id': self.picking_type_out.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'project_id': self.project.id,
        })
        picking_out.picking_type_id.analytic_costs = True
        move_values = {
            'product_uom': self.uom_unit.id,
            'picking_id': picking_out.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
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
        """
            In this module, the project profitability should be computed while checking the AAL data from the pickings.
            When the 'analytic costs' option from delivery order is enabled, it is expected for picking to generate
            an aal for the move line created. These aals should be taken into account when computing the 'project
            profitability' right side panel and displayed under the 'costs -> materials' section.
        """
        self.uid = self.user_stock_manager

        picking_in = self.PickingObj.create({
            'picking_type_id': self.picking_type_in.id,
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'project_id': self.project.id,
            'company_id': self.stock_company.id,
        })

        picking_in.picking_type_id.analytic_costs = True
        move_values = {
            'product_uom': self.uom_unit.id,
            'picking_id': picking_in.id,
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'company_id': self.stock_company.id,
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

        self.assertDictEqual(
            self.project._get_profitability_items(False),
            {
                'revenues': {'data': [], 'total': {'invoiced': 0.0, 'to_invoice': 0.0}},
                'costs': {
                    'data': [{'id': 'other_costs', 'sequence': 15, 'billed': 1300.0, 'to_bill': 0.0}],
                    'total': {'billed': 1300.0, 'to_bill': 0.0}
                }
            }
        )

    def test_mandatory_analytic_plan_picking(self):
        self.env['account.analytic.applicability'].create({
            'business_domain': 'stock_picking',
            'analytic_plan_id': self.analytic_plan_1.id,
            'applicability': 'mandatory',
        })
        picking_in = self.PickingObj.create({
            'picking_type_id': self.picking_type_in.id,
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'project_id': self.project.id,
        })
        picking_in.picking_type_id.analytic_costs = True
        self.project[self.plan1_name] = False  # Remove the mandatory plan from the project linked to the picking
        self.MoveObj.create({
            'name': 'Move',
            'product_uom': self.uom_unit.id,
            'picking_id': picking_in.id,
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product2.id,
            'product_uom_qty': 5,
        })
        picking_in.action_confirm()
        with self.assertRaises(ValidationError):
            picking_in.button_validate()  # A missing mandatory plan is required on the project linked to the picking
