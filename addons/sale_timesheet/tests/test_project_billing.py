# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.sale_timesheet.tests.common import TestCommonSaleTimesheet
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestProjectBilling(TestCommonSaleTimesheet):
    """ This test suite provide checks for miscellaneous small things. """

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        # set up
        cls.employee_tde = cls.env['hr.employee'].create({
            'name': 'Employee TDE',
            'timesheet_cost': 42,
        })

        cls.partner_2 = cls.env['res.partner'].create({
            'name': 'Customer from the South',
            'email': 'customer.usd@south.com',
            'property_account_payable_id': cls.company_data['default_account_payable'].id,
            'property_account_receivable_id': cls.company_data['default_account_receivable'].id,
        })

        # Sale Order 1, no project/task created, used to timesheet at employee rate
        SaleOrder = cls.env['sale.order'].with_context(tracking_disable=True)
        SaleOrderLine = cls.env['sale.order.line'].with_context(tracking_disable=True)
        cls.sale_order_1 = SaleOrder.create({
            'partner_id': cls.partner_a.id,
            'partner_invoice_id': cls.partner_a.id,
            'partner_shipping_id': cls.partner_a.id,
        })

        cls.so1_line_order_no_task = SaleOrderLine.create({
            'name': cls.product_order_timesheet1.name,
            'product_id': cls.product_order_timesheet1.id,
            'product_uom_qty': 10,
            'product_uom': cls.product_order_timesheet1.uom_id.id,
            'price_unit': cls.product_order_timesheet1.list_price,
            'order_id': cls.sale_order_1.id,
        })

        cls.so1_line_deliver_no_task = SaleOrderLine.create({
            'name': cls.product_delivery_timesheet1.name,
            'product_id': cls.product_delivery_timesheet1.id,
            'product_uom_qty': 10,
            'product_uom': cls.product_delivery_timesheet1.uom_id.id,
            'price_unit': cls.product_delivery_timesheet1.list_price,
            'order_id': cls.sale_order_1.id,
        })
        # Sale Order 2, creates 2 project billed at task rate
        cls.sale_order_2 = SaleOrder.create({
            'partner_id': cls.partner_2.id,
            'partner_invoice_id': cls.partner_2.id,
            'partner_shipping_id': cls.partner_2.id,
        })
        cls.so2_line_deliver_project_task = SaleOrderLine.create({
            'order_id': cls.sale_order_2.id,
            'name': cls.product_delivery_timesheet3.name,
            'product_id': cls.product_delivery_timesheet3.id,
            'product_uom_qty': 5,
            'product_uom': cls.product_delivery_timesheet3.uom_id.id,
            'price_unit': cls.product_delivery_timesheet3.list_price
        })
        cls.so2_line_deliver_project_template = SaleOrderLine.create({
            'order_id': cls.sale_order_2.id,
            'name': cls.product_delivery_timesheet5.name,
            'product_id': cls.product_delivery_timesheet5.id,
            'product_uom_qty': 7,
            'product_uom': cls.product_delivery_timesheet5.uom_id.id,
            'price_unit': cls.product_delivery_timesheet5.list_price
        })
        cls.sale_order_2.action_confirm()

        # Projects: at least one per billable type
        Project = cls.env['project.project'].with_context(tracking_disable=True)
        cls.project_subtask = Project.create({
            'name': "Sub Task Project (non billable)",
            'allow_timesheets': True,
            'allow_billable': False,
            'partner_id': False,
        })
        cls.project_non_billable = Project.create({
            'name': "Non Billable Project",
            'allow_timesheets': True,
            'allow_billable': False,
            'partner_id': False,
            'subtask_project_id': cls.project_subtask.id,
        })
        cls.project_task_rate = cls.env['project.project'].search([('sale_line_id', '=', cls.so2_line_deliver_project_task.id)], limit=1)
        cls.project_task_rate2 = cls.env['project.project'].search([('sale_line_id', '=', cls.so2_line_deliver_project_template.id)], limit=1)

        cls.project_employee_rate = Project.create({
            'name': "Project billed at Employee Rate",
            'allow_timesheets': True,
            'allow_billable': True,
            'bill_type': 'customer_project',
            'pricing_type': 'employee_rate',
            'sale_order_id': cls.sale_order_1.id,
            'partner_id': cls.sale_order_1.partner_id.id,
            'subtask_project_id': cls.project_subtask.id,
        })
        cls.project_employee_rate_manager = cls.env['project.sale.line.employee.map'].create({
            'project_id': cls.project_employee_rate.id,
            'sale_line_id': cls.so1_line_order_no_task.id,
            'employee_id': cls.employee_manager.id,
        })
        cls.project_employee_rate_user = cls.env['project.sale.line.employee.map'].create({
            'project_id': cls.project_employee_rate.id,
            'sale_line_id': cls.so1_line_deliver_no_task.id,
            'employee_id': cls.employee_user.id,
        })

    def test_make_billable_at_task_rate(self):
        """ Starting from a non billable project, make it billable at task rate """
        Timesheet = self.env['account.analytic.line']
        Task = self.env['project.task']
        # set a customer on the project
        self.project_non_billable.write({
            'partner_id': self.partner_2.id
        })
        # create a task and 2 timesheets
        task = Task.with_context(default_project_id=self.project_non_billable.id).create({
            'name': 'first task',
            'partner_id': self.project_non_billable.partner_id.id,
            'planned_hours': 10,
        })
        timesheet1 = Timesheet.create({
            'name': 'Test Line',
            'project_id': task.project_id.id,
            'task_id': task.id,
            'unit_amount': 3,
            'employee_id': self.employee_manager.id,
        })
        timesheet2 = Timesheet.create({
            'name': 'Test Line tde',
            'project_id': task.project_id.id,
            'task_id': task.id,
            'unit_amount': 2,
            'employee_id': self.employee_tde.id,
        })

        # Change project to billable at task rate
        self.project_non_billable.write({
            'allow_billable': True,
            'bill_type': 'customer_project',
            'pricing_type': 'fixed_rate',
        })
        task.timesheet_product_id = self.product_delivery_timesheet3

        # create wizard
        wizard = self.env['project.create.sale.order'].with_context(active_id=self.project_non_billable.id, active_model='project.project').create({})

        self.assertEqual(wizard.partner_id, self.project_non_billable.partner_id, "The wizard should have the same partner as the project")
        self.assertEqual(len(wizard.line_ids), 1, "The wizard should have one line")
        self.assertEqual(wizard.line_ids.product_id, self.product_delivery_timesheet3, "The wizard should have one line with right product")

        # create the SO from the project
        action = wizard.action_create_sale_order()
        sale_order = self.env['sale.order'].browse(action['res_id'])

        self.assertEqual(sale_order.partner_id, self.project_non_billable.partner_id, "The customer of the SO should be the same as the project")
        self.assertEqual(len(sale_order.order_line), 1, "The SO should have 1 line")
        self.assertEqual(sale_order.order_line.product_id, wizard.line_ids.product_id, "The product of the only SOL should be the selected on the wizard")
        self.assertEqual(sale_order.order_line.project_id, self.project_non_billable, "SOL should be linked to the project")
        self.assertTrue(sale_order.order_line.task_id, "The SOL creates a task as they were no task already present in the project (system limitation)")
        self.assertEqual(sale_order.order_line.task_id.project_id, self.project_non_billable, "The created task should be in the project")
        self.assertEqual(sale_order.order_line.qty_delivered, timesheet1.unit_amount + timesheet2.unit_amount, "The create SOL should have an delivered quantity equals to the sum of tasks'timesheets")

    def test_make_billable_at_employee_rate(self):
        """ Starting from a non billable project, make it billable at employee rate """
        Timesheet = self.env['account.analytic.line']
        Task = self.env['project.task']
        # set a customer on the project
        self.project_non_billable.write({
            'partner_id': self.partner_2.id
        })
        # create a task and 2 timesheets
        task = Task.with_context(default_project_id=self.project_non_billable.id).create({
            'name': 'first task',
            'partner_id': self.project_non_billable.partner_id.id,
            'planned_hours': 10,
        })
        timesheet1 = Timesheet.create({
            'name': 'Test Line',
            'project_id': task.project_id.id,
            'task_id': task.id,
            'unit_amount': 3,
            'employee_id': self.employee_manager.id,
        })
        timesheet2 = Timesheet.create({
            'name': 'Test Line tde',
            'project_id': task.project_id.id,
            'task_id': task.id,
            'unit_amount': 2,
            'employee_id': self.employee_user.id,
        })

        # Change project to billable at employee rate
        self.project_non_billable.write({
            'allow_billable': True,
            'bill_type': 'customer_project',
            'pricing_type': 'employee_rate',
        })

        # create wizard
        wizard = self.env['project.create.sale.order'].with_context(active_id=self.project_non_billable.id, active_model='project.project').create({
            'partner_id': self.partner_2.id,
            'line_ids': [
                (0, 0, {'product_id': self.product_delivery_timesheet1.id, 'price_unit': 15, 'employee_id': self.employee_tde.id}),  # product creates no T
                (0, 0, {'product_id': self.product_delivery_timesheet1.id, 'price_unit': 15, 'employee_id': self.employee_manager.id}),  # product creates no T (same product than previous one)
                (0, 0, {'product_id': self.product_delivery_timesheet3.id, 'price_unit': self.product_delivery_timesheet3.list_price, 'employee_id': self.employee_user.id}),  # product creates new T in new P
            ]
        })

        self.assertEqual(wizard.partner_id, self.project_non_billable.partner_id, "The wizard should have the same partner as the project")
        self.assertEqual(wizard.project_id, self.project_non_billable, "The wizard'project should be the non billable project")

        # create the SO from the project
        action = wizard.action_create_sale_order()
        sale_order = self.env['sale.order'].browse(action['res_id'])

        self.assertEqual(sale_order.partner_id, self.project_non_billable.partner_id, "The customer of the SO should be the same as the project")
        self.assertEqual(len(sale_order.order_line), 2, "The SO should have 2 lines, as in wizard map there were 2 time the same product with the same price (for 2 different employees)")
        self.assertEqual(len(self.project_non_billable.sale_line_employee_ids), 3, "The project have 3 lines in its map")
        self.assertEqual(self.project_non_billable.sale_line_id, sale_order.order_line[0], "The wizard sets sale line fallbakc on project as the first of the list")
        self.assertEqual(task.sale_line_id, sale_order.order_line[0], "The wizard sets sale line fallback on tasks")
        self.assertEqual(task.partner_id, wizard.partner_id, "The wizard sets the customer on tasks to make SOL line field visible")

        line1 = sale_order.order_line.filtered(lambda sol: sol.product_id == self.product_delivery_timesheet1)
        line2 = sale_order.order_line.filtered(lambda sol: sol.product_id == self.product_delivery_timesheet3)

        self.assertTrue(line1, "Sale line 1 with product 1 should exists")
        self.assertTrue(line2, "Sale line 2 with product 3 should exists")

        self.assertFalse(line1.project_id, "Sale line 1 should be linked to the 'non billable' project")
        self.assertEqual(line2.project_id, self.project_non_billable, "Sale line 3 should be linked to the 'non billable' project")
        self.assertEqual(line1.price_unit, 15, "The unit price of SOL 1 should be 15")
        self.assertEqual(line1.product_uom_qty, 3, "The ordered qty of SOL 1 should be 3")
        self.assertEqual(line2.product_uom_qty, 2, "The ordered qty of SOL 2 should be 2")

        self.assertEqual(self.project_non_billable.sale_line_employee_ids.mapped('sale_line_id'), sale_order.order_line, "The SO lines of the map should be the same of the sales order")
        self.assertEqual(timesheet1.so_line, line1, "Timesheet1 should be linked to sale line 1, as employee manager create the timesheet")
        self.assertEqual(timesheet2.so_line, line2, "Timesheet2 should be linked to sale line 2, as employee tde create the timesheet")
        self.assertEqual(timesheet1.unit_amount, line1.qty_delivered, "Sale line 1 should have a delivered qty equals to the sum of its linked timesheets")
        self.assertEqual(timesheet2.unit_amount, line2.qty_delivered, "Sale line 2 should have a delivered qty equals to the sum of its linked timesheets")

    def test_billing_employee_rate(self):
        """ Check task and subtask creation, and timesheeting in a project billed at 'employee rate'. Then move the task into a 'task rate' project. """
        Task = self.env['project.task'].with_context(tracking_disable=True)
        Timesheet = self.env['account.analytic.line']

        # create a task
        task = Task.with_context(default_project_id=self.project_employee_rate.id).create({
            'name': 'first task',
            'partner_id': self.partner_a.id,
        })

        self.assertTrue(task.allow_billable, "Task in project 'employee rate' should be billable")
        self.assertEqual(task.bill_type, 'customer_project', "Task in project 'employee rate' should be billed at employee rate")
        self.assertEqual(task.pricing_type, 'employee_rate', "Task in project 'employee rate' should be billed at employee rate")
        self.assertFalse(task.sale_line_id, "Task created in a project billed on 'employee rate' should not be linked to a SOL")
        self.assertEqual(task.partner_id, task.project_id.partner_id, "Task created in a project billed on 'employee rate' should have the same customer as the one from the project")

        # log timesheet on task
        timesheet1 = Timesheet.create({
            'name': 'Test Line',
            'project_id': task.project_id.id,
            'task_id': task.id,
            'unit_amount': 50,
            'employee_id': self.employee_manager.id,
        })

        self.assertFalse(timesheet1.so_line, "The timesheet should be not linked to the project of the map entry since no SOL in the linked task.")

        task.write({
            'sale_line_id': self.project_employee_rate_user.sale_line_id.id
        })

        self.assertEqual(self.project_employee_rate_manager.sale_line_id, timesheet1.so_line, "The timesheet should be linked to the SOL associated to the Employee manager in the map")
        self.assertEqual(self.project_employee_rate_manager.project_id, timesheet1.project_id, "The timesheet should be linked to the project of the map entry")

        # create a subtask
        subtask = Task.with_context(default_project_id=self.project_employee_rate.subtask_project_id.id).create({
            'name': 'first subtask task',
            'parent_id': task.id,
        })

        self.assertFalse(subtask.allow_billable, "Subtask in non billable project should be non billable too")
        self.assertFalse(subtask.project_id.allow_billable, "The subtask project is non billable even if the subtask is")
        self.assertEqual(subtask.partner_id, subtask.parent_id.partner_id, "Subtask should have the same customer as the one from their mother")

        # log timesheet on subtask
        timesheet2 = Timesheet.create({
            'name': 'Test Line on subtask',
            'project_id': subtask.project_id.id,
            'task_id': subtask.id,
            'unit_amount': 50,
            'employee_id': self.employee_user.id,
        })

        self.assertEqual(subtask.project_id, timesheet2.project_id, "The timesheet is in the subtask project")
        self.assertNotEqual(self.project_employee_rate_user.project_id, timesheet2.project_id, "The timesheet should not be linked to the billing project for the map")
        self.assertFalse(timesheet2.so_line, "The timesheet should not be linked to SOL as the task is in a non billable project")

        # move task into task rate project
        task.write({
            'project_id': self.project_task_rate.id,
        })
        task._onchange_project()

        self.assertTrue(task.allow_billable, "Task in project 'task rate' should be billed at task rate")
        self.assertEqual(task.sale_line_id, self.project_task_rate.sale_line_id, "Task moved in a task rate billable project")
        self.assertEqual(task.partner_id, task.project_id.partner_id, "Task created in a project billed on 'employee rate' should have the same customer as the one from the project")

        # move subtask into task rate project
        subtask.write({
            'project_id': self.project_task_rate2.id,
        })

        self.assertTrue(task.allow_billable, "Subtask should keep the billable type from its parent, even when they are moved into another project")
        self.assertEqual(task.sale_line_id, self.project_task_rate.sale_line_id, "Subtask should keep the same sale order line than their mother, even when they are moved into another project")

        # create a second task in employee rate project
        task2 = Task.with_context(default_project_id=self.project_employee_rate.id).create({
            'name': 'first task',
            'partner_id': self.partner_a.id,
            'sale_line_id': False
        })

        # log timesheet on task in 'employee rate' project without any fallback (no map, no SOL on task, no SOL on project)
        timesheet3 = Timesheet.create({
            'name': 'Test Line',
            'project_id': task2.project_id.id,
            'task_id': task2.id,
            'unit_amount': 3,
            'employee_id': self.employee_tde.id,
        })

        self.assertFalse(timesheet3.so_line, "The timesheet should not be linked to SOL as there is no fallback at all (no map, no SOL on task, no SOL on project)")

        # log timesheet on task in 'employee rate' project (no map, no SOL on task, but SOL on project)
        timesheet4 = Timesheet.create({
            'name': 'Test Line ',
            'project_id': task2.project_id.id,
            'task_id': task2.id,
            'unit_amount': 4,
            'employee_id': self.employee_tde.id,
        })

        self.assertFalse(timesheet4.so_line, "The timesheet should not be linked to SOL, as no entry for TDE in project map")

    def test_billing_task_rate(self):
        """
        Check task and subtask creation, and timesheeting in a project billed at 'task rate'.
        Then move the task into a 'employee rate' project then, 'non billable'.
        """
        Task = self.env['project.task'].with_context(tracking_disable=True)
        Timesheet = self.env['account.analytic.line']

        # set subtask project on task rate project
        self.project_task_rate.write({'subtask_project_id': self.project_subtask.id})

        # create a task
        task = Task.with_context(default_project_id=self.project_task_rate.id).create({
            'name': 'first task',
        })
        task._onchange_project()

        self.assertEqual(task.sale_line_id, self.project_task_rate.sale_line_id, "Task created in a project billed on 'task rate' should be linked to a SOL of the project")
        self.assertEqual(task.partner_id, task.project_id.partner_id, "Task created in a project billed on 'employee rate' should have the same customer as the one from the project")

        # log timesheet on task
        timesheet1 = Timesheet.create({
            'name': 'Test Line',
            'project_id': task.project_id.id,
            'task_id': task.id,
            'unit_amount': 50,
            'employee_id': self.employee_manager.id,
        })

        self.assertEqual(self.project_task_rate.sale_line_id, timesheet1.so_line, "The timesheet should be linked to the SOL associated to the Employee manager in the map")

        # create a subtask
        subtask = Task.with_context(default_project_id=self.project_task_rate.subtask_project_id.id).create({
            'name': 'first subtask task',
            'parent_id': task.id,
        })

        self.assertEqual(subtask.partner_id, subtask.parent_id.partner_id, "Subtask should have the same customer as the one from their mother")

        # log timesheet on subtask
        timesheet2 = Timesheet.create({
            'name': 'Test Line on subtask',
            'project_id': subtask.project_id.id,
            'task_id': subtask.id,
            'unit_amount': 50,
            'employee_id': self.employee_user.id,
        })

        self.assertEqual(subtask.project_id, timesheet2.project_id, "The timesheet is in the subtask project")
        self.assertFalse(timesheet2.so_line, "The timesheet should not be linked to SOL as it's a non billable project")

        # move task and subtask into task rate project
        task.write({
            'project_id': self.project_employee_rate.id,
        })
        task._onchange_project()
        subtask.write({
            'project_id': self.project_employee_rate.id,
        })
        subtask._onchange_project()

        self.assertFalse(task.sale_line_id, "Task moved in a employee rate billable project have empty so line")
        self.assertEqual(task.partner_id, task.project_id.partner_id, "Task created in a project billed on 'employee rate' should have the same customer as the one from the project")

        self.assertFalse(subtask.sale_line_id, "Subask moved in a employee rate billable project have empty so line")
        self.assertEqual(subtask.partner_id, task.project_id.partner_id, "Subask created in a project billed on 'employee rate' should have the same customer as the one from the project")
