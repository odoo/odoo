# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo import Command, _
from odoo.tests import Form
from .common import TestMrpCommon


class TestReportMoOverview(TestMrpCommon):
    """Test suite for MO Overview report with employee tracking."""
    _test_user_groups = (
            'mrp.group_mrp_manager',
    )
    _test_user_name = 'Test MRP Workorder Manager'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create workcenter with default employee cost
        cls.workcenter = cls.env['mrp.workcenter'].create({
            'name': 'Test Workcenter',
            'employee_costs_hour': 30.0,
            'employee_ids': [
                Command.create({
                    'name': 'John Doe',
                    'pin': '1001',
                    'hourly_cost': 50.0}),
                Command.create({
                    'name': 'Jane Doe',
                    'pin': '1002',
                    'hourly_cost': 75.0})
            ]
        })
        cls.employee_1 = cls.workcenter.employee_ids[0]
        cls.employee_2 = cls.workcenter.employee_ids[1]

        # Create a product and BOM with operation
        cls.product = cls.env['product.product'].create({
            'name': 'Test Product',
            'is_storable': True,
        })
        cls.component = cls.env['product.product'].create({
            'name': 'Component',
            'is_storable': True,
        })
        cls.bom = cls.env['mrp.bom'].create({
            'product_tmpl_id': cls.product.product_tmpl_id.id,
            'product_qty': 1.0,
            'operation_ids': [
                Command.create({
                    'name': 'Operation 1',
                    'workcenter_id': cls.workcenter.id,
                    'time_cycle': 12,
                    'sequence': 1
                })
            ]
        })
        cls.env['mrp.bom.line'].create({
            'product_id': cls.component.id,
            'product_qty': 1.0,
            'bom_id': cls.bom.id
        })
        cls.env.user.write({'group_ids': [Command.link(cls.env.ref('mrp.group_mrp_routings').id)]})

    def test_report_with_employee_and_no_employee(self):
        """Test that the MO Overview report correctly displays workorder time entries
        with both employee and no employee cases.
        """
        # Create and confirm production order
        mo = self.env['mrp.production'].create({
            'bom_id': self.bom.id,
            'product_qty': 1.0,
        })
        mo.action_confirm()

        # Get the workorder
        workorder = mo.workorder_ids[0]
        self.assertTrue(workorder)

        # Add time entry with employee
        wo_form = Form(workorder)
        with wo_form.time_ids.new() as line:
            line.employee_id = self.employee_1
            line.date_start = datetime(2027, 1, 1, 10, 0, 0)
            line.date_end = datetime(2027, 1, 1, 11, 0, 0)
        wo_form.save()
        with wo_form.time_ids.new() as line:
            line.date_start = datetime(2027, 1, 1, 11, 0, 0)
            line.date_end = datetime(2027, 1, 1, 12, 0, 0)
        wo_form.save()

        # Get report data
        report_data = self.env['report.mrp.report_mo_overview']._get_finished_operation_data(mo)
        operations = report_data['details']

        # Verify we have the workorder, and two employee operations
        self.assertEqual(len(operations), 3, f"Expected 3 operations, got {len(operations)}")

        # Find operations by name pattern
        employee_operation = next(
            (op for op in operations if self.employee_1.display_name in op['name']),
            None
        )

        no_employee_label = _("Employee")
        no_employee_operation = next(
            (op for op in operations if no_employee_label in op['name']),
            None
        )

        # Verify the employee operation
        self.assertIsNotNone(employee_operation, "Operation with employee not found in report")
        self.assertIn(self.employee_1.display_name, employee_operation['name'])
        self.assertEqual(employee_operation['quantity'], 1.0)  # 60 minutes / 60
        self.assertEqual(employee_operation['unit_cost'], 50.0)

        # Verify the no-employee operation
        self.assertIsNotNone(no_employee_operation, "Operation without employee not found in report")
        self.assertIn(no_employee_label, no_employee_operation['name'])
        self.assertEqual(no_employee_operation['quantity'], 1.0)  # 60 minutes / 60
        self.assertEqual(no_employee_operation['unit_cost'], 30.0)

    def test_report_multiple_employees(self):
        """Test that the report correctly handles multiple employees
        with different costs in the same workorder.
        """
        # Create and confirm production order
        mo = self.env['mrp.production'].create({
            'bom_id': self.bom.id,
            'product_qty': 1.0,
        })
        mo.action_confirm()

        workorder = mo.workorder_ids[0]

        # Add time entries for both employees
        wo_form = Form(workorder)
        with wo_form.time_ids.new() as line:
            line.employee_id = self.employee_1
            line.date_start = datetime(2027, 1, 1, 10, 0, 0)
            line.date_end = datetime(2027, 1, 1, 11, 0, 0)
        with wo_form.time_ids.new() as line:
            line.employee_id = self.employee_2
            line.date_start = datetime(2027, 1, 1, 11, 0, 0)
            line.date_end = datetime(2027, 1, 1, 12, 30, 0)
        wo_form.save()

        # Get report data
        report_data = self.env['report.mrp.report_mo_overview']._get_finished_operation_data(mo)
        operations = report_data['details']

        # Find operations for both employees
        emp1_operations = [
            op for op in operations
            if self.employee_1.display_name in op['name']
        ]
        emp2_operations = [
            op for op in operations
            if self.employee_2.display_name in op['name']
        ]

        # Verify both employees have operations
        self.assertEqual(len(emp1_operations), 1, "Operations for employee 1 not found")
        self.assertEqual(len(emp2_operations), 1, "Operations for employee 2 not found")

        # Verify costs are correctly assigned
        emp1_op = emp1_operations[0]
        emp2_op = emp2_operations[0]
        self.assertEqual(emp1_op['unit_cost'], 50.0)
        self.assertEqual(emp2_op['unit_cost'], 75.0)
        self.assertEqual(emp1_op['quantity'], 1.0)
        self.assertEqual(emp2_op['quantity'], 1.5)  # 90 minutes / 60
