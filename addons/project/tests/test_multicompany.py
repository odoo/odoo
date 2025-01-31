# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from contextlib import contextmanager
from lxml import etree

from odoo.tests import Form, TransactionCase
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
            'group_ids': [(6, 0, [user_group_employee.id])]
        })
        cls.user_manager_company_a = Users.create({
            'name': 'Manager Company A',
            'login': 'manager-a',
            'email': 'manager@companya.com',
            'company_id': cls.company_a.id,
            'company_ids': [(6, 0, [cls.company_a.id])],
            'group_ids': [(6, 0, [user_group_employee.id])]
        })
        cls.user_employee_company_b = Users.create({
            'name': 'Employee Company B',
            'login': 'employee-b',
            'email': 'employee@companyb.com',
            'company_id': cls.company_b.id,
            'company_ids': [(6, 0, [cls.company_b.id])],
            'group_ids': [(6, 0, [user_group_employee.id])]
        })
        cls.user_manager_company_b = Users.create({
            'name': 'Manager Company B',
            'login': 'manager-b',
            'email': 'manager@companyb.com',
            'company_id': cls.company_b.id,
            'company_ids': [(6, 0, [cls.company_b.id])],
            'group_ids': [(6, 0, [user_group_employee.id])]
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
            'group_ids': [(4, user_group_project_user.id)]
        })
        cls.user_manager_company_a.write({
            'group_ids': [(4, user_group_project_manager.id)]
        })
        cls.user_employee_company_b.write({
            'group_ids': [(4, user_group_project_user.id)]
        })
        cls.user_manager_company_b.write({
            'group_ids': [(4, user_group_project_manager.id)]
        })

        # create project in both companies
        cls.Project = cls.env['project.project'].with_context({'mail_create_nolog': True, 'tracking_disable': True})
        cls.project_company_a = cls.Project.create({
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
        cls.project_company_b = cls.Project.create({
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
            self.assertFalse(project.company_id, "A newly created project should have a company set to False by default")

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

                self.assertEqual(self.project_company_a.company_id, self.project_company_a.account_id.company_id, "The analytic account created from a project should be in the same company.")

        project_no_company = self.Project.create({'name': 'Project no company'})
        #ensures that all the existing plan have a company_id
        project_no_company._create_analytic_account()
        self.assertFalse(project_no_company.account_id.company_id, "The analytic account created from a project without company_id should have its company_id field set to False.")

        project_no_company_2 = self.Project.create({'name': 'Project no company 2'})
        project_no_company_2._create_analytic_account()
        self.assertNotEqual(project_no_company_2.account_id, project_no_company.account_id, "The analytic account created should be different from the account created for the 1st project.")
        self.assertEqual(project_no_company_2.account_id.plan_id, project_no_company.account_id.plan_id, "No new analytic should have been created.")

    def test_analytic_account_company_consistency(self):
        """
            This test ensures that the following invariant is kept:
            If the company of an analytic account is set, all of its project must have the same company.
            If the company of an analytic account is not set, its project can either have a company set, or none.
        """
        project_no_company = self.Project.create({'name': 'Project no company'})
        project_no_company._create_analytic_account()
        account_no_company = project_no_company.account_id
        self.project_company_a._create_analytic_account()
        account_a = self.project_company_a.account_id

        # Set the account of the project to a new account without company_id
        self.project_company_a.account_id = account_no_company
        self.assertEqual(self.project_company_a.account_id, account_no_company, "The new account should be set on the project.")
        self.assertFalse(account_no_company.company_id, "The company of the account should not have been updated.")
        self.project_company_a.account_id = account_a

        # Set the account of the project to a new account with a company_id
        project_no_company.account_id = account_a
        self.assertEqual(project_no_company.company_id, self.company_a, "The company of the project should have been updated to the company of its new account.")
        self.assertEqual(project_no_company.account_id, account_a, "The account of the project should have been updated.")
        project_no_company.account_id = account_no_company
        project_no_company.company_id = False

        # Neither the project nor its account have a company_id
        # set the company of the project
        project_no_company.company_id = self.company_a
        self.assertEqual(project_no_company.company_id, self.company_a, "The company of the project should have been updated.")
        self.assertFalse(account_no_company.company_id, "The company of the account should not have been updated for the company of the project was False before its update.")
        project_no_company.company_id = False
        # set the company of the account
        account_no_company.company_id = self.company_a
        self.assertEqual(project_no_company.company_id, self.company_a, "The company of the project should have been updated to the company of its new account.")
        self.assertEqual(account_no_company.company_id, self.company_a, "The company of the account should have been updated.")

        # The project and its account have the same company (company A)
        # set the company of the project to False
        self.project_company_a.company_id = False
        self.assertFalse(self.project_company_a.company_id, "The company of the project should have been updated.")
        self.assertFalse(account_a.company_id, "The company of the account should be set to False, as it only has one project linked to it and the company of the project was set from company A to False")
        account_a.company_id = self.company_a
        # set the company of the project to company B
        self.project_company_a.company_id = self.company_b
        self.assertEqual(self.project_company_a.company_id, self.company_b, "The company of the project should have been updated.")
        self.assertEqual(account_a.company_id, self.company_b, "The company of the account should have been updated, for its company was the same as the one of its project and the company of the project was set before the update.")
        # set the company of the account to company A
        account_a.company_id = self.company_a
        self.assertEqual(self.project_company_a.company_id, self.company_a, "The company of the project should have been updated to the company of its account.")
        self.assertEqual(account_a.company_id, self.company_a, "The company of the account should have been updated.")
        # set the company of the account to False
        account_a.company_id = False
        self.assertEqual(self.project_company_a.company_id, self.company_a, "The company of the project should not have been updated for the company of its account has been set to False.")
        self.assertFalse(account_a.company_id, "The company of the account should have been updated.")

        # The project has a company_id set, but not its account
        # set the company of the account to company B (!= project.company_id)
        account_a.company_id = self.company_b
        self.assertEqual(self.project_company_a.company_id, self.company_b, "The company of the project should have been updated to the company of its account even if the new company set on the account is a different one than the one the project.")
        self.assertEqual(account_a.company_id, self.company_b, "The company of the account should have been updated.")
        account_a.company_id = False
        self.project_company_a.company_id = self.company_a
        # set the company of the account to company A (== project.company_id)
        account_a.company_id = self.company_a
        self.assertEqual(self.project_company_a.company_id, self.company_a, "The company of the project should have been updated to the company of its account.")
        self.assertEqual(account_a.company_id, self.company_a, "The company of the account should have been updated.")
        account_a.company_id = False
        # set the company of the project to company B
        self.project_company_a.company_id = self.company_b
        self.assertEqual(self.project_company_a.company_id, self.company_b, "The company of the project should have been updated.")
        self.assertFalse(account_a.company_id, "The company of the account should not have been updated for it is was set to False.")
        # set the company of the project to False
        self.project_company_a.company_id = False
        self.assertFalse(self.project_company_a.company_id, "The company of the project should have been updated.")
        self.assertFalse(account_a.company_id, "The company of the account should not have been updated for it was set to False.")

        # creates an AAL for the account_a
        account_a.company_id = self.company_b
        aal = self.env['account.analytic.line'].create({
            'name': 'other revenues line',
            'account_id': account_a.id,
            'company_id': self.company_b.id,
            'amount': 100,
        })
        with self.assertRaises(UserError):
            self.project_company_a.company_id = self.company_a
        self.assertEqual(self.project_company_a.company_id, self.company_b, "The account of the project contains AAL, its company can not be updated.")
        aal.unlink()

        project_no_company.account_id = account_a
        self.assertEqual(project_no_company.company_id, account_a.company_id)
        with self.assertRaises(UserError):
            self.project_company_a.company_id = self.company_a
        self.assertEqual(self.project_company_a.company_id, self.company_b, "The account of the project is linked to more than one project, its company can not be updated.")

    def test_create_task(self):
        with self.sudo('employee-a'):
            # create task, set project; the onchange will set the correct company
            with Form(self.env['project.task'].with_context({'tracking_disable': True})) as task_form:
                task_form.name = 'Test Task in company A'
                task_form.project_id = self.project_company_a
            task = task_form.save()

            self.assertEqual(task.company_id, self.project_company_a.company_id, "The company of the task should be the one from its project.")

    def test_update_company_id(self):
        """ this test ensures that:
        - All the tasks of a project with a company set have the same company as their project. Updating the task set the task to a private state.
        Updating the company the project update all the tasks even if the company of the project is set to False.
        - The tasks of a project without company can have any company set. Updating a task does not update the company of its project. Updating the project update
        all the tasks even if these tasks had a company set.
        """
        project = self.Project.create({'name': 'Project'})
        task = self.env['project.task'].create({
            'name': 'task no company',
            'project_id': project.id,
        })
        self.assertFalse(task.company_id, "Creating a task in a project without company set its company_id to False.")

        with self.debug_mode():
            task_form = Form(task)
            task_form.company_id = self.company_a
            task = task_form.save()
        self.assertFalse(project.company_id, "Setting a new company on a task should not update the company of its project.")
        self.assertEqual(task.company_id, self.company_a, "The company of the task should have been updated.")

        project.company_id = self.company_b
        self.assertEqual(project.company_id, self.company_b, "The company of the project should have been updated.")
        self.assertEqual(task.company_id, self.company_b, "The company of the task should have been updated.")


        with self.debug_mode():
            task_form = Form(task)
            task_form.company_id = self.company_a
            task = task_form.save()
        self.assertEqual(task.company_id, self.company_a, "The company of the task should have been updated.")
        self.assertFalse(task.project_id, "The task should now be a private task.")
        self.assertEqual(project.company_id, self.company_b, "the company of the project should not have been updated.")

        task_1, task_2, task_3 = self.env['project.task'].create([{
            'name': 'task 1',
            'project_id': project.id,
        }, {
            'name': 'task 2',
            'project_id': project.id,
        }, {
            'name': 'task 3',
            'project_id': project.id,
        }])
        project.company_id = False
        for task in project.task_ids:
            self.assertFalse(task.company_id, "The tasks should not have a company_id set.")
        task_1.company_id = self.company_a
        task_2.company_id = self.company_b
        self.assertEqual(task_1.company_id, self.company_a, "The company of task_1 should have been set to company A.")
        self.assertEqual(task_2.company_id, self.company_b, "The company of task_2 should have been set to company B.")
        self.assertFalse(task_3.company_id, "The company of the task_3 should not have been updated.")
        self.assertFalse(project.company_id, "The company of the project should not have been updated.")
        company_c = self.env['res.company'].create({'name': 'company C'})
        project.company_id = company_c
        for task in project.tasks:
            self.assertEqual(task.company_id, company_c, "The company of the tasks should have been updated to company C.")

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
        # 1) Create a subtask and check that every field is correctly set on the subtask
        with (
            Form(self.task_1) as task_1_form,
            task_1_form.child_ids.new() as subtask_line,
        ):
            self.assertEqual(subtask_line.project_id, self.task_1.project_id, "The task's project should already be set on the subtask.")
            subtask_line.name = 'Test Subtask'
        subtask = self.task_1.child_ids[0]
        self.assertFalse(subtask.display_in_project, "The subtask's field 'display in project' should be unchecked.")
        self.assertEqual(subtask.company_id, self.task_1.company_id, "The company of the subtask should be the one from its project.")

        # 2) Change the project of the parent task and check that the subtask follows it
        with Form(self.task_1) as task_1_form:
            task_1_form.project_id = self.project_company_b
        self.assertEqual(subtask.project_id, self.task_1.project_id, "The task's project should already be set on the subtask.")
        self.assertFalse(subtask.display_in_project, "The subtask's field 'display in project' should be unchecked.")
        self.assertEqual(subtask.company_id, self.project_company_b.company_id, "The company of the subtask should be the one from its project.")
        task_1_form.project_id = self.project_company_a

        # 3) Change the parent of the subtask and check that every field is correctly set on it
        # For `parent_id` to  be visible in the view, you need
        # 1. The debug mode
        # <field name="parent_id" groups="base.group_no_one"/>
        view = self.env.ref('project.view_task_form2').sudo()
        tree = etree.fromstring(view.arch)
        for node in tree.xpath('//field[@name="parent_id"][@invisible]'):
            node.attrib.pop('invisible')
        view.arch = etree.tostring(tree)
        with (
            self.debug_mode(),
            Form(subtask) as subtask_form
        ):
            subtask_form.parent_id = self.task_2
            self.assertEqual(subtask_form.project_id, self.task_2.project_id, "The task's project should already be set on the subtask.")
            self.assertFalse(subtask.display_in_project, "The subtask's field 'display in project' should be unchecked.")
        self.assertEqual(subtask.company_id, self.task_2.company_id, "The company of the subtask should be the one from its new project, set from its parent.")

        # 4) Change the project of the subtask and check some fields
        subtask.project_id = self.project_company_a
        self.assertTrue(subtask.display_in_project, "The subtask's field 'display in project' should be checked.")
        self.assertEqual(subtask.company_id, self.project_company_a.company_id, "The company of the subtask should be the one from its project, and not from its parent.")


    def test_cross_subtask_project(self):

        # For `parent_id` to  be visible in the view, you need
        # 1. The debug mode
        # <field name="parent_id" groups="base.group_no_one"/>
        view = self.env.ref('project.view_task_form2').sudo()
        tree = etree.fromstring(view.arch)
        for node in tree.xpath('//field[@name="parent_id"][@invisible]'):
            node.attrib.pop('invisible')
        view.arch = etree.tostring(tree)

        with self.sudo('employee-a'):
            with self.allow_companies([self.company_a.id, self.company_b.id]):
                with self.debug_mode():
                    with Form(self.env['project.task'].with_context({'tracking_disable': True})) as task_form:
                        task_form.name = 'Test Subtask in company B'
                        task_form.project_id = self.task_1.project_id
                        task_form.parent_id = self.task_1
                    task = task_form.save()

                self.assertEqual(self.task_1.child_ids.ids, [task.id])

        with self.sudo('employee-a'):
            with self.assertRaises(AccessError):
                with Form(task) as task_form:
                    task_form.name = "Testing changing name in a company I can not read/write"
