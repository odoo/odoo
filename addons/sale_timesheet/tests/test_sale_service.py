# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.sale_timesheet.tests.common import TestCommonSaleTimesheet
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged


@tagged('-at_install', 'post_install')
class TestSaleService(TestCommonSaleTimesheet):
    """ This test suite provide checks for miscellaneous small things. """

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.sale_order = cls.env['sale.order'].with_context(mail_notrack=True, mail_create_nolog=True).create({
            'partner_id': cls.partner_a.id,
            'partner_invoice_id': cls.partner_a.id,
            'partner_shipping_id': cls.partner_a.id,
        })

    def test_sale_service(self):
        """ Test task creation when confirming a sale_order with the corresponding product """
        sale_order_line = self.env['sale.order.line'].create({
            'order_id': self.sale_order.id,
            'name': self.product_delivery_timesheet2.name,
            'product_id': self.product_delivery_timesheet2.id,
            'product_uom_qty': 50,
            'product_uom': self.product_delivery_timesheet2.uom_id.id,
            'price_unit': self.product_delivery_timesheet2.list_price
        })

        self.sale_order.order_line._compute_product_updatable()
        self.assertTrue(sale_order_line.product_updatable)
        self.sale_order.action_confirm()
        self.sale_order.order_line._compute_product_updatable()

        self.sale_order.action_confirm()
        self.sale_order.order_line._compute_product_updatable()
        self.assertFalse(sale_order_line.product_updatable)
        self.assertEqual(self.sale_order.invoice_status, 'no', 'Sale Service: there should be nothing to invoice after validation')

        # check task creation
        project = self.project_global
        task = project.task_ids.filtered(lambda t: t.name == '%s: %s' % (self.sale_order.name, self.product_delivery_timesheet2.name))
        self.assertTrue(task, 'Sale Service: task is not created, or it badly named')
        self.assertEqual(task.partner_id, self.sale_order.partner_id, 'Sale Service: customer should be the same on task and on SO')
        self.assertEqual(task.email_from, self.sale_order.partner_id.email, 'Sale Service: Task Email should be the same as the SO customer Email')

        # log timesheet on task
        self.env['account.analytic.line'].create({
            'name': 'Test Line',
            'project_id': project.id,
            'task_id': task.id,
            'unit_amount': 50,
            'employee_id': self.employee_manager.id,
        })
        self.assertEqual(self.sale_order.invoice_status, 'to invoice', 'Sale Service: there should be sale_ordermething to invoice after registering timesheets')
        self.sale_order._create_invoices()

        self.assertTrue(sale_order_line.product_uom_qty == sale_order_line.qty_delivered == sale_order_line.qty_invoiced, 'Sale Service: line should be invoiced completely')
        self.assertEqual(self.sale_order.invoice_status, 'invoiced', 'Sale Service: SO should be invoiced')
        self.assertEqual(self.sale_order.tasks_count, 1, "A task should have been created on SO confirmation.")

        # Add a line on the confirmed SO, and it should generate a new task directly
        product_service_task = self.env['product.product'].create({
            'name': "Delivered Service",
            'standard_price': 30,
            'list_price': 90,
            'type': 'service',
            'invoice_policy': 'delivery',
            'uom_id': self.env.ref('uom.product_uom_hour').id,
            'uom_po_id': self.env.ref('uom.product_uom_hour').id,
            'default_code': 'SERV-DELI',
            'service_type': 'timesheet',
            'service_tracking': 'task_global_project',
            'project_id': project.id
        })

        self.env['sale.order.line'].create({
            'name': product_service_task.name,
            'product_id': product_service_task.id,
            'product_uom_qty': 10,
            'product_uom': product_service_task.uom_id.id,
            'price_unit': product_service_task.list_price,
            'order_id': self.sale_order.id,
        })

        self.assertEqual(self.sale_order.tasks_count, 2, "Adding a new service line on a confirmer SO should create a new task.")

        # delete timesheets before deleting the task, so as to trigger the error
        # about linked sales order lines and not the one about linked timesheets
        task.timesheet_ids.unlink()
        # not possible to delete a task linked to a SOL
        with self.assertRaises(ValidationError):
            task.unlink()

    def test_timesheet_uom(self):
        """ Test timesheet invoicing and uom conversion """
        # create SO and confirm it
        uom_days = self.env.ref('uom.product_uom_day')
        sale_order_line = self.env['sale.order.line'].create({
            'order_id': self.sale_order.id,
            'name': self.product_delivery_timesheet3.name,
            'product_id': self.product_delivery_timesheet3.id,
            'product_uom_qty': 5,
            'product_uom': uom_days.id,
            'price_unit': self.product_delivery_timesheet3.list_price
        })
        self.sale_order.action_confirm()
        task = self.env['project.task'].search([('sale_line_id', '=', sale_order_line.id)])

        # let's log some timesheets
        self.env['account.analytic.line'].create({
            'name': 'Test Line',
            'project_id': task.project_id.id,
            'task_id': task.id,
            'unit_amount': 16,
            'employee_id': self.employee_manager.id,
        })
        self.assertEqual(sale_order_line.qty_delivered, 2, 'Sale: uom conversion of timesheets is wrong')

        self.env['account.analytic.line'].create({
            'name': 'Test Line',
            'project_id': task.project_id.id,
            'task_id': task.id,
            'unit_amount': 24,
            'employee_id': self.employee_user.id,
        })
        self.sale_order._create_invoices()
        self.assertEqual(self.sale_order.invoice_status, 'invoiced', 'Sale Timesheet: "invoice on delivery" timesheets should not modify the invoice_status of the so')

    def test_task_so_line_assignation(self):
        # create SO line and confirm it
        so_line_deliver_global_project = self.env['sale.order.line'].create({
            'name': self.product_delivery_timesheet2.name,
            'product_id': self.product_delivery_timesheet2.id,
            'product_uom_qty': 10,
            'product_uom': self.product_delivery_timesheet2.uom_id.id,
            'price_unit': self.product_delivery_timesheet2.list_price,
            'order_id': self.sale_order.id,
        })
        so_line_deliver_global_project.product_id_change()
        self.sale_order.action_confirm()
        task_serv2 = self.env['project.task'].search([('sale_line_id', '=', so_line_deliver_global_project.id)])

        # let's log some timesheets (on the project created by so_line_ordered_project_only)
        timesheets = self.env['account.analytic.line']
        timesheets |= self.env['account.analytic.line'].create({
            'name': 'Test Line',
            'project_id': task_serv2.project_id.id,
            'task_id': task_serv2.id,
            'unit_amount': 4,
            'employee_id': self.employee_user.id,
        })
        timesheets |= self.env['account.analytic.line'].create({
            'name': 'Test Line',
            'project_id': task_serv2.project_id.id,
            'task_id': task_serv2.id,
            'unit_amount': 1,
            'employee_id': self.employee_manager.id,
        })
        self.assertTrue(all([billing_type == 'billable_time' for billing_type in timesheets.mapped('timesheet_invoice_type')]), "All timesheets linked to the task should be on 'billable time'")
        self.assertEqual(so_line_deliver_global_project.qty_to_invoice, 5, "Quantity to invoice should have been increased when logging timesheet on delivered quantities task")

        # invoice SO, and validate invoice
        invoice = self.sale_order._create_invoices()[0]
        invoice.action_post()

        # make task non billable
        task_serv2.write({'sale_line_id': False})
        self.assertTrue(all([billing_type == 'billable_time' for billing_type in timesheets.mapped('timesheet_invoice_type')]), "billable type of timesheet should not change when tranfering task into another project")
        self.assertEqual(task_serv2.timesheet_ids.mapped('so_line'), so_line_deliver_global_project, "Old invoiced timesheet are not modified when changing the task SO line")

        # try to update timesheets, catch error 'You cannot modify invoiced timesheet'
        with self.assertRaises(UserError):
            timesheets.write({'so_line': False})

    def test_delivered_quantity(self):
        # create SO line and confirm it
        so_line_deliver_new_task_project = self.env['sale.order.line'].create({
            'name': self.product_delivery_timesheet3.name,
            'product_id': self.product_delivery_timesheet3.id,
            'product_uom_qty': 10,
            'product_uom': self.product_delivery_timesheet3.uom_id.id,
            'price_unit': self.product_delivery_timesheet3.list_price,
            'order_id': self.sale_order.id,
        })
        so_line_deliver_new_task_project.product_id_change()
        self.sale_order.action_confirm()
        task_serv2 = self.env['project.task'].search([('sale_line_id', '=', so_line_deliver_new_task_project.id)])

        # add a timesheet
        timesheet1 = self.env['account.analytic.line'].create({
            'name': 'Test Line',
            'project_id': task_serv2.project_id.id,
            'task_id': task_serv2.id,
            'unit_amount': 4,
            'employee_id': self.employee_user.id,
        })
        self.assertEqual(so_line_deliver_new_task_project.qty_delivered, timesheet1.unit_amount, 'Delivered quantity should be the same then its only related timesheet.')

        # remove the only timesheet
        timesheet1.unlink()
        self.assertEqual(so_line_deliver_new_task_project.qty_delivered, 0.0, 'Delivered quantity should be reset to zero, since there is no more timesheet.')

        # log 2 new timesheets
        timesheet2 = self.env['account.analytic.line'].create({
            'name': 'Test Line 2',
            'project_id': task_serv2.project_id.id,
            'task_id': task_serv2.id,
            'unit_amount': 4,
            'employee_id': self.employee_user.id,
        })
        timesheet3 = self.env['account.analytic.line'].create({
            'name': 'Test Line 3',
            'project_id': task_serv2.project_id.id,
            'task_id': task_serv2.id,
            'unit_amount': 2,
            'employee_id': self.employee_user.id,
        })
        self.assertEqual(so_line_deliver_new_task_project.qty_delivered, timesheet2.unit_amount + timesheet3.unit_amount, 'Delivered quantity should be the sum of the 2 timesheets unit amounts.')

        # remove timesheet2
        timesheet2.unlink()
        self.assertEqual(so_line_deliver_new_task_project.qty_delivered, timesheet3.unit_amount, 'Delivered quantity should be reset to the sum of remaining timesheets unit amounts.')

    def test_sale_create_task(self):
        """ Check that confirming SO create correctly a task, and reconfirming it does not create a second one. Also check changing
            the ordered quantity of a SO line that have created a task should update the planned hours of this task.
        """
        so_line1 = self.env['sale.order.line'].create({
            'name': self.product_delivery_timesheet3.name,
            'product_id': self.product_delivery_timesheet3.id,
            'product_uom_qty': 7,
            'product_uom': self.product_delivery_timesheet3.uom_id.id,
            'price_unit': self.product_delivery_timesheet3.list_price,
            'order_id': self.sale_order.id,
        })

        # confirm SO
        self.sale_order.action_confirm()

        self.assertTrue(so_line1.task_id, "SO confirmation should create a task and link it to SOL")
        self.assertTrue(so_line1.project_id, "SO confirmation should create a project and link it to SOL")
        self.assertEqual(self.sale_order.tasks_count, 1, "The SO should have only one task")
        self.assertEqual(so_line1.task_id.sale_line_id, so_line1, "The created task is also linked to its origin sale line, for invoicing purpose.")
        self.assertFalse(so_line1.task_id.user_ids, "The created task should be unassigned")
        self.assertEqual(so_line1.product_uom_qty, so_line1.task_id.planned_hours, "The planned hours should be the same as the ordered quantity of the native SO line")

        so_line1.write({'product_uom_qty': 20})
        self.assertEqual(so_line1.product_uom_qty, so_line1.task_id.planned_hours, "The planned hours should have changed when updating the ordered quantity of the native SO line")

        # cancel SO
        self.sale_order.action_cancel()

        self.assertTrue(so_line1.task_id, "SO cancellation should keep the task")
        self.assertTrue(so_line1.project_id, "SO cancellation should create a project")
        self.assertEqual(self.sale_order.tasks_count, 1, "The SO should still have only one task")
        self.assertEqual(so_line1.task_id.sale_line_id, so_line1, "The created task is also linked to its origin sale line, for invoicing purpose.")

        so_line1.write({'product_uom_qty': 30})
        self.assertEqual(so_line1.product_uom_qty, so_line1.task_id.planned_hours, "The planned hours should have changed when updating the ordered quantity, even after SO cancellation")

        # reconfirm SO
        self.sale_order.action_draft()
        self.sale_order.action_confirm()

        self.assertTrue(so_line1.task_id, "SO reconfirmation should not have create another task")
        self.assertTrue(so_line1.project_id, "SO reconfirmation should bit have create another project")
        self.assertEqual(self.sale_order.tasks_count, 1, "The SO should still have only one task")
        self.assertEqual(so_line1.task_id.sale_line_id, so_line1, "The created task is also linked to its origin sale line, for invoicing purpose.")

        self.sale_order.action_done()
        with self.assertRaises(UserError):
            so_line1.write({'product_uom_qty': 20})

    def test_sale_create_project(self):
        """ A SO with multiple product that should create project (with and without template) like ;
                Line 1 : Service 1 create project with Template A ===> project created with template A
                Line 2 : Service 2 create project no template ==> empty project created
                Line 3 : Service 3 create project with Template A ===> Don't create any project because line 1 has already created a project with template A
                Line 4 : Service 4 create project no template ==> Don't create any project because line 2 has already created an empty project
                Line 5 : Service 5 create project with Template B ===> project created with template B
        """
        # second project template and its associated product
        project_template2 = self.env['project.project'].create({
            'name': 'Second Project TEMPLATE for services',
            'allow_timesheets': True,
            'active': False,  # this template is archived
        })
        Stage = self.env['project.task.type'].with_context(default_project_id=project_template2.id)
        stage1_tmpl2 = Stage.create({
            'name': 'Stage 1',
            'sequence': 1
        })
        stage2_tmpl2 = Stage.create({
            'name': 'Stage 2',
            'sequence': 2
        })
        product_deli_ts_tmpl = self.env['product.product'].create({
            'name': "Service delivered, create project only based on template B",
            'standard_price': 17,
            'list_price': 34,
            'type': 'service',
            'invoice_policy': 'delivery',
            'uom_id': self.env.ref('uom.product_uom_hour').id,
            'uom_po_id': self.env.ref('uom.product_uom_hour').id,
            'default_code': 'SERV-DELI4',
            'service_type': 'timesheet',
            'service_tracking': 'project_only',
            'project_template_id': project_template2.id,
            'project_id': False,
            'taxes_id': False,
            'property_account_income_id': self.account_sale.id,
        })

        # create 5 so lines
        so_line1 = self.env['sale.order.line'].create({
            'name': self.product_delivery_timesheet5.name,
            'product_id': self.product_delivery_timesheet5.id,
            'product_uom_qty': 11,
            'product_uom': self.product_delivery_timesheet5.uom_id.id,
            'price_unit': self.product_delivery_timesheet5.list_price,
            'order_id': self.sale_order.id,
        })
        so_line2 = self.env['sale.order.line'].create({
            'name': self.product_order_timesheet4.name,
            'product_id': self.product_order_timesheet4.id,
            'product_uom_qty': 10,
            'product_uom': self.product_order_timesheet4.uom_id.id,
            'price_unit': self.product_order_timesheet4.list_price,
            'order_id': self.sale_order.id,
        })
        so_line3 = self.env['sale.order.line'].create({
            'name': self.product_delivery_timesheet5.name,
            'product_id': self.product_delivery_timesheet5.id,
            'product_uom_qty': 5,
            'product_uom': self.product_delivery_timesheet5.uom_id.id,
            'price_unit': self.product_delivery_timesheet5.list_price,
            'order_id': self.sale_order.id,
        })
        so_line4 = self.env['sale.order.line'].create({
            'name': self.product_delivery_manual3.name,
            'product_id': self.product_delivery_manual3.id,
            'product_uom_qty': 4,
            'product_uom': self.product_delivery_manual3.uom_id.id,
            'price_unit': self.product_delivery_manual3.list_price,
            'order_id': self.sale_order.id,
        })
        so_line5 = self.env['sale.order.line'].create({
            'name': product_deli_ts_tmpl.name,
            'product_id': product_deli_ts_tmpl.id,
            'product_uom_qty': 8,
            'product_uom': product_deli_ts_tmpl.uom_id.id,
            'price_unit': product_deli_ts_tmpl.list_price,
            'order_id': self.sale_order.id,
        })

        # confirm SO
        self.sale_order.action_confirm()

        # check each line has or no generate something
        self.assertTrue(so_line1.project_id, "Line1 should have create a project based on template A")
        self.assertTrue(so_line2.project_id, "Line2 should have create an empty project")
        self.assertEqual(so_line3.project_id, so_line1.project_id, "Line3 should reuse project of line1")
        self.assertEqual(so_line4.project_id, so_line2.project_id, "Line4 should reuse project of line2")
        self.assertTrue(so_line4.task_id, "Line4 should have create a new task, even if no project created.")
        self.assertTrue(so_line5.project_id, "Line5 should have create a project based on template B")

        # check all generated project should be active, even if the template is not
        self.assertTrue(so_line1.project_id.active, "Project of Line1 should be active")
        self.assertTrue(so_line2.project_id.active, "Project of Line2 should be active")
        self.assertTrue(so_line5.project_id.active, "Project of Line5 should be active")

        # check generated stuff are correct
        self.assertTrue(so_line1.project_id in self.project_template_state.project_ids, "Stage 1 from template B should be part of project from so line 1")
        self.assertTrue(so_line1.project_id in self.project_template_state.project_ids, "Stage 1 from template B should be part of project from so line 1")

        self.assertTrue(so_line5.project_id in stage1_tmpl2.project_ids, "Stage 1 from template B should be part of project from so line 5")
        self.assertTrue(so_line5.project_id in stage2_tmpl2.project_ids, "Stage 2 from template B should be part of project from so line 5")

        self.assertTrue(so_line1.project_id.allow_timesheets, "Create project should allow timesheets")
        self.assertTrue(so_line2.project_id.allow_timesheets, "Create project should allow timesheets")
        self.assertTrue(so_line5.project_id.allow_timesheets, "Create project should allow timesheets")

        self.assertEqual(so_line4.task_id.project_id, so_line2.project_id, "Task created with line 4 should have the project based on template A of the SO.")

        self.assertEqual(so_line1.project_id.sale_line_id, so_line1, "SO line of project with template A should be the one that create it.")
        self.assertEqual(so_line2.project_id.sale_line_id, so_line2, "SO line of project should be the one that create it.")
        self.assertEqual(so_line5.project_id.sale_line_id, so_line5, "SO line of project with template B should be the one that create it.")

    def test_sale_task_in_project_with_project(self):
        """ This will test the new 'task_in_project' service tracking correctly creates tasks and projects
            when a project_id is configured on the parent sale_order (ref task #1915660).

            Setup:
            - Configure a project_id on the SO
            - SO line 1: a product with its delivery tracking set to 'task_in_project'
            - SO line 2: the same product as SO line 1
            - SO line 3: a product with its delivery tracking set to 'project_only'
            - Confirm sale_order

            Expected result:
            - 2 tasks created on the project_id configured on the SO
            - 1 project created with the correct template for the 'project_only' product
        """

        self.sale_order.write({'project_id': self.project_global.id})
        self.sale_order._onchange_project_id()
        self.assertEqual(self.sale_order.analytic_account_id, self.analytic_account_sale, "Changing the project on the SO should set the analytic account accordingly.")

        so_line1 = self.env['sale.order.line'].create({
            'name': self.product_order_timesheet3.name,
            'product_id': self.product_order_timesheet3.id,
            'product_uom_qty': 11,
            'product_uom': self.product_order_timesheet3.uom_id.id,
            'price_unit': self.product_order_timesheet3.list_price,
            'order_id': self.sale_order.id,
        })
        so_line2 = self.env['sale.order.line'].create({
            'name': self.product_order_timesheet3.name,
            'product_id': self.product_order_timesheet3.id,
            'product_uom_qty': 10,
            'product_uom': self.product_order_timesheet3.uom_id.id,
            'price_unit': self.product_order_timesheet3.list_price,
            'order_id': self.sale_order.id,
        })
        so_line3 = self.env['sale.order.line'].create({
            'name': self.product_order_timesheet4.name,
            'product_id': self.product_order_timesheet4.id,
            'product_uom_qty': 5,
            'product_uom': self.product_order_timesheet4.uom_id.id,
            'price_unit': self.product_order_timesheet4.list_price,
            'order_id': self.sale_order.id,
        })

        # temporary project_template_id for our checks
        self.product_order_timesheet4.write({
            'project_template_id': self.project_template.id
        })
        self.sale_order.action_confirm()
        # remove it after the confirm because other tests don't like it
        self.product_order_timesheet4.write({
            'project_template_id': False
        })

        self.assertTrue(so_line1.task_id, "so_line1 should create a task as its product's service_tracking is set as 'task_in_project'")
        self.assertEqual(so_line1.task_id.project_id, self.project_global, "The project on so_line1's task should be project_global as configured on its parent sale_order")
        self.assertTrue(so_line2.task_id, "so_line2 should create a task as its product's service_tracking is set as 'task_in_project'")
        self.assertEqual(so_line2.task_id.project_id, self.project_global, "The project on so_line2's task should be project_global as configured on its parent sale_order")
        self.assertFalse(so_line3.task_id.name, "so_line3 should not create a task as its product's service_tracking is set as 'project_only'")
        self.assertNotEqual(so_line3.project_id, self.project_template, "so_line3 should create a new project and not directly use the configured template")
        self.assertIn(self.project_template.name, so_line3.project_id.name, "The created project for so_line3 should use the configured template")

    def test_sale_task_in_project_without_project(self):
        """ This will test the new 'task_in_project' service tracking correctly creates tasks and projects
            when the parent sale_order does NOT have a configured project_id (ref task #1915660).

            Setup:
            - SO line 1: a product with its delivery tracking set to 'task_in_project'
            - Confirm sale_order

            Expected result:
            - 1 project created with the correct template for the 'task_in_project' because the SO
              does not have a configured project_id
            - 1 task created from this new project
        """

        so_line1 = self.env['sale.order.line'].create({
            'name': self.product_order_timesheet3.name,
            'product_id': self.product_order_timesheet3.id,
            'product_uom_qty': 10,
            'product_uom': self.product_order_timesheet3.uom_id.id,
            'price_unit': self.product_order_timesheet3.list_price,
            'order_id': self.sale_order.id,
        })

        # temporary project_template_id for our checks
        self.product_order_timesheet3.write({
            'project_template_id': self.project_template.id
        })
        self.sale_order.action_confirm()
        # remove it after the confirm because other tests don't like it
        self.product_order_timesheet3.write({
            'project_template_id': False
        })

        self.assertTrue(so_line1.task_id, "so_line1 should create a task as its product's service_tracking is set as 'task_in_project'")
        self.assertNotEqual(so_line1.project_id, self.project_template, "so_line1 should create a new project and not directly use the configured template")
        self.assertIn(self.project_template.name, so_line1.project_id.name, "The created project for so_line1 should use the configured template")

    def test_billable_task_and_subtask(self):
        """ Test if subtasks and tasks are billed on the correct SO line """
        # create SO line and confirm it
        so_line_deliver_new_task_project = self.env['sale.order.line'].create({
            'name': self.product_delivery_timesheet3.name,
            'product_id': self.product_delivery_timesheet3.id,
            'product_uom_qty': 10,
            'product_uom': self.product_delivery_timesheet3.uom_id.id,
            'price_unit': self.product_delivery_timesheet3.list_price,
            'order_id': self.sale_order.id,
        })
        so_line_deliver_new_task_project_2 = self.env['sale.order.line'].create({
            'name': self.product_delivery_timesheet3.name + "(2)",
            'product_id': self.product_delivery_timesheet3.id,
            'product_uom_qty': 10,
            'product_uom': self.product_delivery_timesheet3.uom_id.id,
            'price_unit': self.product_delivery_timesheet3.list_price,
            'order_id': self.sale_order.id,
        })
        so_line_deliver_new_task_project.product_id_change()
        so_line_deliver_new_task_project_2.product_id_change()
        self.sale_order.action_confirm()

        project = so_line_deliver_new_task_project.project_id
        task = so_line_deliver_new_task_project.task_id

        self.assertEqual(project.sale_line_id, so_line_deliver_new_task_project, "The created project should be linked to the so line")
        self.assertEqual(task.sale_line_id, so_line_deliver_new_task_project, "The created task should be linked to the so line")

        # create a new task and subtask
        subtask = self.env['project.task'].create({
            'parent_id': task.id,
            'project_id': project.id,
            'name': '%s: substask1' % (task.name,),
        })
        task2 = self.env['project.task'].create({
            'project_id': project.id,
            'name': '%s: substask1' % (task.name,)
        })

        self.assertEqual(subtask.sale_line_id, task.sale_line_id, "By, default, a child task should have the same SO line as its mother")
        self.assertEqual(task2.sale_line_id, project.sale_line_id, "A new task in a billable project should have the same SO line as its project")
        self.assertEqual(task2.partner_id, so_line_deliver_new_task_project.order_partner_id, "A new task in a billable project should have the same SO line as its project")

        # moving subtask in another project
        subtask.write({'display_project_id': self.project_global.id})

        self.assertEqual(subtask.sale_line_id, task.sale_line_id, "A child task should always have the same SO line as its mother, even when changing project")
        self.assertEqual(subtask.sale_line_id, so_line_deliver_new_task_project)

        # changing the SO line of the mother task
        task.write({'sale_line_id': so_line_deliver_new_task_project_2.id})

        self.assertEqual(subtask.sale_line_id, so_line_deliver_new_task_project, "A child task is not impacted by the change of SO line of its mother")
        self.assertEqual(task.sale_line_id, so_line_deliver_new_task_project_2, "A mother task can have its SO line set manually")

        # changing the SO line of a subtask
        subtask.write({'sale_line_id': so_line_deliver_new_task_project_2.id})

        self.assertEqual(subtask.sale_line_id, so_line_deliver_new_task_project_2, "A child can have its SO line set manually")

    def test_change_ordered_qty(self):
        """ Changing the ordered quantity of a SO line that have created a task should update the planned hours of this task """
        sale_order_line = self.env['sale.order.line'].create({
            'order_id': self.sale_order.id,
            'name': self.product_delivery_timesheet2.name,
            'product_id': self.product_delivery_timesheet2.id,
            'product_uom_qty': 50,
            'product_uom': self.product_delivery_timesheet2.uom_id.id,
            'price_unit': self.product_delivery_timesheet2.list_price
        })

        self.sale_order.action_confirm()
        self.assertEqual(sale_order_line.product_uom_qty, sale_order_line.task_id.planned_hours, "The planned hours should be the same as the ordered quantity of the native SO line")

        sale_order_line.write({'product_uom_qty': 20})
        self.assertEqual(sale_order_line.product_uom_qty, sale_order_line.task_id.planned_hours, "The planned hours should have changed when updating the ordered quantity of the native SO line")

        self.sale_order.action_cancel()
        sale_order_line.write({'product_uom_qty': 30})
        self.assertEqual(sale_order_line.product_uom_qty, sale_order_line.task_id.planned_hours, "The planned hours should have changed when updating the ordered quantity, even after SO cancellation")

        self.sale_order.action_done()
        with self.assertRaises(UserError):
            sale_order_line.write({'product_uom_qty': 20})

    def test_copy_billable_project_and_task(self):
        sale_order_line = self.env['sale.order.line'].create({
            'order_id': self.sale_order.id,
            'name': self.product_delivery_timesheet3.name,
            'product_id': self.product_delivery_timesheet3.id,
            'product_uom_qty': 5,
            'product_uom': self.product_delivery_timesheet3.uom_id.id,
            'price_unit': self.product_delivery_timesheet3.list_price
        })
        self.sale_order.action_confirm()
        task = self.env['project.task'].search([('sale_line_id', '=', sale_order_line.id)])
        project = sale_order_line.project_id

        # copy the project
        project_copy = project.copy()
        self.assertFalse(project_copy.sale_line_id, "Duplicating project should erase its Sale line")
        self.assertFalse(project_copy.sale_order_id, "Duplicating project should erase its Sale order")
        self.assertEqual(len(project.tasks), len(project_copy.tasks), "Copied project must have the same number of tasks")
        self.assertFalse(project_copy.tasks.mapped('sale_line_id'), "The tasks of the duplicated project should not have a Sale Line set.")

        # copy the task
        task_copy = task.copy()
        self.assertEqual(task_copy.sale_line_id, task.sale_line_id, "Duplicating task should keep its Sale line")

    def test_remaining_hours_prepaid_services(self):
        """ Test if the remaining hours is correctly computed

            Test Case:
            =========
            1) Check the remaining hours in the SOL containing a prepaid service product,
            2) Create task in project with pricing type is equal to "task rate" and has the customer in the SO
                and check if the remaining hours is equal to the remaining hours in the SOL,
            3) Create timesheet in the task for this SOL and check if the remaining hours correctly decrease,
            4) Change the SOL in the task and see if the remaining hours is correctly recomputed.
            5) Create without storing the timesheet to check if remaining hours in SOL does not change.
        """
        # 1) Check the remaining hours in the SOL containing a prepaid service product
        prepaid_service_sol = self.so.order_line.filtered(lambda sol: sol.product_id.service_policy == 'ordered_timesheet')
        self.assertEqual(len(prepaid_service_sol), 1, "It should only have one SOL with prepaid service product in this SO.")
        self.assertEqual(prepaid_service_sol.remaining_hours, prepaid_service_sol.product_uom_qty - prepaid_service_sol.qty_delivered, "The remaining hours of this SOL should be equal to the ordered quantity minus the delivered quantity.")

        # 2) Create task in project with pricing type is equal to "task rate" and has the customer in the SO
        # and check if the remaining hours is equal to the remaining hours in the SOL,
        task = self.env['project.task'].create({
            'name': 'Test task',
            'project_id': self.project_task_rate.id,
        })
        self.assertEqual(task.partner_id, self.project_task_rate.partner_id)
        self.assertEqual(task.partner_id, self.so.partner_id)
        self.assertEqual(task.remaining_hours_so, prepaid_service_sol.remaining_hours)

        # 3) Create timesheet in the task for this SOL and check if the remaining hours correctly decrease
        self.env['account.analytic.line'].create({
            'name': 'Test Timesheet',
            'project_id': self.project_task_rate.id,
            'task_id': task.id,
            'unit_amount': 1,
        })
        self.assertEqual(task.remaining_hours_so, 1, "Before the creation of a timesheet, the remaining hours was 2 hours, when we timesheet 1 hour, the remaining hours should be equal to 1 hour.")
        self.assertEqual(prepaid_service_sol.remaining_hours, task.remaining_hours_so, "The remaining hours on the SOL should also be equal to 1 hour.")

        # 4) Change the SOL in the task and see if the remaining hours is correctly recomputed.
        task.update({
            'sale_line_id': self.so.order_line[0].id,
        })
        self.assertEqual(task.remaining_hours_so, False, "Since the SOL doesn't contain a prepaid service product, the remaining_hours_so should be equal to False.")
        self.assertEqual(prepaid_service_sol.remaining_hours, 2, "Since the timesheet on task has the same SOL than the one in the task, the remaining_hours should increase of 1 hour to be equal to 2 hours.")

        # 5) Create without storing the timesheet to check if remaining hours in SOL does not change
        timesheet = self.env['account.analytic.line'].new({
            'name': 'Test Timesheet',
            'project_id': self.project_task_rate.id,
            'task_id': task.id,
            'unit_amount': 1,
            'so_line': prepaid_service_sol.id,
            'is_so_line_edited': True,
        })
        self.assertEqual(timesheet.so_line, prepaid_service_sol, "The SOL should be the same than one containing the prepaid service product.")
        self.assertEqual(prepaid_service_sol.remaining_hours, 2, "The remaining hours should not change.")

    def test_several_uom_sol_to_planned_hours(self):
        planned_hours_for_uom = {
            'day': 8.0,
            'hour': 1.0,
            'unit': 1.0,
            'gram': 0.0,
        }

        Product = self.env['product.product']
        product_vals = {
            'type': 'service',
            'service_type': 'timesheet',
            'project_id': self.project_global.id,
            'service_tracking': 'task_global_project',
        }

        SaleOrderLine = self.env['sale.order.line']
        sol_vals = {
            'product_uom_qty': 1,
            'price_unit': 100,
            'order_id': self.sale_order.id,
        }

        self.project_global.task_ids = False
        for uom_name in planned_hours_for_uom:
            uom_id = self.env.ref('uom.product_uom_%s' % uom_name)

            product_vals.update({
                'name': uom_name,
                'uom_id': uom_id.id,
                'uom_po_id': uom_id.id,
            })
            product = Product.create(product_vals)

            sol_vals.update({
                'name': uom_name,
                'product_id': product.id,
                'product_uom': uom_id.id,
            })
            SaleOrderLine.create(sol_vals)

        self.sale_order.action_confirm()

        tasks = self.project_global.task_ids
        for task in tasks:
            self.assertEqual(task.planned_hours, planned_hours_for_uom[task.sale_line_id.name])

        project_updates_data = self.project_global._get_sold_items()['data']
        for datum in project_updates_data:
            # A datum looks like this: {'name': 'day', 'value': '0.0 / 8.0 Hours',...}
            uom_in = datum['name']

            # So the value looks like this: '0.0 / 8.0 Hours'
            # We extract the ordered quantity (second number in the string) and the displayed unit of measure
            values = datum['value'][6:].split(' ')
            qty = float(values[0])
            uom_out = values[1]

            # All uom but grams should have been converted to company's project time unit
            company_time_uom = self.env.company.project_time_mode_id
            if uom_in == 'gram':
                self.assertEqual(qty, 1.0)
                self.assertEqual(uom_out, self.env.ref('uom.product_uom_gram').display_name)
            else:
                self.assertEqual(qty, planned_hours_for_uom[uom_in])
                self.assertEqual(uom_out, company_time_uom.display_name)

    def test_add_product_analytic_account(self):
        """ When we have a project with an analytic account and we add a product to the task,
            the consequent invoice line should have the same analytic account as the project.
        """
        # Ensure the SO has no analytic account to give to its SOLs
        self.assertFalse(self.sale_order.analytic_account_id)
        Product = self.env['product.product']
        SaleOrderLine = self.env['sale.order.line']

        # Create a SO with a service that creates a task
        product_create = Product.create({
            'name': 'Product that creates the task',
            'type': 'service',
            'service_type': 'timesheet',
            'project_id': self.project_global.id,
            'service_tracking': 'task_global_project',
        })
        sale_order_line_create = SaleOrderLine.create({
            'order_id': self.sale_order.id,
            'name': product_create.name,
            'product_id': product_create.id,
            'product_uom_qty': 5,
            'product_uom': product_create.uom_id.id,
            'price_unit': product_create.list_price,
        })
        self.sale_order.action_confirm()

        # Add a SOL with a task_id to mimmic the "Add a product" flow on the task
        product_add = Product.create({'name': 'Product added on task'})
        SaleOrderLine.create({
            'order_id': self.sale_order.id,
            'name': product_add.name,
            'product_id': product_add.id,
            'product_uom_qty': 5,
            'product_uom': product_add.uom_id.id,
            'price_unit': product_add.list_price,
            'task_id': sale_order_line_create.task_id.id,
        })
        self.sale_order._create_invoices()

        # Check that the resulting invoice line and the project have the same analytic account
        invoice_line = self.sale_order.invoice_ids.line_ids.filtered(lambda line: line.product_id == product_add)
        self.assertEqual(invoice_line.analytic_account_id, self.project_global.analytic_account_id,
             "SOL's analytic account should be the same as the project's")

    def test_timesheet_hours_delivered_rounding(self):
        """
        Ensure hours are rounded consistently on SO & invoice.
        """
        self.env.company.project_time_mode_id.rounding = 1.0
        self.env['sale.order.line'].create({
            'name': self.product_delivery_timesheet3.name,
            'product_id': self.product_delivery_timesheet3.id,
            'product_uom_qty': 10,
            'product_uom': self.product_delivery_timesheet3.uom_id.id,
            'price_unit': self.product_delivery_timesheet3.list_price,
            'order_id': self.sale_order.id,
        })

        for amount in (8.1, 8.5, 8.9):
            order = self.sale_order.copy()
            sol = order.order_line
            order.action_confirm()

            self.env['account.analytic.line'].create([{
                'name': 'Test Line',
                'project_id': sol.project_id.id,
                'task_id': sol.task_id.id,
                'unit_amount': amount,
                'employee_id': self.employee_manager.id,
            }])

            invoice = order._create_invoices()
            hours_delivered = sol._get_delivered_quantity_by_analytic([])[sol.id]

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
