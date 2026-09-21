from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.sale_timesheet.tests.common import TestCommonSaleTimesheet


@tagged("-at_install", "post_install")
class TestSaleService(TestCommonSaleTimesheet):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.sale_order = cls.env["sale.order"].create(
            {
                "partner_id": cls.partner_a.id,
                "partner_invoice_id": cls.partner_a.id,
                "partner_shipping_id": cls.partner_a.id,
            }
        )

    def test_sale_service(self):
        sale_order_line = self.env["sale.order.line"].create(
            {
                "order_id": self.sale_order.id,
                "name": self.product_delivery_timesheet2.name,
                "product_id": self.product_delivery_timesheet2.id,
                "product_qty": 50,
            }
        )

        self.assertFalse(sale_order_line.product_readonly)
        self.sale_order.action_confirm()
        self.assertTrue(sale_order_line.product_readonly)
        self.assertEqual(
            self.sale_order.invoice_state,
            "to do",
            "Sale Service: a confirmed order whose delivered quantity is still "
            "zero is outstanding, not settled — c0180669ca0 made a line-level "
            "'no' that carries a quantity mean 'not yet' rather than 'never', "
            "so 'no' is now reserved for what will never be billed",
        )

        project = self.project_global
        task = project.task_ids.filtered(
            lambda t: (
                t.name
                == "%s - %s"
                % (self.sale_order.name, self.product_delivery_timesheet2.name)
            )
        )
        self.assertTrue(task, "Sale Service: task is not created, or it badly named")
        self.assertEqual(
            task.partner_id,
            self.sale_order.partner_id,
            "Sale Service: customer should be the same on task and on SO",
        )

        self.env["account.analytic.line"].create(
            {
                "name": "Test Line",
                "project_id": project.id,
                "task_id": task.id,
                "unit_amount": 50,
                "employee_id": self.employee_manager.id,
            }
        )
        self.assertEqual(
            self.sale_order.invoice_state,
            "to do",
            "Sale Service: there should be sale_ordermething to invoice after registering timesheets",
        )
        self.sale_order._create_invoices().action_post()

        self.assertTrue(
            sale_order_line.product_qty
            == sale_order_line.qty_transferred
            == sale_order_line.qty_invoiced,
            "Sale Service: line should be invoiced completely",
        )
        self.assertEqual(
            self.sale_order.invoice_state, "done", "Sale Service: SO should be invoiced"
        )
        self.assertEqual(
            self.sale_order.tasks_count,
            1,
            "A task should have been created on SO confirmation.",
        )

        product_service_task = self.env["product.product"].create(
            {
                "name": "Delivered Service",
                "standard_price": 30,
                "list_price": 90,
                "type": "service",
                "invoice_policy": "transferred",
                "uom_id": self.env.ref("uom.product_uom_hour").id,
                "default_code": "SERV-DELI",
                "service_type": "timesheet",
                "service_tracking": "task_global_project",
                "project_id": project.id,
            }
        )

        second_line = self.env["sale.order.line"].create(
            {
                "product_id": product_service_task.id,
                "product_qty": 10,
                "order_id": self.sale_order.id,
            }
        )

        self.assertEqual(
            self.sale_order.tasks_count,
            2,
            "Adding a new service line on a confirmer SO should create a new task.",
        )

        second_task = second_line.task_id
        self.assertTrue(
            second_task, "The second service line should have created a task."
        )
        second_task.timesheet_ids.unlink()
        second_task.unlink()
        self.assertFalse(
            second_line.task_id,
            "Deleting the task its should automatically unlink the task from SOL.",
        )

    def test_timesheet_uom(self):
        uom_days = self.env.ref("uom.product_uom_day")
        sale_order_line = self.env["sale.order.line"].create(
            {
                "order_id": self.sale_order.id,
                "product_id": self.product_delivery_timesheet3.id,
                "product_qty": 5,
                "product_uom_id": uom_days.id,
            }
        )
        self.sale_order.action_confirm()
        task = self.env["project.task"].search(
            [("sale_line_id", "=", sale_order_line.id)]
        )

        self.env["account.analytic.line"].create(
            {
                "name": "Test Line",
                "project_id": task.project_id.id,
                "task_id": task.id,
                "unit_amount": 16,
                "employee_id": self.employee_manager.id,
            }
        )
        self.assertEqual(
            sale_order_line.qty_transferred,
            2,
            "Sale: uom conversion of timesheets is wrong",
        )

        self.env["account.analytic.line"].create(
            {
                "name": "Test Line",
                "project_id": task.project_id.id,
                "task_id": task.id,
                "unit_amount": 24,
                "employee_id": self.employee_user.id,
            }
        )
        self.sale_order._create_invoices().action_post()
        self.assertEqual(
            self.sale_order.invoice_state,
            "done",
            'Sale Timesheet: "invoice on delivery" timesheets should not modify the invoice_state of the so',
        )

    def test_task_so_line_assignation(self):
        so_line_deliver_global_project = self.env["sale.order.line"].create(
            {
                "product_id": self.product_delivery_timesheet2.id,
                "product_qty": 10,
                "order_id": self.sale_order.id,
            }
        )
        self.sale_order.action_confirm()
        task_serv2 = self.env["project.task"].search(
            [("sale_line_id", "=", so_line_deliver_global_project.id)]
        )

        timesheets = self.env["account.analytic.line"]
        timesheets |= self.env["account.analytic.line"].create(
            {
                "name": "Test Line",
                "project_id": task_serv2.project_id.id,
                "task_id": task_serv2.id,
                "unit_amount": 4,
                "employee_id": self.employee_user.id,
            }
        )
        timesheets |= self.env["account.analytic.line"].create(
            {
                "name": "Test Line",
                "project_id": task_serv2.project_id.id,
                "task_id": task_serv2.id,
                "unit_amount": 1,
                "employee_id": self.employee_manager.id,
            }
        )
        self.assertTrue(
            all(
                billing_type == "billable_time"
                for billing_type in timesheets.mapped("timesheet_invoice_type")
            ),
            "All timesheets linked to the task should be on 'billable time'",
        )
        self.assertEqual(
            so_line_deliver_global_project.qty_to_invoice,
            5,
            "Quantity to invoice should have been increased when logging timesheet on delivered quantities task",
        )

        invoice = self.sale_order._create_invoices()[0]
        invoice.action_post()

        task_serv2.write({"sale_line_id": False})
        self.assertTrue(
            all(
                billing_type == "billable_time"
                for billing_type in timesheets.mapped("timesheet_invoice_type")
            ),
            "billable type of timesheet should not change when tranfering task into another project",
        )
        self.assertEqual(
            task_serv2.timesheet_ids.mapped("so_line"),
            so_line_deliver_global_project,
            "Old invoiced timesheet are not modified when changing the task SO line",
        )

        with self.assertRaises(UserError):
            timesheets.write({"so_line": False})

    def test_delivered_quantity(self):
        so_line_deliver_new_task_project = self.env["sale.order.line"].create(
            {
                "product_id": self.product_delivery_timesheet3.id,
                "product_qty": 10,
                "order_id": self.sale_order.id,
            }
        )
        self.sale_order.action_confirm()
        task_serv2 = self.env["project.task"].search(
            [("sale_line_id", "=", so_line_deliver_new_task_project.id)]
        )

        timesheet1 = self.env["account.analytic.line"].create(
            {
                "name": "Test Line",
                "project_id": task_serv2.project_id.id,
                "task_id": task_serv2.id,
                "unit_amount": 4,
                "employee_id": self.employee_user.id,
            }
        )
        self.assertEqual(
            so_line_deliver_new_task_project.qty_transferred,
            timesheet1.unit_amount,
            "Delivered quantity should be the same then its only related timesheet.",
        )

        timesheet1.unlink()
        self.assertEqual(
            so_line_deliver_new_task_project.qty_transferred,
            0.0,
            "Delivered quantity should be reset to zero, since there is no more timesheet.",
        )

        timesheet2 = self.env["account.analytic.line"].create(
            {
                "name": "Test Line 2",
                "project_id": task_serv2.project_id.id,
                "task_id": task_serv2.id,
                "unit_amount": 4,
                "employee_id": self.employee_user.id,
            }
        )
        timesheet3 = self.env["account.analytic.line"].create(
            {
                "name": "Test Line 3",
                "project_id": task_serv2.project_id.id,
                "task_id": task_serv2.id,
                "unit_amount": 2,
                "employee_id": self.employee_user.id,
            }
        )
        self.assertEqual(
            so_line_deliver_new_task_project.qty_transferred,
            timesheet2.unit_amount + timesheet3.unit_amount,
            "Delivered quantity should be the sum of the 2 timesheets unit amounts.",
        )

        timesheet2.unlink()
        self.assertEqual(
            so_line_deliver_new_task_project.qty_transferred,
            timesheet3.unit_amount,
            "Delivered quantity should be reset to the sum of remaining timesheets unit amounts.",
        )

    def test_sale_create_task(self):
        so_line1 = self.env["sale.order.line"].create(
            {
                "product_id": self.product_delivery_timesheet3.id,
                "product_qty": 7,
                "order_id": self.sale_order.id,
            }
        )

        self.sale_order.action_confirm()

        self.assertTrue(
            so_line1.task_id, "SO confirmation should create a task and link it to SOL"
        )
        self.assertTrue(
            so_line1.project_id,
            "SO confirmation should create a project and link it to SOL",
        )
        self.assertEqual(
            self.sale_order.tasks_count, 1, "The SO should have only one task"
        )
        self.assertEqual(
            so_line1.task_id.sale_line_id,
            so_line1,
            "The created task is also linked to its origin sale line, for invoicing purpose.",
        )
        self.assertFalse(
            so_line1.task_id.user_ids, "The created task should be unassigned"
        )
        self.assertEqual(
            so_line1.product_qty,
            so_line1.project_id.allocated_hours,
            "The planned hours on the project should be the same as the ordered quantity of the native SO line",
        )
        self.assertEqual(
            so_line1.product_qty,
            so_line1.task_id.planned_hours,
            "The planned hours on the task should be the same as the ordered quantity of the native SO line",
        )

        so_line1.write({"product_qty": 20})
        self.assertEqual(
            so_line1.product_qty,
            so_line1.task_id.planned_hours,
            "The planned hours should have changed when updating the ordered quantity of the native SO line",
        )

        self.sale_order._action_cancel()

        self.assertTrue(so_line1.task_id, "SO cancellation should keep the task")
        self.assertTrue(so_line1.project_id, "SO cancellation should create a project")
        self.assertEqual(
            self.sale_order.tasks_count, 1, "The SO should still have only one task"
        )
        self.assertEqual(
            so_line1.task_id.sale_line_id,
            so_line1,
            "The created task is also linked to its origin sale line, for invoicing purpose.",
        )

        so_line1.write({"product_qty": 30})
        self.assertEqual(
            so_line1.product_qty,
            so_line1.task_id.planned_hours,
            "The planned hours should have changed when updating the ordered quantity, even after SO cancellation",
        )

        self.sale_order.action_draft()
        self.sale_order.action_confirm()

        self.assertTrue(
            so_line1.task_id, "SO reconfirmation should not have create another task"
        )
        self.assertTrue(
            so_line1.project_id,
            "SO reconfirmation should bit have create another project",
        )
        self.assertEqual(
            self.sale_order.tasks_count, 1, "The SO should still have only one task"
        )
        self.assertEqual(
            so_line1.task_id.sale_line_id,
            so_line1,
            "The created task is also linked to its origin sale line, for invoicing purpose.",
        )

        self.sale_order.action_lock()
        with self.assertRaises(UserError):
            so_line1.write({"product_qty": 20})

    def test_sale_create_project(self):
        project_template2 = self.env["project.project"].create(
            {
                "name": "Second Project TEMPLATE for services",
                "allow_timesheets": True,
                "active": False,
            }
        )
        Stage = self.env["project.workflow.step"].with_context(
            default_project_id=project_template2.id
        )
        stage1_tmpl2 = Stage.create({"name": "Stage 1", "sequence": 1})
        stage2_tmpl2 = Stage.create({"name": "Stage 2", "sequence": 2})
        product_deli_ts_tmpl = self.env["product.product"].create(
            {
                "name": "Service delivered, create project only based on template B",
                "standard_price": 17,
                "list_price": 34,
                "type": "service",
                "invoice_policy": "transferred",
                "uom_id": self.env.ref("uom.product_uom_hour").id,
                "default_code": "SERV-DELI4",
                "service_type": "timesheet",
                "service_tracking": "project_only",
                "project_template_id": project_template2.id,
                "project_id": False,
                "taxes_id": False,
                "property_account_income_id": self.account_sale.id,
            }
        )

        so_line1 = self.env["sale.order.line"].create(
            {
                "product_id": self.product_delivery_timesheet5.id,
                "product_qty": 11,
                "order_id": self.sale_order.id,
            }
        )
        so_line2 = self.env["sale.order.line"].create(
            {
                "product_id": self.product_order_timesheet4.id,
                "product_qty": 10,
                "order_id": self.sale_order.id,
            }
        )
        so_line3 = self.env["sale.order.line"].create(
            {
                "product_id": self.product_delivery_timesheet5.id,
                "product_qty": 5,
                "order_id": self.sale_order.id,
            }
        )
        so_line4 = self.env["sale.order.line"].create(
            {
                "product_id": self.product_delivery_manual3.id,
                "product_qty": 4,
                "order_id": self.sale_order.id,
            }
        )
        so_line5 = self.env["sale.order.line"].create(
            {
                "product_id": product_deli_ts_tmpl.id,
                "product_qty": 8,
                "order_id": self.sale_order.id,
            }
        )

        self.sale_order.action_confirm()

        self.assertTrue(
            so_line1.project_id,
            "Line1 should have create a project based on template A",
        )
        self.assertTrue(
            so_line2.project_id, "Line2 should have create an empty project"
        )
        self.assertEqual(
            so_line3.project_id,
            so_line1.project_id,
            "Line3 should reuse project of line1",
        )
        self.assertEqual(
            so_line4.project_id,
            so_line2.project_id,
            "Line4 should reuse project of line2",
        )
        self.assertTrue(
            so_line4.task_id,
            "Line4 should have create a new task, even if no project created.",
        )
        self.assertTrue(
            so_line5.project_id,
            "Line5 should have create a project based on template B",
        )

        self.assertTrue(so_line1.project_id.active, "Project of Line1 should be active")
        self.assertTrue(so_line2.project_id.active, "Project of Line2 should be active")
        self.assertTrue(so_line5.project_id.active, "Project of Line5 should be active")

        self.assertTrue(
            so_line1.project_id in self.project_template_state.project_ids,
            "Stage 1 from template B should be part of project from so line 1",
        )
        self.assertTrue(
            so_line1.project_id in self.project_template_state.project_ids,
            "Stage 1 from template B should be part of project from so line 1",
        )

        self.assertTrue(
            so_line5.project_id in stage1_tmpl2.project_ids,
            "Stage 1 from template B should be part of project from so line 5",
        )
        self.assertTrue(
            so_line5.project_id in stage2_tmpl2.project_ids,
            "Stage 2 from template B should be part of project from so line 5",
        )

        self.assertTrue(
            so_line1.project_id.allow_timesheets,
            "Create project should allow timesheets",
        )
        self.assertTrue(
            so_line2.project_id.allow_timesheets,
            "Create project should allow timesheets",
        )
        self.assertTrue(
            so_line5.project_id.allow_timesheets,
            "Create project should allow timesheets",
        )

        self.assertEqual(
            so_line4.task_id.project_id,
            so_line2.project_id,
            "Task created with line 4 should have the project based on template A of the SO.",
        )

        self.assertEqual(
            so_line1.project_id.sale_line_id,
            so_line1,
            "SO line of project with template A should be the one that create it.",
        )
        self.assertEqual(
            so_line2.project_id.sale_line_id,
            so_line2,
            "SO line of project should be the one that create it.",
        )
        self.assertEqual(
            so_line5.project_id.sale_line_id,
            so_line5,
            "SO line of project with template B should be the one that create it.",
        )

    def test_sale_task_in_project_without_project(self):

        so_line1 = self.env["sale.order.line"].create(
            {
                "product_id": self.product_order_timesheet3.id,
                "product_qty": 10,
                "order_id": self.sale_order.id,
            }
        )

        self.product_order_timesheet3.write(
            {"project_template_id": self.project_template.id}
        )
        self.sale_order.action_confirm()
        self.product_order_timesheet3.write({"project_template_id": False})

        self.assertTrue(
            so_line1.task_id,
            "so_line1 should create a task as its product's service_tracking is set as 'task_in_project'",
        )
        self.assertNotEqual(
            so_line1.project_id,
            self.project_template,
            "so_line1 should create a new project and not directly use the configured template",
        )
        self.assertIn(
            self.project_template.name,
            so_line1.project_id.name,
            "The created project for so_line1 should use the configured template",
        )

    def test_billable_task_and_subtask(self):
        so_line_deliver_new_task_project = self.env["sale.order.line"].create(
            {
                "product_id": self.product_delivery_timesheet3.id,
                "product_qty": 10,
                "order_id": self.sale_order.id,
            }
        )
        so_line_deliver_new_task_project_2 = self.env["sale.order.line"].create(
            {
                "name": self.product_delivery_timesheet3.name + "(2)",
                "product_id": self.product_delivery_timesheet3.id,
                "product_qty": 10,
                "order_id": self.sale_order.id,
            }
        )
        self.sale_order.action_confirm()

        project = so_line_deliver_new_task_project.project_id
        task = so_line_deliver_new_task_project.task_id

        self.assertEqual(
            project.sale_line_id,
            so_line_deliver_new_task_project,
            "The created project should be linked to the so line",
        )
        self.assertEqual(
            task.sale_line_id,
            so_line_deliver_new_task_project,
            "The created task should be linked to the so line",
        )

        subtask = self.env["project.task"].create(
            {
                "parent_id": task.id,
                "project_id": project.id,
                "name": "%s: substask1" % (task.name,),
            }
        )
        task2 = self.env["project.task"].create(
            {"project_id": project.id, "name": "%s: substask1" % (task.name,)}
        )

        self.assertEqual(
            subtask.sale_line_id,
            task.sale_line_id,
            "By, default, a child task should have the same SO line as its mother",
        )
        self.assertEqual(
            task2.sale_line_id,
            project.sale_line_id,
            "A new task in a billable project should have the same SO line as its project",
        )
        self.assertEqual(
            task2.partner_id,
            so_line_deliver_new_task_project.partner_id,
            "A new task in a billable project should have the same SO line as its project",
        )

        subtask.write({"project_id": self.project_global.id})

        self.assertEqual(
            subtask.sale_line_id,
            task.sale_line_id,
            "A child task should always have the same SO line as its mother, even when changing project",
        )
        self.assertEqual(subtask.sale_line_id, so_line_deliver_new_task_project)

        task.write({"sale_line_id": so_line_deliver_new_task_project_2.id})

        self.assertEqual(
            subtask.sale_line_id,
            so_line_deliver_new_task_project,
            "A child task is not impacted by the change of SO line of its mother",
        )
        self.assertEqual(
            task.sale_line_id,
            so_line_deliver_new_task_project_2,
            "A mother task can have its SO line set manually",
        )

        subtask.write({"sale_line_id": so_line_deliver_new_task_project_2.id})

        self.assertEqual(
            subtask.sale_line_id,
            so_line_deliver_new_task_project_2,
            "A child can have its SO line set manually",
        )

    def test_change_ordered_qty(self):
        sale_order_line = self.env["sale.order.line"].create(
            {
                "order_id": self.sale_order.id,
                "product_id": self.product_delivery_timesheet2.id,
                "product_qty": 50,
            }
        )

        self.sale_order.action_confirm()
        self.assertEqual(
            sale_order_line.product_qty,
            sale_order_line.task_id.planned_hours,
            "The planned hours should be the same as the ordered quantity of the native SO line",
        )

        sale_order_line.write({"product_qty": 20})
        self.assertEqual(
            sale_order_line.product_qty,
            sale_order_line.task_id.planned_hours,
            "The planned hours should have changed when updating the ordered quantity of the native SO line",
        )

        self.sale_order._action_cancel()
        sale_order_line.write({"product_qty": 30})
        self.assertEqual(
            sale_order_line.product_qty,
            sale_order_line.task_id.planned_hours,
            "The planned hours should have changed when updating the ordered quantity, even after SO cancellation",
        )

        self.sale_order.action_lock()
        with self.assertRaises(UserError):
            sale_order_line.write({"product_qty": 20})

    def test_copy_billable_project_and_task(self):
        sale_order_line = self.env["sale.order.line"].create(
            {
                "order_id": self.sale_order.id,
                "product_id": self.product_delivery_timesheet3.id,
                "product_qty": 5,
            }
        )
        self.sale_order.action_confirm()
        task = self.env["project.task"].search(
            [("sale_line_id", "=", sale_order_line.id)]
        )
        project = sale_order_line.project_id

        project_copy = project.copy()
        self.assertFalse(
            project_copy.sale_line_id, "Duplicating project should erase its Sale line"
        )
        self.assertFalse(
            project_copy.sale_order_id,
            "Duplicating project should erase its Sale order",
        )
        self.assertEqual(
            len(project.task_ids),
            len(project_copy.task_ids),
            "Copied project must have the same number of tasks",
        )
        self.assertFalse(
            project_copy.task_ids.mapped("sale_line_id"),
            "The tasks of the duplicated project should not have a Sale Line set.",
        )

        task_copy = task.copy()
        self.assertEqual(
            task_copy.sale_line_id,
            task.sale_line_id,
            "Duplicating task should keep its Sale line",
        )

    def test_remaining_hours_prepaid_services(self):
        prepaid_service_sol = self.so.line_ids.filtered(
            lambda sol: sol.product_id.service_policy == "ordered_prepaid"
        )
        self.assertEqual(
            len(prepaid_service_sol),
            1,
            "It should only have one SOL with prepaid service product in this SO.",
        )
        self.assertEqual(
            prepaid_service_sol.remaining_hours,
            prepaid_service_sol.product_qty - prepaid_service_sol.qty_transferred,
            "The remaining hours of this SOL should be equal to the ordered quantity minus the delivered quantity.",
        )

        task = self.env["project.task"].create(
            {
                "name": "Test task",
                "project_id": self.project_task_rate.id,
            }
        )
        self.assertEqual(task.partner_id, self.project_task_rate.partner_id)
        self.assertEqual(task.partner_id, self.so.partner_id)
        self.assertEqual(task.remaining_hours_so, prepaid_service_sol.remaining_hours)

        self.env["account.analytic.line"].create(
            {
                "name": "Test Timesheet",
                "project_id": self.project_task_rate.id,
                "task_id": task.id,
                "unit_amount": 1,
                "employee_id": self.employee_user.id,
            }
        )
        self.assertEqual(
            task.remaining_hours_so,
            1,
            "Before the creation of a timesheet, the remaining hours was 2 hours, when we timesheet 1 hour, the remaining hours should be equal to 1 hour.",
        )
        self.assertEqual(
            prepaid_service_sol.remaining_hours,
            task.remaining_hours_so,
            "The remaining hours on the SOL should also be equal to 1 hour.",
        )

        task.update(
            {
                "sale_line_id": self.so.line_ids[0].id,
            }
        )
        self.assertEqual(
            task.remaining_hours_so,
            False,
            "Since the SOL doesn't contain a prepaid service product, the remaining_hours_so should be equal to False.",
        )
        self.assertEqual(
            prepaid_service_sol.remaining_hours,
            2,
            "Since the timesheet on task has the same SOL than the one in the task, the remaining_hours should increase of 1 hour to be equal to 2 hours.",
        )

        timesheet = self.env["account.analytic.line"].new(
            {
                "name": "Test Timesheet",
                "project_id": self.project_task_rate.id,
                "task_id": task.id,
                "unit_amount": 1,
                "so_line": prepaid_service_sol.id,
                "is_so_line_edited": True,
                "employee_id": self.employee_user.id,
            }
        )
        self.assertEqual(
            timesheet.so_line,
            prepaid_service_sol,
            "The SOL should be the same than one containing the prepaid service product.",
        )
        self.assertEqual(
            prepaid_service_sol.remaining_hours,
            2,
            "The remaining hours should not change.",
        )

    def test_several_uom_sol_to_planned_hours(self):
        allocated_hours_for_uom = {
            "day": 8.0,
            "hour": 1.0,
            "unit": 1.0,
        }

        project = self.project_global.copy({"task_ids": False})
        Product = self.env["product.product"]
        product_vals = {
            "type": "service",
            "service_type": "timesheet",
            "project_id": project.id,
            "service_tracking": "task_global_project",
        }

        SaleOrderLine = self.env["sale.order.line"]
        sol_vals = {
            "product_qty": 1,
            "price_unit": 100,
            "order_id": self.sale_order.id,
        }

        for uom_name in allocated_hours_for_uom:
            uom_id = self.env.ref("uom.product_uom_%s" % uom_name)

            product_vals.update(
                {
                    "name": uom_name,
                    "uom_id": uom_id.id,
                }
            )
            product = Product.create(product_vals)

            sol_vals.update(
                {
                    "name": uom_name,
                    "product_id": product.id,
                    "product_uom_id": uom_id.id,
                }
            )
            SaleOrderLine.create(sol_vals)

        self.sale_order.action_confirm()

        tasks = project.task_ids
        for task in tasks:
            self.assertEqual(
                task.planned_hours, allocated_hours_for_uom[task.sale_line_id.name]
            )

    def test_add_product_analytic_account(self):
        Product = self.env["product.product"]
        SaleOrderLine = self.env["sale.order.line"]

        product_create = Product.create(
            {
                "name": "Product that creates the task",
                "type": "service",
                "service_type": "timesheet",
                "project_id": self.project_global.id,
                "service_tracking": "task_global_project",
            }
        )
        sale_order_line_create = SaleOrderLine.create(
            {
                "order_id": self.sale_order.id,
                "name": product_create.name,
                "product_id": product_create.id,
                "product_qty": 5,
                "price_unit": product_create.list_price,
            }
        )
        self.sale_order.action_confirm()

        product_add = Product.create({"name": "Product added on task"})
        SaleOrderLine.create(
            {
                "order_id": self.sale_order.id,
                "name": product_add.name,
                "product_id": product_add.id,
                "product_qty": 5,
                "price_unit": product_add.list_price,
                "task_id": sale_order_line_create.task_id.id,
            }
        )
        self.sale_order._create_invoices()

        invoice_line = self.sale_order.invoice_ids.line_ids.filtered(
            lambda line: line.product_id == product_add
        )
        self.assertEqual(
            invoice_line.analytic_distribution,
            {str(self.project_global.account_id.id): 100},
            "SOL's analytic distribution should contain the project analytic account",
        )

    def test_sale_timesheet_invoice(self):
        so_line = self.env["sale.order.line"].create(
            {
                "product_id": self.product_delivery_timesheet2.id,
                "product_qty": 10,
                "order_id": self.sale_order.id,
            }
        )
        self.sale_order.action_confirm()

        timesheet = self.env["account.analytic.line"].create(
            {
                "name": "Test Line",
                "project_id": so_line.task_id.project_id.id,
                "task_id": so_line.task_id.id,
                "unit_amount": 5,
                "employee_id": self.employee_manager.id,
            }
        )

        self.assertFalse(timesheet.timesheet_invoice_id)
        invoice = self.sale_order._create_invoices()
        invoice.action_post()

        self.assertEqual(invoice, timesheet.timesheet_invoice_id)

    def test_prevent_update_project_allocated_hours_after_confirming_quotation(self):
        order_line = self.env["sale.order.line"].create(
            {
                "order_id": self.sale_order.id,
                "product_id": self.product_delivery_timesheet3.id,
                "product_qty": 8,
            }
        )
        self.sale_order.action_confirm()
        allocated_hours = order_line.project_id.allocated_hours
        order_line.product_qty = 10
        self.assertEqual(
            allocated_hours,
            order_line.project_id.allocated_hours,
            "Project allocated hours should not be changed.",
        )

    def test_different_uom_to_hours_on_sale_order_confirmation(self):

        self.env["sale.order.line"].create(
            [
                {
                    "order_id": self.sale_order.id,
                    "product_id": self.product_delivery_timesheet3.id,
                    "product_qty": 2,
                    "product_uom_id": self.env.ref("uom.product_uom_day").id,
                },
                {
                    "order_id": self.sale_order.id,
                    "product_id": self.product_delivery_timesheet3.id,
                    "product_qty": 8,
                    "product_uom_id": self.env.ref("uom.product_uom_hour").id,
                },
            ]
        )
        self.sale_order.action_confirm()
        allocated_hours = self.sale_order.project_ids.allocated_hours
        self.assertEqual(
            16 + 8,
            allocated_hours,
            "Project's allocated hours should add up correctly.",
        )

        self.env.company.hr_timesheet_config_id.timesheet_encode_uom_id = self.env.ref(
            "uom.product_uom_day"
        )
        so_copy = self.sale_order.copy()
        so_copy.action_confirm()
        self.assertEqual(
            allocated_hours,
            so_copy.project_ids.allocated_hours,
            "Timesheet encoding shouldn't affect hours allocated.",
        )

    def test_compute_project_and_task_button_with_ts(self):
        sale_order_1 = self.env["sale.order"].create(
            [
                {
                    "partner_id": self.partner_a.id,
                    "partner_invoice_id": self.partner_a.id,
                    "partner_shipping_id": self.partner_a.id,
                }
            ]
        )
        line_1 = self.env["sale.order.line"].create(
            {
                "product_id": self.product_service_delivered_timesheet.id,
                "order_id": sale_order_1.id,
            }
        )
        sale_order_1.action_confirm()
        self.assertTrue(
            sale_order_1.show_create_project_button,
            "There is a product service with the service_policy set on 'delivered on timesheet' on the sale order, the button should be displayed",
        )
        self.assertFalse(
            sale_order_1.show_project_button,
            "There is no project on the sale order, the button should be hidden",
        )
        line_1.project_id = self.project_global.id
        sale_order_1._compute_show_project_and_task_button()
        self.assertFalse(
            sale_order_1.show_create_project_button,
            "There is a product service with the service_policy set on 'delivered on timesheet' and a project on the sale order, the button should be hidden",
        )
        self.assertTrue(
            sale_order_1.show_project_button,
            "There is a product service with the service_policy set on 'delivered on timesheet' and a project on the sale order, the button should be displayed",
        )

    def test_compute_show_timesheet_button(self):
        sale_order_1, sale_order_2 = self.env["sale.order"].create(
            [
                {
                    "partner_id": self.partner_a.id,
                    "partner_invoice_id": self.partner_a.id,
                    "partner_shipping_id": self.partner_a.id,
                },
                {
                    "partner_id": self.partner_a.id,
                    "partner_invoice_id": self.partner_a.id,
                    "partner_shipping_id": self.partner_a.id,
                },
            ]
        )
        self.env["sale.order.line"].create(
            [
                {
                    "product_id": self.product_consumable.id,
                    "order_id": sale_order_1.id,
                },
                {
                    "product_id": self.product_service_delivered_milestone.id,
                    "order_id": sale_order_1.id,
                },
                {
                    "product_id": self.product_service_delivered_manual.id,
                    "order_id": sale_order_1.id,
                },
            ]
        )
        sale_order_1.action_confirm()
        self.assertFalse(
            sale_order_1.show_hours_recorded_button,
            "There is no service product service with the correct service_policy set on 'delivered on timesheet' on the sale order, the button should be hidden",
        )
        line_4 = self.env["sale.order.line"].create(
            {
                "product_id": self.product_service_delivered_timesheet.id,
                "order_id": sale_order_1.id,
            }
        )
        self.assertFalse(
            sale_order_1.show_hours_recorded_button,
            "There is a product service with the service_policy set on 'delivered on timesheet' but no project on the sale order, the button should be hidden",
        )
        line_4.project_id = self.project_global
        sale_order_1._compute_show_hours_recorded_button()
        self.assertTrue(
            sale_order_1.show_hours_recorded_button,
            "There is a product service with the service_policy set on 'delivered on timesheet' and a project on the sale order, the button should be displayed",
        )

        line_1 = self.env["sale.order.line"].create(
            {
                "product_id": self.product_service_ordered_prepaid.id,
                "order_id": sale_order_2.id,
            }
        )
        sale_order_2.action_confirm()
        self.assertFalse(
            sale_order_2.show_hours_recorded_button,
            "There is a product service with the service_policy set on 'delivered on timesheet' but no project on the sale order, the button should be hidden",
        )
        line_1.project_id = self.project_global
        sale_order_2._compute_show_hours_recorded_button()
        self.assertTrue(
            sale_order_2.show_hours_recorded_button,
            "There is a product service with the service_policy set on 'delivered on timesheet' and a project on the sale order, the button should be displayed",
        )
        line_1.project_id = False
        sale_order_2._compute_show_hours_recorded_button()
        self.assertFalse(
            sale_order_2.show_hours_recorded_button,
            "There is a product service with the service_policy set on 'delivered on timesheet' but no project on the sale order, the button should be hidden",
        )

        task = self.env["project.task"].create(
            {
                "name": "Test Task",
                "project_id": self.project_global.id,
                "sale_line_id": line_1.id,
            }
        )
        self.env["account.analytic.line"].create(
            {
                "name": "timesheet",
                "unit_amount": 5,
                "project_id": task.project_id.id,
                "task_id": task.id,
                "employee_id": self.employee_user.id,
            }
        )
        sale_order_2._compute_timesheet_count()
        sale_order_2._compute_show_hours_recorded_button()
        self.assertTrue(
            sale_order_2.show_hours_recorded_button,
            "There is a product service with the service_policy set on 'delivered on timesheet' and a project on the sale order, the button should be displayed",
        )

    def test_timesheet_hours_delivered_rounding(self):
        self.env["decimal.precision"].search([("name", "=", "Product Unit")]).digits = 0
        self.product_delivery_timesheet3.uom_id._invalidate_cache(["rounding"])
        self.env["sale.order.line"].create(
            {
                "name": self.product_delivery_timesheet3.name,
                "product_id": self.product_delivery_timesheet3.id,
                "product_qty": 10,
                "price_unit": self.product_delivery_timesheet3.list_price,
                "order_id": self.sale_order.id,
            }
        )

        for amount in (8.1, 8.5, 8.9):
            order = self.sale_order.copy()
            sol = order.line_ids
            order.action_confirm()

            self.env["account.analytic.line"].create(
                [
                    {
                        "name": "Test Line",
                        "project_id": sol.project_id.id,
                        "task_id": sol.task_id.id,
                        "unit_amount": amount,
                        "employee_id": self.employee_manager.id,
                    }
                ]
            )

            invoice = order._create_invoices()
            hours_delivered = sol._get_qty_delivered_by_analytic([])[sol.id]

            self.assertEqual(
                order.timesheet_total_duration,
                hours_delivered,
                f"{amount} hours delivered should round the same for SO & timesheet",
            )
            self.assertEqual(
                invoice.timesheet_total_duration,
                hours_delivered,
                f"{amount} hours delivered should round the same for invoice & timesheet",
            )

    def test_prepaid_pack_remaining_hours_rounding(self):
        uom_hour = self.env.ref("uom.product_uom_hour")
        pack20 = self.env["uom.uom"].create(
            {
                "name": "Pack of 20 Hours",
                "relative_factor": 20.0,
                "relative_uom_id": uom_hour.id,
            }
        )
        product = self.env["product.product"].create(
            {
                "name": "Prepaid Pack 20h",
                "type": "service",
                "uom_id": pack20.id,
                "service_type": "timesheet",
                "service_policy": "ordered_prepaid",
                "service_tracking": "task_in_project",
            }
        )
        order = self.env["sale.order"].create({"partner_id": self.partner_a.id})
        sol = self.env["sale.order.line"].create(
            {
                "order_id": order.id,
                "product_id": product.id,
                "product_qty": 1.0,
                "product_uom_id": pack20.id,
            }
        )
        order.action_confirm()
        self.env["account.analytic.line"].create(
            {
                "name": "Over-consumed timesheet",
                "project_id": sol.project_id.id,
                "task_id": sol.task_id.id,
                "unit_amount": 22.0,
                "employee_id": self.employee_user.id,
            }
        )
        sol.invalidate_recordset()
        self.assertAlmostEqual(sol.remaining_hours, -2.0, places=6)
        self.assertIn(
            "-02:00", sol.with_context(with_remaining_hours=True).display_name
        )
