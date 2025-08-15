# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests import Form, new_test_user, tagged

from .common import TestSaleProjectCommon


@tagged('post_install', '-at_install')
class TestSaleProject(TestSaleProjectCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.analytic_plan = cls.env['account.analytic.plan'].create({
            'name': 'Plan Test',
        })
        cls.analytic_account_sale = cls.env['account.analytic.account'].create({
            'name': 'Project for selling timesheet - AA',
            'plan_id': cls.analytic_plan.id,
            'code': 'AA-2030'
        })

        # Create projects
        cls.project_global = cls.env['project.project'].create({
            'name': 'Global Project',
            'analytic_account_id': cls.analytic_account_sale.id,
            'allow_billable': True,
        })
        cls.project_template = cls.env['project.project'].create({
            'name': 'Project TEMPLATE for services',
        })
        cls.project_template_state = cls.env['project.task.type'].create({
            'name': 'Only stage in project template',
            'sequence': 1,
            'project_ids': [(4, cls.project_template.id)]
        })

        # Create service products
        uom_hour = cls.env.ref('uom.product_uom_hour')

        cls.product_order_service1 = cls.env['product.product'].create({
            'name': "Service Ordered, create no task",
            'standard_price': 11,
            'list_price': 13,
            'type': 'service',
            'invoice_policy': 'order',
            'uom_id': uom_hour.id,
            'uom_po_id': uom_hour.id,
            'default_code': 'SERV-ORDERED1',
            'service_tracking': 'no',
            'project_id': False,
        })
        cls.product_order_service2 = cls.env['product.product'].create({
            'name': "Service Ordered, create task in global project",
            'standard_price': 30,
            'list_price': 90,
            'type': 'service',
            'invoice_policy': 'order',
            'uom_id': uom_hour.id,
            'uom_po_id': uom_hour.id,
            'default_code': 'SERV-ORDERED2',
            'service_tracking': 'task_global_project',
            'project_id': cls.project_global.id,
        })
        cls.product_order_service3 = cls.env['product.product'].create({
            'name': "Service Ordered, create task in new project",
            'standard_price': 10,
            'list_price': 20,
            'type': 'service',
            'invoice_policy': 'order',
            'uom_id': uom_hour.id,
            'uom_po_id': uom_hour.id,
            'default_code': 'SERV-ORDERED3',
            'service_tracking': 'task_in_project',
            'project_id': False,  # will create a project
        })
        cls.product_order_service4 = cls.env['product.product'].create({
            'name': "Service Ordered, create project only",
            'standard_price': 15,
            'list_price': 30,
            'type': 'service',
            'invoice_policy': 'order',
            'uom_id': uom_hour.id,
            'uom_po_id': uom_hour.id,
            'default_code': 'SERV-ORDERED4',
            'service_tracking': 'project_only',
            'project_id': False,
        })

        # Create partner
        cls.partner = cls.env['res.partner'].create({'name': "Mur en béton"})

    def test_sale_order_with_project_task(self):
        SaleOrder = self.env['sale.order'].with_context(tracking_disable=True)
        SaleOrderLine = self.env['sale.order.line'].with_context(tracking_disable=True)

        sale_order = SaleOrder.create({
            'partner_id': self.partner.id,
            'partner_invoice_id': self.partner.id,
            'partner_shipping_id': self.partner.id,
        })
        so_line_order_no_task = SaleOrderLine.create({
            'product_id': self.product_order_service1.id,
            'product_uom_qty': 10,
            'order_id': sale_order.id,
        })

        so_line_order_task_in_global = SaleOrderLine.create({
            'product_id': self.product_order_service2.id,
            'product_uom_qty': 10,
            'order_id': sale_order.id,
        })

        so_line_order_new_task_new_project = SaleOrderLine.create({
            'product_id': self.product_order_service3.id,
            'product_uom_qty': 10,
            'order_id': sale_order.id,
        })

        so_line_order_only_project = SaleOrderLine.create({
            'product_id': self.product_order_service4.id,
            'product_uom_qty': 10,
            'order_id': sale_order.id,
        })
        sale_order.action_confirm()

        # service_tracking 'no'
        self.assertFalse(so_line_order_no_task.project_id, "The project should not be linked to no task product")
        self.assertFalse(so_line_order_no_task.task_id, "The task should not be linked to no task product")
        # service_tracking 'task_global_project'
        self.assertFalse(so_line_order_task_in_global.project_id, "Only task should be created, project should not be linked")
        self.assertEqual(self.project_global.tasks.sale_line_id, so_line_order_task_in_global, "Global project's task should be linked to so line")
        #  service_tracking 'task_in_project'
        self.assertTrue(so_line_order_new_task_new_project.project_id, "Sales order line should be linked to newly created project")
        self.assertTrue(so_line_order_new_task_new_project.task_id, "Sales order line should be linked to newly created task")
        # service_tracking 'project_only'
        self.assertFalse(so_line_order_only_project.task_id, "Task should not be created")
        self.assertTrue(so_line_order_only_project.project_id, "Sales order line should be linked to newly created project")

        self.assertEqual(self.env['sale.order'].search([('tasks_ids', 'in', so_line_order_new_task_new_project.task_id.ids)]), sale_order)
        self.assertEqual(self.env['sale.order'].search([('tasks_ids', '=', so_line_order_new_task_new_project.task_id.id)]), sale_order)
        self.assertEqual(self.env['sale.order'].search([('tasks_ids', 'any', [('project_id', '=', so_line_order_new_task_new_project.project_id.id)])]), sale_order)
        self.assertEqual(self.env['sale.order'].search([('tasks_ids.project_id', '=', so_line_order_new_task_new_project.project_id.id)]), sale_order)

        self.assertEqual(self.project_global._get_sale_order_items(), self.project_global.sale_line_id | self.project_global.tasks.sale_line_id, 'The _get_sale_order_items should returns all the SOLs linked to the project and its active tasks.')

        sale_order_2 = SaleOrder.create({
            'partner_id': self.partner.id,
            'partner_invoice_id': self.partner.id,
            'partner_shipping_id': self.partner.id,
        })
        sale_line_1_order_2 = SaleOrderLine.create({
            'product_id': self.product_order_service1.id,
            'product_uom_qty': 10,
            'product_uom': self.product_order_service1.uom_id.id,
            'price_unit': self.product_order_service1.list_price,
            'order_id': sale_order_2.id,
        })
        section_sale_line_order_2 = SaleOrderLine.create({
            'display_type': 'line_section',
            'name': 'Test Section',
            'order_id': sale_order_2.id,
        })
        note_sale_line_order_2 = SaleOrderLine.create({
            'display_type': 'line_note',
            'name': 'Test Note',
            'order_id': sale_order_2.id,
        })
        sale_order_2.action_confirm()
        task = self.env['project.task'].create({
            'name': 'Task',
            'sale_line_id': sale_line_1_order_2.id,
            'project_id': self.project_global.id,
        })
        self.assertEqual(task.sale_line_id, sale_line_1_order_2)
        self.assertIn(task.sale_line_id, self.project_global._get_sale_order_items())
        self.assertEqual(self.project_global._get_sale_orders(), sale_order | sale_order_2)

        sale_order_lines = sale_order.order_line + sale_line_1_order_2  # exclude the Section and Note Sales Order Items
        sale_items_data = self.project_global._get_sale_items(with_action=False)
        self.assertEqual(sale_items_data['total'], len(sale_order_lines - so_line_order_new_task_new_project - so_line_order_only_project),
                         "Should be all the sale items linked to the global project.")
        expected_sale_line_dict = {
            sol_read['id']: sol_read
            for sol_read in sale_order_lines.read(['display_name', 'product_uom_qty', 'qty_delivered', 'qty_invoiced', 'product_uom'])
        }
        actual_sol_ids = []
        for line in sale_items_data['data']:
            sol_id = line['id']
            actual_sol_ids.append(sol_id)
            self.assertIn(sol_id, expected_sale_line_dict)
            self.assertDictEqual(line, expected_sale_line_dict[sol_id])
        self.assertNotIn(section_sale_line_order_2.id, actual_sol_ids, 'The section Sales Order Item should not be takken into account in the Sales section of project.')
        self.assertNotIn(note_sale_line_order_2.id, actual_sol_ids, 'The note Sales Order Item should not be takken into account in the Sales section of project.')

    def test_sol_product_type_update(self):
        sale_order = self.env['sale.order'].with_context(tracking_disable=True).create({
            'partner_id': self.partner.id,
            'partner_invoice_id': self.partner.id,
            'partner_shipping_id': self.partner.id,
        })
        self.product_order_service3.type = 'consu'
        sale_order_line = self.env['sale.order.line'].create({
            'order_id': sale_order.id,
            'name': self.product_order_service3.name,
            'product_id': self.product_order_service3.id,
            'product_uom_qty': 5,
            'product_uom': self.product_order_service3.uom_id.id,
            'price_unit': self.product_order_service3.list_price
        })
        self.assertFalse(sale_order_line.is_service, "As the product is consumable, the SOL should not be a service")

        self.product_order_service3.type = 'service'
        self.assertTrue(sale_order_line.is_service, "As the product is a service, the SOL should be a service")

    def test_cancel_so_linked_to_project(self):
        """ Test that cancelling a SO linked to a project will not raise an error """
        # Ensure user don't have edit right access to the project
        group_sale_manager = self.env.ref('sales_team.group_sale_manager')
        group_project_user = self.env.ref('project.group_project_user')
        self.env.user.write({'groups_id': [(6, 0, [group_sale_manager.id, group_project_user.id])]})
        sale_order = self.env['sale.order'].with_context(tracking_disable=True).create({
            'partner_id': self.partner.id,
            'partner_invoice_id': self.partner.id,
            'partner_shipping_id': self.partner.id,
            'project_id': self.project_global.id,
        })
        sale_order_line = self.env['sale.order.line'].create({
            'name': self.product_order_service2.name,
            'product_id': self.product_order_service2.id,
            'order_id': sale_order.id,
        })
        self.assertFalse(self.project_global.tasks.sale_line_id, "The project tasks should not be linked to the SOL")

        sale_order.action_confirm()
        self.assertEqual(self.project_global.tasks.sale_line_id.id, sale_order_line.id, "The project tasks should be linked to the SOL from the SO")
        #use of sudo() since the env.user does not have the access right to edit projects.
        self.project_global.sudo().sale_line_id = sale_order_line
        sale_order.with_context({'disable_cancel_warning': True}).action_cancel()
        self.assertFalse(self.project_global.sale_line_id, "The project should not be linked to the SOL anymore")

    def test_links_with_sale_order_line(self):
        """
            Check that the subtasks are linked to the correct sale order line.
        """
        product_A, product_B, product_C = self.env['product.product'].create([
            {
                'name': 'product_A',
                'lst_price': 100.0,
                'detailed_type': 'service',
                'service_tracking': 'task_in_project',
            },
            {
                'name': 'product_B',
                'lst_price': 100.0,
                'detailed_type': 'service',
                'service_tracking': 'task_in_project',
            },
            {
                'name': 'product_C',
                'lst_price': 100.0,
                'detailed_type': 'service',
                'service_tracking': 'task_in_project',
            },
        ])
        sale_order_first, sale_order_second = self.env['sale.order'].create([
            {
                'partner_id': self.partner.id,
                'order_line': [
                    Command.create({'product_id': product_A.id}),
                    Command.create({'product_id': product_B.id}),
                ]
            },
            {
                'partner_id': self.partner.id,
                'order_line': [
                    Command.create({'product_id': product_C.id}),
                ]
            }
        ])
        (sale_order_first + sale_order_second).action_confirm()

        sale_order_line_A = sale_order_first.order_line.filtered(lambda sol: sol.product_id == product_A)
        sale_order_line_B = sale_order_first.order_line - sale_order_line_A
        sale_order_line_C = sale_order_second.order_line

        project_first = sale_order_first.project_ids
        project_second = sale_order_second.project_ids

        task_A = sale_order_first.tasks_ids.filtered(lambda task: task.sale_line_id == sale_order_line_A)
        task_B = sale_order_first.tasks_ids - task_A
        task_C = sale_order_second.tasks_ids

        # [CASE 1] Parent in the same project --> use parent's sale order line
        task_A.write({
            'child_ids': [
                Command.create({'name': 'Sub A in first project', 'project_id': project_first.id}),
            ]
        })
        task_B.write({
            'child_ids': [
                Command.create({'name': 'Sub B in first project', 'project_id': project_first.id}),
            ]
        })
        task_C.write({
            'child_ids': [
                Command.create({'name': 'Sub C in second project', 'project_id': project_second.id}),
            ]
        })
        self.assertEqual(task_A.child_ids.sale_line_id, sale_order_line_A)
        self.assertEqual(task_B.child_ids.sale_line_id, sale_order_line_B)
        self.assertEqual(task_C.child_ids.sale_line_id, sale_order_line_C)

        # [CASE 2] Parent in an other project --> use parent's sale_order line
        task_B.write({
            'child_ids': [
                Command.create({'name': 'Sub B in second project', 'project_id': project_second.id}),
            ]
        })
        sub_B_second = task_B.child_ids.filtered(lambda sub: sub.name == 'Sub B in second project')
        self.assertEqual(sub_B_second.sale_line_id, sale_order_line_B)

        # [CASE 3] Without project --> no sale order line defined
        task_B.write({
            'child_ids': [
                Command.create({'name': 'Sub B without project'}),
            ]
        })
        sub_B_without = task_B.child_ids.filtered(lambda sub: sub.name == 'Sub B without project')
        self.assertEqual(sub_B_without.sale_line_id, task_B.sale_line_id)

        # [CASE 4] Without parent --> use sale order line of the project
        task_D = self.env['project.task'].create({
            'name': 'Task D',
            'project_id': project_first.id,
        })
        self.assertEqual(task_D.sale_line_id, project_first.sale_line_id)

    def test_compute_project_and_task_button(self):
        """
            Ensures that when a sale order has at least one sol with a service product whose service-policy is either delivered on milestone or ordered prepaid, then the
            show_create_project_button is set to True. If the sale order also has one project linked to it, then the show_project_and_task_button should be True, and the show_create_button
            should be updated to False
        """
        sale_order_1 = self.env['sale.order'].with_context(tracking_disable=True).create({
            'partner_id': self.partner.id,
            'partner_invoice_id': self.partner.id,
            'partner_shipping_id': self.partner.id,
        })
        sale_order_2 = sale_order_1.copy()
        sale_order_3 = sale_order_1.copy()
        (sale_order_1 | sale_order_2 | sale_order_3).action_confirm()
        # consumable product, manual service product
        self.env['sale.order.line'].create([{
            'product_id': self.product_consumable.id,
            'order_id': sale_order_1.id,
        }])
        self.assertFalse(sale_order_1.show_create_project_button, "There is no service product with one of the correct service_policy on the sale order, the button should be hidden")
        self.assertFalse(sale_order_1.show_project_button, "There is no project on the sale order, the button should be hidden")
        self.assertFalse(sale_order_1.show_task_button, "There is no project on the sale order, the button should be hidden")
        # add a milestone product
        line_delivered_milestone = self.env['sale.order.line'].create({
            'product_id': self.product_service_delivered_milestone.id,
            'order_id': sale_order_1.id,
        })
        # the user does not have project creation right
        user_wrong_group = new_test_user(self.env, groups='sales_team.group_sale_manager,project.group_project_user', login='wendy', name='wendy')
        sale_order_1.with_user(user_wrong_group)._compute_show_project_and_task_button()
        self.assertFalse(sale_order_1.show_create_project_button, "The user does not have the right to create a new project, the button should be hidden")
        self.assertFalse(sale_order_1.show_project_button, "There is no project on the sale order, the button should be hidden")
        self.assertFalse(sale_order_1.show_task_button, "There is no project on the sale order, the button should be hidden")
        # the user has project creation right
        sale_order_1._compute_show_project_and_task_button()
        self.assertTrue(sale_order_1.show_create_project_button, "There is a product service with the service_policy set on 'delivered on milestone' on the sale order, the button should be displayed")
        self.assertFalse(sale_order_1.show_project_button, "There is no project on the sale order, the button should be hidden")
        self.assertFalse(sale_order_1.show_task_button, "There is no project on the sale order, the button should be hidden")
        # add a project to the SO
        line_delivered_milestone.project_id = self.project_global
        sale_order_1._compute_show_project_and_task_button()
        self.assertFalse(sale_order_1.show_create_project_button, "There is a product service with the service_policy set on 'delivered on milestone' and a project on the sale order, the button should be hidden")
        self.assertTrue(sale_order_1.show_project_button, "There is a product service with the service_policy set on 'delivered on milestone' and a project on the sale order, the button should be displayed")
        self.assertTrue(sale_order_1.show_task_button, "There is a product service with the service_policy set on 'delivered on milestone' and a project on the sale order, the button should be displayed")

        # add an ordered_prepaid service product
        line_prepaid = self.env['sale.order.line'].create({
            'product_id': self.product_service_ordered_prepaid.id,
            'order_id': sale_order_2.id,
        })
        sale_order_2._compute_show_project_and_task_button()
        self.assertFalse(sale_order_2.show_create_project_button, "There is a product service with the service_policy set on 'ordered_prepaid' on the sale order, the button should be hidden")
        self.assertFalse(sale_order_2.show_project_button, "There is no project on the sale order, the button should be hidden")
        self.assertFalse(sale_order_2.show_task_button, "There is no project on the sale order, the button should be hidden")
        # create a new task, whose sale order item is a sol of the SO
        self.env['project.task'].create({
            'name': 'Test Task',
            'project_id': self.project_global.id,
            'sale_line_id': line_prepaid.id,
        })
        sale_order_2._compute_tasks_ids()
        sale_order_2._compute_show_project_and_task_button()
        self.assertFalse(sale_order_2.show_create_project_button, "There is a product service with the service_policy set on 'ordered_prepaid' on the sale order, the button should be hidden")
        self.assertFalse(sale_order_2.show_project_button, "There is no project on the sale order, the button should be hidden")
        self.assertTrue(sale_order_2.show_task_button, "There is no project on the sale order and there is a task whose sale item is one of the sale_line of the SO, the button should be displayed")

        # add a manual service product
        self.env['sale.order.line'].create({
            'product_id': self.product_service_delivered_manual.id,
            'order_id': sale_order_3.id,
        })
        sale_order_3._compute_show_project_and_task_button()
        self.assertFalse(sale_order_3.show_create_project_button, "There is a product service with the service_policy set on 'manual' on the sale order, the button should be hidden")
        self.assertFalse(sale_order_3.show_project_button, "There is no project on the sale order, the button should be hidden")
        self.assertFalse(sale_order_3.show_task_button, "There is no project on the sale order, the button should be hidden")

    def test_create_task_from_template_line(self):
        """
        When we add an SOL from a template that is a service that has a service_policy that will generate a task,
        even if default_task_id is present in the context, a new task should be created when confirming the SO.
        """
        default_task = self.env['project.task'].with_context(tracking_disable=True).create({
            'name': 'Task',
            'project_id': self.project_global.id
        })
        sale_order = self.env['sale.order'].with_context(tracking_disable=True, default_task_id=default_task.id).create({
            'partner_id': self.partner.id,
        })
        quotation_template = self.env['sale.order.template'].create({
            'name': 'Test quotation',
        })
        quotation_template.write({
            'sale_order_template_line_ids': [
                Command.set(
                    self.env['sale.order.template.line'].create([{
                        'name': self.product_order_service2.display_name,
                        'sale_order_template_id': quotation_template.id,
                        'product_id': self.product_order_service2.id,
                        'product_uom_id': self.product_order_service2.uom_id.id,
                    }, {
                        'name': self.product_order_service3.display_name,
                        'sale_order_template_id': quotation_template.id,
                        'product_id': self.product_order_service3.id,
                        'product_uom_id': self.product_order_service3.uom_id.id,
                    }]).ids
                )
            ]
        })
        sale_order.with_context(default_task_id=default_task.id).write({
            'sale_order_template_id': quotation_template.id,
        })
        sale_order.with_context(default_task_id=default_task.id)._onchange_sale_order_template_id()
        self.assertFalse(sale_order.order_line.mapped('task_id'),
                         "SOL should have no related tasks, because they are from services that generates a task")
        sale_order.action_confirm()
        self.assertEqual(sale_order.tasks_count, 2, "SO should have 2 related tasks")
        self.assertNotIn(default_task, sale_order.tasks_ids, "SO should link to the default task from the context")

    def test_project_creation_on_so_confirm_with_account(self):
        # Ensures that the company of the account of the SO is propagated to the project.
        sale_order = self.env['sale.order'].with_context(tracking_disable=True).create({
            'partner_id': self.partner.id,
            'partner_invoice_id': self.partner.id,
            'partner_shipping_id': self.partner.id,
        })
        analytic_account_company = self.env['account.analytic.account'].create({
            'name': 'Account with company',
            'plan_id': self.analytic_plan.id,
            'company_id': self.env.company.id,
        })
        sale_order.analytic_account_id = analytic_account_company
        self.env['sale.order.line'].create({
            'name': self.product_order_service2.name,
            'product_id': self.product_order_service3.id,
            'order_id': sale_order.id,
        })
        self.assertTrue(sale_order.analytic_account_id, "The SO should have an analytic account before it is confirmed.")
        sale_order.action_confirm()
        self.assertEqual(self.env.company, sale_order.analytic_account_id.company_id, "The company of the account should be the company of the SO.")
        self.assertEqual(sale_order.analytic_account_id, sale_order.project_ids.analytic_account_id, "The project created for the SO and the SO should have the same account.")
        self.assertEqual(self.env.company, sale_order.project_ids.company_id, "The project created for the SO should have the same company as its account.")

    def test_project_creation_on_so_confirm_with_default_plan_with_company_in_setting(self):
         #This test ensures that the plan of the created account is the default plan of the setting, and that the company is correctly propagated
        sale_order = self.env['sale.order'].with_context(tracking_disable=True).create({
            'partner_id': self.partner.id,
            'partner_invoice_id': self.partner.id,
            'partner_shipping_id': self.partner.id,
        })
        self.env['sale.order.line'].create({
            'name': self.product_order_service2.name,
            'product_id': self.product_order_service3.id,
            'order_id': sale_order.id,
        })
        project_plan, _other_plans = self.env['account.analytic.plan']._get_all_plans()

        self.assertFalse(sale_order.analytic_account_id, "The SO should not have any analytic account before it is confirmed.")
        sale_order.action_confirm()

        self.assertEqual(sale_order.analytic_account_id.company_id, sale_order.project_ids.company_id, "The company_id of the account created should be the company of the project.")
        self.assertEqual(sale_order.analytic_account_id.plan_id, project_plan, "The plan of the account created should be the default analytic plan of the setting")
        self.assertEqual(sale_order.analytic_account_id, sale_order.project_ids.analytic_account_id, "The project created for the SO and the SO should have the same account.")

    def test_include_archived_projects_in_stat_btn_related_view(self):
        """Checks if the project stat-button action includes both archived and active projects."""
        # Setup
        project_A = self.env['project.project'].create({'name': 'Project_A'})
        project_B = self.env['project.project'].create({'name': 'Project_B'})

        product_A = self.env['product.product'].create({
            'name': 'product A',
            'list_price': 1.0,
            'type': 'service',
            'service_tracking': 'task_global_project',
            'project_id':project_A.id,
        })
        product_B = self.env['product.product'].create({
            'name': 'product B',
            'list_price': 2.0,
            'type': 'service',
            'service_tracking': 'task_global_project',
            'project_id':project_B.id,
        })

        sale_order = self.env['sale.order'].with_context(tracking_disable=True).create({
            'partner_id': self.partner.id,
            'partner_invoice_id': self.partner.id,
            'partner_shipping_id': self.partner.id,
        })

        SaleOrderLine = self.env['sale.order.line'].with_context(tracking_disable=True)
        SaleOrderLine.create({
            'name': product_A.name,
            'product_id': product_A.id,
            'product_uom_qty': 10,
            'price_unit': product_A.list_price,
            'order_id': sale_order.id,
        })
        SaleOrderLine.create({
            'name': product_B.name,
            'product_id': product_B.id,
            'product_uom_qty': 10,
            'price_unit': product_B.list_price,
            'order_id': sale_order.id,
        })

        def get_project_ids_from_action_domain(action):
            for el in action['domain']:
                if len(el) == 3 and el[0] == 'id' and el[1] == 'in':
                    domain_proj_ids = el[2]
                    break
            else:
                raise Exception(f"Couldn't find projects ids in the following action domain: {action['domain']}")
            return domain_proj_ids

        # Check if button action includes both projects BEFORE archivization
        action = sale_order.action_view_project_ids()
        self.assertEqual(len(get_project_ids_from_action_domain(action)), 2, "Domain should contain 2 projects.")

        # Check if button action includes both projects AFTER archivization
        project_B.write({'active': False})
        action = sale_order.action_view_project_ids()
        self.assertEqual(len(get_project_ids_from_action_domain(action)), 2, "Domain should contain 2 projects. (one archived, one not)")

    def test_sale_order_line_view_form_editable(self):
        """ Check the behavior of the form view editable of `sale.order.line` introduced in that module

            Test Case:
            =========
            1. create SO to use it as default_order_id when the SOL will be created by the editable form
            2. open form view of `sale.order.line` to create and edit a SOL
            3. create on the fly a product and check default values of that product
                3.1. type should be "service"
                3.2. service_policy should be "ordered_prepaid" (Prepaid/Fixed Price)
            4. check if the qty_delivered is editable
                4.1. if sale_timesheet is installed then the field should be readonly otherwise editable
            5. change the product set on the SOL form view to service product with invoice policy to 'delivered_milestones'
            6. check if the qty_delivered field is readonly
            7. change the product set on the SOL form view to service product with invoice policy to 'ordered_prepaid'
            8. check if the qty_delivered is editable
                8.1. if sale_timesheet is installed then the field should be readonly otherwise editable
            9. change the product set on the SOL form view to service product with invoice policy to 'delivered_manual'
            10. check if the qty_delivered is editable
        """
        so = self.env['sale.order'].create({
            'partner_id': self.partner.id,
        })
        so.action_confirm()
        SaleOrderLine = self.env['sale.order.line'].with_context(default_order_id=so.id)
        self.assertEqual(self.product_service_ordered_prepaid.service_policy, 'ordered_prepaid')
        self.assertEqual(self.product_service_delivered_milestone.service_policy, 'delivered_milestones')
        self.assertEqual(self.product_service_delivered_manual.service_policy, 'delivered_manual')
        with Form(SaleOrderLine, 'sale_project.sale_order_line_view_form_editable') as sol_form:
            product_context = sol_form._get_context('product_id')
            product = sol_form.product_id.with_context(product_context).new({
                'name': 'Test product',
            })
            self.assertEqual(product.detailed_type, 'service')
            self.assertEqual(product.type, 'service')
            self.assertEqual(product.service_policy, 'ordered_prepaid')
            sol_form.product_id = product
            is_readonly = product.service_type != 'manual'
            self.assertEqual(sol_form._get_modifier('qty_delivered', 'readonly'), is_readonly)
            if is_readonly:
                self.assertEqual(sol_form.qty_delivered_method, 'timesheet')
                self.assertEqual(sol_form.qty_delivered, 0, 'quantity delivered is readonly')
            else:
                sol_form.qty_delivered = 1
                self.assertEqual(sol_form.qty_delivered_method, 'manual')
                self.assertEqual(sol_form.qty_delivered, 1, 'quantity delivered is editable')
                sol_form.qty_delivered = 0  # reset for the next test case

            sol_form.product_id = self.product_service_delivered_milestone
            self.assertTrue(sol_form._get_modifier('qty_delivered', 'readonly'))
            self.assertEqual(sol_form.qty_delivered_method, 'milestones')

            sol_form.product_id = self.product_service_ordered_prepaid
            is_readonly = self.product_service_ordered_prepaid.service_type != 'manual'
            self.assertEqual(sol_form._get_modifier('qty_delivered', 'readonly'), is_readonly)
            if is_readonly:  # then sale_timesheet module installed
                self.assertEqual(sol_form.qty_delivered_method, 'timesheet')
                self.assertEqual(sol_form.qty_delivered, 0, 'quantity delivered is readonly')
            else:
                sol_form.qty_delivered = 1
                self.assertEqual(sol_form.qty_delivered_method, 'manual')
                self.assertEqual(sol_form.qty_delivered, 1, 'quantity delivered is editable')
                sol_form.qty_delivered = 0  # reset for the next test case

            sol_form.product_id = self.product_service_delivered_manual
            self.assertFalse(sol_form._get_modifier('qty_delivered', 'readonly'))
            sol_form.qty_delivered = 1
            self.assertEqual(sol_form.qty_delivered_method, 'manual')
            self.assertEqual(sol_form.qty_delivered, 1, 'quantity delivered is editable')

    def test_quick_create_sol(self):
        """
        When creating a SOL on the fly through the quick create, use a product matching
        what was typed in the field if there is one, and make sure the SOL name is computed correctly.
        """
        product_service = self.env['product.product'].create({
            'name': 'Signage',
            'type': 'service',
            'invoice_policy': 'order',
            'uom_id': self.env.ref('uom.product_uom_hour').id,
            'uom_po_id': self.env.ref('uom.product_uom_hour').id,
        })
        sale_line_id, sale_line_name = self.env['sale.order.line'].with_context(
            default_partner_id=self.partner.id,
            form_view_ref='sale_project.sale_order_line_view_form_editable',
        ).name_create('gnag')

        sale_line = self.env['sale.order.line'].browse(sale_line_id)
        self.assertEqual(sale_line.product_id, product_service, 'The created SOL should use the right product.')
        self.assertTrue(product_service.name in sale_line_name, 'The created SOL should use the full name of the product and not just what was typed.')

    def test_sale_order_items_of_the_project_status(self):
        """
        Checks that the sale order items appearing in the project status display every
        sale.order.line referrencing a product ignores the notes and sections
        """
        analytic_account = self.env['account.analytic.account'].create({
            'name': 'Project X',
            'plan_id': self.env.ref('analytic.analytic_plan_projects').id,
        })
        project = self.env['project.project'].create({
            'name': 'Project X',
            'partner_id': self.partner.id,
            'allow_billable': True,
            'analytic_account_id': analytic_account.id,
        })
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'project_id': project.id,
            'order_line': [
                Command.create({
                    'product_id': self.product_order_service1.id,
                    'product_uom_qty': 1,
                }),
                Command.create({
                    'name': "Section",
                    'display_type': "line_section",
                }),
                Command.create({
                    'name': "notes",
                    'display_type': "line_section",
                }),
                Command.create({
                    'product_id': self.product_a.id,
                    'product_uom_qty': 1,
                }),
            ],
            'analytic_account_id': analytic_account.id,
        })
        relevant_sale_order_lines = sale_order.order_line.filtered(lambda sol: sol.product_id)
        reported_sale_order_lines = self.env['sale.order.line'].search(project.action_view_sols()['domain'])
        self.assertEqual(project.sale_order_line_count, 2)
        self.assertEqual(relevant_sale_order_lines, reported_sale_order_lines)

    def test_sale_order_with_project_task_from_multi_companies(self):
        uom_hour = self.env.ref("uom.product_uom_hour")
        will_smith = self.env["res.partner"].create({"name": "Will Smith"})
        multi_company_project = self.env["project.project"].create({
            "name": "Multi Company Project",
            "company_id": None,
            "allow_billable": True,
        })

        company_a, company_b = self.env['res.company'].create([
            {"name": "Company A"},
            {"name": "Company B"},
        ])

        # cannot be done in batch because of `_check_sale_product_company` constraint
        product_a, product_b = (
            self.env["product.product"].with_company(company).create({
                "name": "Task Creating Product",
                "standard_price": 30,
                "list_price": 90,
                "type": "service",
                "service_tracking": "task_global_project",
                "invoice_policy": "order",
                "uom_id": uom_hour.id,
                "uom_po_id": uom_hour.id,
                "project_id": multi_company_project.id,
            })
            for company in [company_a, company_b]
        )
        sale_order_a, sale_order_b = self.env["sale.order"].create([
            {
                "partner_id": will_smith.id,
                "order_line": [
                    Command.create({
                        "product_id": product.id,
                        "product_uom_qty": 10,
                    }),
                    Command.create({
                        "product_id": product.id,
                        "product_uom_qty": 10,
                    }),
                ],
                'company_id': company.id,
            }
            for company, product in zip([company_a, company_b], [product_a, product_b])
        ])
        (sale_order_a + sale_order_b).action_confirm()

        for company in [company_a, company_b]:
            self.assertEqual(multi_company_project.with_company(company).sale_order_count, 2, "Expected all sale orders to be counted by project")
            self.assertEqual(
                multi_company_project.with_company(company).sale_order_line_count,
                len(sale_order_a.order_line) + len(sale_order_b.order_line),  # expect 4
                "Expected all sale order lines lines to be counted by project")
            sale_order_action = multi_company_project.with_company(company).action_view_sos()
            self.assertEqual(sale_order_action["type"], "ir.actions.act_window")
            self.assertEqual(sale_order_action["res_model"], "sale.order")

    def test_action_view_task_stages(self):
        SaleOrder = self.env['sale.order'].with_context(tracking_disable=True)
        SaleOrderLine = self.env['sale.order.line'].with_context(tracking_disable=True)

        sale_order_2 = SaleOrder.create({
            'partner_id': self.partner.id,
            'partner_invoice_id': self.partner.id,
            'partner_shipping_id': self.partner.id,
        })
        sale_line_1_order_2 = SaleOrderLine.create({
            'product_id': self.product_order_service1.id,
            'product_uom_qty': 10,
            'product_uom': self.product_order_service1.uom_id.id,
            'price_unit': self.product_order_service1.list_price,
            'order_id': sale_order_2.id,
        })

        self.env['project.task'].create({
            'name': 'Task',
            'sale_line_id': sale_line_1_order_2.id,
            'project_id': self.project_global.id,
        })
        action = sale_order_2.action_view_task()
        self.assertEqual(action["context"]["default_project_id"], self.project_global.id)

    def test_task_compute_sale_order_id(self):
        """
        Check whether a task's sale_order_id is set iff its partner_id matches
        the SO's partner_id, partner_invoice_id, or partner_shipping_id fields.
        """
        project_user = new_test_user(
            self.env, groups='project.group_project_user',
            login='Project user', name='Project user',
        )
        partners = [
            self.partner,
            self.partner_a,
            self.partner_b,
            self.env['res.partner'].create({'name': "unrelated partner"}),
        ]
        sale_order = self.env['sale.order'].with_context(tracking_disable=True).create({
            'partner_id': partners[0].id,
            'partner_invoice_id': partners[1].id,
            'partner_shipping_id': partners[2].id,
            'order_line': [Command.create({'product_id': self.product_order_service1.id})],
        })
        sale_order.action_confirm()

        task0, task1, task2, task3 = self.env['project.task'].with_user(project_user).create([{
            'name': f"Task {i}",
            'sale_line_id': sale_order.order_line.id,
            'project_id': self.project_global.id,
            'partner_id': partner.id,
        } for i, partner in enumerate(partners)])

        self.assertEqual(task0.sale_order_id, sale_order, "Task matches SO's partner_id")
        self.assertEqual(task1.sale_order_id, sale_order, "Task matches SO's partner_invoice_id")
        self.assertEqual(task2.sale_order_id, sale_order, "Task matches SO's partner_shipping_id")
        self.assertFalse(task3.sale_order_id, "Task partner doesn't match any of the SO partners")

        with self.assertRaises(AccessError):
            sale_order.with_user(project_user).partner_id
        task3.with_user(project_user).write({
            'partner_id': self.partner.id,
            'sale_line_id': sale_order.order_line.id,
        })
        self.assertEqual(task3.sale_order_id, sale_order, "Task matches SO's partner_id")

    def test_action_view_project_ids(self):
        order = self.env['sale.order'].create({
            'name': 'Project Order',
            'partner_id': self.partner.id
        })

        sol = self.env['sale.order.line'].create({
            'product_id': self.product_order_service4.id,
            'order_id': order.id,
        })

        order.action_confirm()
        action = order.action_view_project_ids()
        self.assertEqual(action['type'], 'ir.actions.act_window', 'Should return a window action')
        self.assertEqual(action['context']['default_sale_line_id'], sol.id, 'The SOL linked to the SO should be chosen as default value')

        self.product_order_service4.type = 'consu'
        action = order.action_view_project_ids()
        self.assertEqual(action['type'], 'ir.actions.act_window', 'Should return a window action')
        self.assertFalse(action['context']['default_sale_line_id'], 'No SOL should be set by default since the product changed')

    def test_confirm_sale_order_on_task_save(self):
        sale_order = self.env['sale.order'].create({
            'name': 'Sale Order',
            'partner_id': self.partner.id,
        })
        sale_order_line = self.env['sale.order.line'].create({
            'order_id': sale_order.id,
            'product_id': self.product_order_service1.id,
        })
        self.assertEqual(sale_order.state, 'draft')

        task = self.env['project.task'].create({
            'name': 'Task',
            'project_id': self.project_global.id,
        })
        task.write({'sale_line_id': sale_order_line.id})
        self.assertEqual(sale_order.state, 'sale')

    def test_confirm_sale_order_on_project_creation(self):
        sale_order = self.env['sale.order'].create({
            'name': 'Sale Order',
            'partner_id': self.partner.id,
        })
        sale_order_line = self.env['sale.order.line'].create({
            'order_id': sale_order.id,
            'product_id': self.product_order_service1.id,
        })
        self.assertEqual(sale_order.state, 'draft')

        self.env['project.project'].create({
            'name': 'Project',
            'sale_line_id': sale_order_line.id,
        })
        self.assertEqual(sale_order.state, 'sale')

    def test_sale_order_milestone_with_no_project_rights(self):
        milestone_user = new_test_user(
            self.env, groups='project.group_project_milestone,sales_team.group_sale_salesman',
            login='Milestone user', name='Milestone user',
        )

        group_project_user = self.env.ref('project.group_project_user').id
        self.assertNotIn(group_project_user, milestone_user.groups_id.ids)

        sale_order_form = Form(self.env['sale.order'].with_user(milestone_user), view='sale_project.view_order_form_inherit_sale_project')
        project_ids = sale_order_form._view['fields'].get('project_ids')
        self.assertTrue(project_ids, "'project_ids' field should be present for milestone users in the sale order form")
