from odoo import Command
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, users


class TestTaskTemplate(TransactionCase):

    @classmethod
    def setUpClass(self):
        super().setUpClass()
        self.partner = self.env['res.partner'].create({
            'name': 'Test Partner',
        })
        self.manager = mail_new_test_user(self.env, 'Project admin', groups='project.group_project_manager')
        self.user = mail_new_test_user(self.env, 'Project user', groups='project.group_project_user')
        self.project = self.env['project.project'].create({'name': 'home design'})
        self.project_con = self.env['project.project'].create({'name': 'home con'})
        self.task_template = self.env['project.task'].create({
            'name': "home con",
            'is_task_template': True,
            'child_ids': [
                Command.create({
                    'name': 'home arch',
                    'allocated_hours': 20,
                }),
                Command.create({
                    'name': 'home pool',
                    'allocated_hours': 20,
                    'active': False,
                    'task_template_project_id': self.project_con.id
                }),
                Command.create({
                    'name': 'home con',
                    'allocated_hours': 20,
                    'task_template_project_id': self.project_con.id
                })]
        })
        self.product0 = self.env['product.product'].create({
            'name': 'Test0',
            'type': 'service',
            'service_tracking': 'task_global_project', 'project_id': self.project.id,
            'task_template_id': self.task_template.id
        })

        self.product1 = self.env['product.product'].create({
            'name': 'Test1',
            'type': 'service',
            'service_tracking': 'task_global_project', 'project_id': self.project.id,
            'task_template_id': self.task_template.id
        })

    def test_task_template_behavior(self):
        """
            Test the task template behavior
        """
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [
                Command.create({
                    'product_id': self.product0.id,
                }),
                Command.create({
                    'product_id': self.product1.id,
                })]
        })
        order.action_confirm()
        task_count = self.env['project.task'].with_context(active_test=False).search_count([('sale_line_id', 'in', order.order_line.ids)])
        self.assertEqual(order.tasks_count, 2, msg="Expected 2 tasks to be generated from the task template, but the count does not match.")
        self.assertEqual(task_count, 3, msg="Expected 3 tasks incl. archived to be generated from the task template, but the count does not match.")
        self.assertEqual(order.tasks_ids[0].allocated_hours, 40, msg="Expected task's hours to be 20 from the task template, but the hours does not match.")
        self.assertEqual(order.project_count, 2, msg="Expected 2 project to be linked to Sale order the count does not match.")

    @users('Project admin', 'Project user')
    def test_check_task_template_accessibility(self):
        """
            Test the task template read access rights
            The project user and project admin should have read access rights to task template.
        """
        try:
            self.assertEqual(len(self.env['project.task'].browse(self.task_template.id).child_ids), 2)
        except AccessError:
            raise RuntimeError("Task Template is accessible to this project.group_project_manager, project.group_project_user group.")
