# -*- coding: utf-8 -*-

from contextlib import contextmanager
from lxml import etree

from odoo.tests.common import TransactionCase, Form
from odoo.exceptions import AccessError, UserError

class TestMultiCompanyCommon(TransactionCase):

    @classmethod
    def setUpMultiCompany(cls):

        # create companies
        cls.company_a = cls.env['res.company'].create({
            'name': 'Company A'
        })
        cls.company_b = cls.env['res.company'].create({
            'name': 'Company B'
        })

        # shared customers
        cls.partner_1 = cls.env['res.partner'].create({
            'name': 'Valid Lelitre',
            'email': 'valid.lelitre@agrolait.com',
            'company_id': False,
        })
        cls.partner_2 = cls.env['res.partner'].create({
            'name': 'Valid Poilvache',
            'email': 'valid.other@gmail.com',
            'company_id': False,
        })

        # users to use through the various tests
        user_group_employee = cls.env.ref('base.group_user')
        Users = cls.env['res.users'].with_context({'no_reset_password': True})

        cls.user_employee_company_a = Users.create({
            'name': 'Employee Company A',
            'login': 'employee-a',
            'email': 'employee@companya.com',
            'company_id': cls.company_a.id,
            'company_ids': [(6, 0, [cls.company_a.id])],
            'groups_id': [(6, 0, [user_group_employee.id])]
        })
        cls.user_manager_company_a = Users.create({
            'name': 'Manager Company A',
            'login': 'manager-a',
            'email': 'manager@companya.com',
            'company_id': cls.company_a.id,
            'company_ids': [(6, 0, [cls.company_a.id])],
            'groups_id': [(6, 0, [user_group_employee.id])]
        })
        cls.user_employee_company_b = Users.create({
            'name': 'Employee Company B',
            'login': 'employee-b',
            'email': 'employee@companyb.com',
            'company_id': cls.company_b.id,
            'company_ids': [(6, 0, [cls.company_b.id])],
            'groups_id': [(6, 0, [user_group_employee.id])]
        })
        cls.user_manager_company_b = Users.create({
            'name': 'Manager Company B',
            'login': 'manager-b',
            'email': 'manager@companyb.com',
            'company_id': cls.company_b.id,
            'company_ids': [(6, 0, [cls.company_b.id])],
            'groups_id': [(6, 0, [user_group_employee.id])]
        })

    @contextmanager
    def sudo(self, login):
        old_uid = self.uid
        try:
            user = self.env['res.users'].sudo().search([('login', '=', login)])
            # switch user
            self.uid = user.id
            self.env = self.env(user=self.uid)
            yield
        finally:
            # back
            self.uid = old_uid
            self.env = self.env(user=self.uid)

    @contextmanager
    def allow_companies(self, company_ids):
        """ The current user will be allowed in each given companies (like he can sees all of them in the company switcher and they are all checked) """
        old_allow_company_ids = self.env.user.company_ids.ids
        current_user = self.env.user
        try:
            current_user.write({'company_ids': company_ids})
            context = dict(self.env.context, allowed_company_ids=company_ids)
            self.env = self.env(user=current_user, context=context)
            yield
        finally:
            # back
            current_user.write({'company_ids': old_allow_company_ids})
            context = dict(self.env.context, allowed_company_ids=old_allow_company_ids)
            self.env = self.env(user=current_user, context=context)

    @contextmanager
    def switch_company(self, company):
        """ Change the company in which the current user is logged """
        old_companies = self.env.context.get('allowed_company_ids', [])
        try:
            # switch company in context
            new_companies = list(old_companies)
            if company.id not in new_companies:
                new_companies = [company.id] + new_companies
            else:
                new_companies.insert(0, new_companies.pop(new_companies.index(company.id)))
            context = dict(self.env.context, allowed_company_ids=new_companies)
            self.env = self.env(context=context)
            yield
        finally:
            # back
            context = dict(self.env.context, allowed_company_ids=old_companies)
            self.env = self.env(context=context)

class TestMultiCompanyProject(TestMultiCompanyCommon):

    @classmethod
    def setUpClass(cls):
        super(TestMultiCompanyProject, cls).setUpClass()

        cls.setUpMultiCompany()

        user_group_project_user = cls.env.ref('project.group_project_user')
        user_group_project_manager = cls.env.ref('project.group_project_manager')

        # setup users
        cls.user_employee_company_a.write({
            'groups_id': [(4, user_group_project_user.id)]
        })
        cls.user_manager_company_a.write({
            'groups_id': [(4, user_group_project_manager.id)]
        })
        cls.user_employee_company_b.write({
            'groups_id': [(4, user_group_project_user.id)]
        })
        cls.user_manager_company_b.write({
            'groups_id': [(4, user_group_project_manager.id)]
        })

        # create project in both companies
        Project = cls.env['project.project'].with_context({'mail_create_nolog': True, 'tracking_disable': True})
        cls.project_company_a = Project.create({
            'name': 'Project Company A',
            'alias_name': 'project+companya',
            'partner_id': cls.partner_1.id,
            'company_id': cls.company_a.id,
            'type_ids': [
                (0, 0, {
                    'name': 'New',
                    'sequence': 1,
                }),
                (0, 0, {
                    'name': 'Won',
                    'sequence': 10,
                })
            ]
        })
        cls.project_company_b = Project.create({
            'name': 'Project Company B',
            'alias_name': 'project+companyb',
            'partner_id': cls.partner_1.id,
            'company_id': cls.company_b.id,
            'type_ids': [
                (0, 0, {
                    'name': 'New',
                    'sequence': 1,
                }),
                (0, 0, {
                    'name': 'Won',
                    'sequence': 10,
                })
            ]
        })
        # already-existing tasks in company A and B
        Task = cls.env['project.task'].with_context({'mail_create_nolog': True, 'tracking_disable': True})
        cls.task_1 = Task.create({
            'name': 'Task 1 in Project A',
            'user_ids': cls.user_employee_company_a,
            'project_id': cls.project_company_a.id
        })
        cls.task_2 = Task.create({
            'name': 'Task 2 in Project B',
            'user_ids': cls.user_employee_company_b,
            'project_id': cls.project_company_b.id
        })

    def test_create_project(self):
        """ Check project creation in multiple companies """
        with self.sudo('manager-a'):
            project = self.env['project.project'].with_context({'tracking_disable': True}).create({
                'name': 'Project Company A',
                'partner_id': self.partner_1.id,
            })
            self.assertEqual(project.company_id, self.env.user.company_id, "A newly created project should be in the current user company")

            with self.switch_company(self.company_b):
                with self.assertRaises(AccessError, msg="Manager can not create project in a company in which he is not allowed"):
                    project = self.env['project.project'].with_context({'tracking_disable': True}).create({
                        'name': 'Project Company B',
                        'partner_id': self.partner_1.id,
                        'company_id': self.company_b.id
                    })

                # when allowed in other company, can create a project in another company (different from the one in which you are logged)
                with self.allow_companies([self.company_a.id, self.company_b.id]):
                    project = self.env['project.project'].with_context({'tracking_disable': True}).create({
                        'name': 'Project Company B',
                        'partner_id': self.partner_1.id,
                        'company_id': self.company_b.id
                    })

    def test_generate_analytic_account(self):
        """ Check the analytic account generation, company propagation """
        with self.sudo('manager-b'):
            with self.allow_companies([self.company_a.id, self.company_b.id]):
                self.project_company_a._create_analytic_account()

                self.assertEqual(self.project_company_a.company_id, self.project_company_a.analytic_account_id.company_id, "The analytic account created from a project should be in the same company")

    def test_create_task(self):
        with self.sudo('employee-a'):
            # create task, set project; the onchange will set the correct company
            with Form(self.env['project.task'].with_context({'tracking_disable': True})) as task_form:
                task_form.name = 'Test Task in company A'
                task_form.project_id = self.project_company_a
            task = task_form.save()

            self.assertEqual(task.company_id, self.project_company_a.company_id, "The company of the task should be the one from its project.")

    def test_move_task(self):
        with self.sudo('employee-a'):
            with self.allow_companies([self.company_a.id, self.company_b.id]):
                with Form(self.task_1) as task_form:
                    task_form.project_id = self.project_company_b
                task = task_form.save()

                self.assertEqual(task.company_id, self.company_b, "The company of the task should be the one from its project.")

                with Form(self.task_1) as task_form:
                    task_form.project_id = self.project_company_a
                task = task_form.save()

                self.assertEqual(task.company_id, self.company_a, "Moving a task should change its company.")

    def test_create_subtask(self):
        with self.sudo('employee-a'):
            with self.allow_companies([self.company_a.id, self.company_b.id]):
                # create subtask, set parent; the onchange will set the correct company and subtask project
                with Form(self.env['project.task'].with_context({'tracking_disable': True, 'default_parent_id': self.task_1.id, 'default_project_id': self.project_company_b.id})) as task_form:
                    task_form.name = 'Test Subtask in company B'
                task = task_form.save()
                self.assertEqual(task.company_id, self.project_company_b.company_id, "The company of the subtask should be the one from its project, and not from its parent.")

                # set parent on existing orphan task; the onchange will set the correct company and subtask project
                self.task_2.write({'project_id': False})
                # For `parent_id` to  be visible in the view, you need
                # 1. The debug mode
                # 2. `allow_subtasks` to be true
                # <field name="parent_id" attrs="{'invisible': [('allow_subtasks', '=', False)]}" groups="base.group_no_one"/>
                # `allow_subtasks` is a related to `allow_subtasks` on the project
                # as the point of the test is to test the behavior of the task `_compute_project_id` when there is no project,
                # `allow_subtasks` is by default invisible, and you shouldn't therefore be able to change it.
                # So, to make it visible, temporary modify the view to make it visible even when `allow_subtasks` is `False`.
                view = self.env.ref('project.view_task_form2').sudo()
                tree = etree.fromstring(view.arch)
                for node in tree.xpath('//field[@name="parent_id"][@attrs]'):
                    node.attrib.pop('attrs')
                view.arch = etree.tostring(tree)
                with self.debug_mode():
                    with Form(self.task_2) as task_form:
                        task_form.name = 'Test Task 2 becomes child of Task 1 (other company)'
                        task_form.parent_id = self.task_1
                    task = task_form.save()

                self.assertEqual(task.company_id, task.project_id.company_id, "The company of the orphan subtask should be the one from its project.")

    def test_cross_subtask_project(self):
        # set up default subtask project
        self.project_company_a.write({'allow_subtasks': True})

        # For `parent_id` to  be visible in the view, you need
        # 1. The debug mode
        # 2. `allow_subtasks` to be true
        # <field name="parent_id" attrs="{'invisible': [('allow_subtasks', '=', False)]}" groups="base.group_no_one"/>
        # `allow_subtasks` is a related to `allow_subtasks` on the project
        # as the point of the test is to test the behavior of the task `_compute_project_id` when there is no project,
        # `allow_subtasks` is by default invisible, and you shouldn't therefore be able to change it.
        # So, to make it visible, temporary modify the view to make it visible even when `allow_subtasks` is `False`.
        view = self.env.ref('project.view_task_form2').sudo()
        tree = etree.fromstring(view.arch)
        for node in tree.xpath('//field[@name="parent_id"][@attrs]'):
            node.attrib.pop('attrs')
        view.arch = etree.tostring(tree)

        with self.sudo('employee-a'):
            with self.allow_companies([self.company_a.id, self.company_b.id]):
                with self.debug_mode():
                    with Form(self.env['project.task'].with_context({'tracking_disable': True})) as task_form:
                        task_form.name = 'Test Subtask in company B'
                        task_form.parent_id = self.task_1

                    task = task_form.save()

                self.assertEqual(task.project_id, self.task_1.project_id, "The default project of a subtask should be the default subtask project of the project from the mother task")
                self.assertEqual(task.company_id, task.project_id.company_id, "The company of the orphan subtask should be the one from its project.")
                self.assertEqual(self.task_1.child_ids.ids, [task.id])

        with self.sudo('employee-a'):
            with self.assertRaises(AccessError):
                with Form(task) as task_form:
                    task_form.name = "Testing changing name in a company I can not read/write"
