from lxml import etree

from odoo import Command, fields
from odoo.tests import Form, users
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class TestProjectCommon(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestProjectCommon, cls).setUpClass()
        cls.env.company.resource_calendar_id.tz = "Europe/Brussels"

        user_group_employee = cls.env.ref('base.group_user')
        user_group_project_user = cls.env.ref('project.group_project_user')
        user_group_project_manager = cls.env.ref('project.group_project_manager')

        cls.partner_1 = cls.env['res.partner'].create({
            'name': 'Valid Lelitre',
            'email': 'valid.lelitre@agrolait.com'})
        cls.partner_2 = cls.env['res.partner'].create({
            'name': 'Valid Poilvache',
            'email': 'valid.other@gmail.com'})
        cls.partner_3 = cls.env['res.partner'].create({
            'name': 'Valid Poilboeuf',
            'email': 'valid.poilboeuf@gmail.com'})

        # Test users to use through the various tests
        Users = cls.env['res.users'].with_context({'no_reset_password': True})
        cls.user_public = Users.create({
            'name': 'Bert Tartignole',
            'login': 'bert',
            'email': 'b.t@example.com',
            'signature': 'SignBert',
            'notification_type': 'email',
            'groups_id': [(6, 0, [cls.env.ref('base.group_public').id])]})
        cls.user_portal = Users.create({
            'name': 'Chell Gladys',
            'login': 'chell',
            'email': 'chell@gladys.portal',
            'signature': 'SignChell',
            'notification_type': 'email',
            'groups_id': [(6, 0, [cls.env.ref('base.group_portal').id])]})
        cls.user_projectuser = Users.create({
            'name': 'Armande ProjectUser',
            'login': 'armandel',
            'password': 'armandel',
            'email': 'armande.projectuser@example.com',
            'groups_id': [(6, 0, [user_group_employee.id, user_group_project_user.id])]
        })
        cls.user_projectmanager = Users.create({
            'name': 'Bastien ProjectManager',
            'login': 'bastien',
            'email': 'bastien.projectmanager@example.com',
            'groups_id': [(6, 0, [user_group_employee.id, user_group_project_manager.id])]})

        # Test 'Pigs' project
        cls.project_pigs = cls.env['project.project'].with_context({'mail_create_nolog': True}).create({
            'name': 'Pigs',
            'privacy_visibility': 'employees',
            'alias_name': 'project+pigs',
            'partner_id': cls.partner_1.id})
        # Already-existing tasks in Pigs
        cls.task_1 = cls.env['project.task'].with_context({'mail_create_nolog': True}).create({
            'name': 'Pigs UserTask',
            'user_ids': cls.user_projectuser,
            'project_id': cls.project_pigs.id})
        cls.task_2 = cls.env['project.task'].with_context({'mail_create_nolog': True}).create({
            'name': 'Pigs ManagerTask',
            'user_ids': cls.user_projectmanager,
            'project_id': cls.project_pigs.id})

        # Test 'Goats' project, same as 'Pigs', but with 2 stages
        cls.project_goats = cls.env['project.project'].with_context({'mail_create_nolog': True}).create({
            'name': 'Goats',
            'privacy_visibility': 'followers',
            'alias_name': 'project+goats',
            'partner_id': cls.partner_1.id,
            'type_ids': [
                (0, 0, {
                    'name': 'New',
                    'sequence': 1,
                }),
                (0, 0, {
                    'name': 'Won',
                    'sequence': 10,
                })]
            })

    def format_and_process(self, template, to='groups@example.com, other@gmail.com', subject='Frogs',
                           extra='', email_from='Sylvie Lelitre <test.sylvie.lelitre@agrolait.com>',
                           cc='', msg_id='<1198923581.41972151344608186760.JavaMail@agrolait.com>',
                           model=None, target_model='project.task', target_field='name'):
        self.assertFalse(self.env[target_model].search([(target_field, '=', subject)]))
        mail = template.format(to=to, subject=subject, cc=cc, extra=extra, email_from=email_from, msg_id=msg_id)
        self.env['mail.thread'].message_process(model, mail)
        return self.env[target_model].search([(target_field, '=', subject)])

    @classmethod
    def _enable_project_manager(cls):
        cls.env.ref('base.group_user').sudo().write({'implied_ids': [
            (4, cls.env.ref('project.group_project_manager').id),
        ]})


class TestProjectBase(TestProjectCommon):

    def test_delete_project_with_tasks(self):
        """Test all tasks linked to a project are removed when the user removes this project. """
        task_type = self.env['project.task.type'].create({'name': 'Won', 'sequence': 1, 'fold': True})
        project_unlink = self.env['project.project'].with_context({'mail_create_nolog': True}).create({
            'name': 'rev',
            'privacy_visibility': 'employees',
            'alias_name': 'rev',
            'partner_id': self.partner_1.id,
            'type_ids': task_type,
        })

        self.env['project.task'].with_context({'mail_create_nolog': True}).create({
            'name': 'Pigs UserTask',
            'user_ids': self.user_projectuser,
            'project_id': project_unlink.id,
            'stage_id': task_type.id})

        task_count = len(project_unlink.tasks)
        self.assertEqual(task_count, 1, "The project should have 1 task")

        project_unlink.unlink()
        self.assertNotEqual(task_count, 0, "The all tasks linked to project should be deleted when user delete the project")

    def test_auto_assign_stages_when_importing_tasks(self):
        self.assertFalse(self.project_pigs.type_ids)
        self.assertEqual(len(self.project_goats.type_ids), 2)
        first_stage = self.project_goats.type_ids[0]
        self.env['project.task']._load_records_create([{
            'name': 'First Task',
            'project_id': self.project_pigs.id,
            'stage_id': first_stage.id,
        }])
        self.assertEqual(self.project_pigs.type_ids, first_stage)
        self.env['project.task']._load_records_create([
            {
                'name': 'task',
                'project_id': self.project_pigs.id,
                'stage_id': stage.id,
            } for stage in self.project_goats.type_ids
        ])
        self.assertEqual(self.project_pigs.type_ids, self.project_goats.type_ids)

    def test_filter_visibility_unread_messages(self):
        """Tests the visibility of the "Unread messages" filter in the project task search view
        according to the notification type of the user.
        A user with the email notification type must not see the Unread messages filter
        A user with the inbox notification type must see the Unread messages filter"""
        user1 = self.user_projectuser
        user2 = self.user_projectuser.copy()
        user1.notification_type = 'email'
        user2.notification_type = 'inbox'
        for user, filter_visible_expected in ((user1, False), (user2, True)):
            Task = self.env['project.task'].with_user(user)
            arch = Task.get_view(self.env.ref('project.view_task_search_form').id)['arch']
            tree = etree.fromstring(arch)
            self.assertEqual(bool(tree.xpath('//filter[@name="message_needaction"]')), filter_visible_expected)

    @users('bastien')
    def test_search_favorite_order(self):
        """ Test the search method, ordering by favorite projects.
        """
        self.project_goats.favorite_user_ids += self.user_projectmanager
        self.env.cr.flush()

        Project = self.env['project.project']
        project_ids = [self.project_pigs.id, self.project_goats.id]
        domain = [('id', 'in', project_ids)]

        self.assertEqual(Project.search(domain, order='is_favorite desc')[0], self.project_goats)
        self.assertEqual(Project.search(domain, order='is_favorite')[-1], self.project_goats)

        self.assertTrue(self.project_pigs.id < self.project_goats.id)
        self.assertEqual(Project.search(domain, order='id').ids, project_ids)

    @users('bastien')
    def test_edit_favorite(self):
        project1, project2 = projects = self.env['project.project'].create([{
            'name': 'Project Test1',
        }, {
            'name': 'Project Test2',
            'is_favorite': True,
        }])
        self.assertFalse(project1.is_favorite)
        self.assertTrue(project2.is_favorite)
        project1.is_favorite = True
        project2.is_favorite = False
        projects.invalidate_recordset(['is_favorite']) # To force 'is_favorite' to recompute
        self.assertTrue(project1.is_favorite)
        self.assertFalse(project2.is_favorite)

    @users('bastien')
    def test_create_favorite_from_project_form(self):
        Project = self.env['project.project']
        form1 = Form(Project)
        form1.name = 'Project Test1'
        self.assertFalse(form1.is_favorite)
        project1 = form1.save()
        self.assertFalse(project1.is_favorite)

        form2 = Form(Project)
        form2.name = 'Project Test2'
        form2.is_favorite = True
        self.assertTrue(form2.is_favorite)
        project2 = form2.save()
        self.assertTrue(project2.is_favorite)

    @users('bastien')
    def test_edit_favorite_from_project_form(self):
        project1, project2 = self.env['project.project'].create([{
            'name': 'Project Test1',
        }, {
            'name': 'Project Test2',
            'is_favorite': True,
        }])
        with Form(project1) as form:
            form.is_favorite = True
        self.assertTrue(project1.is_favorite)

        with Form(project2) as form:
            form.is_favorite = False
        self.assertFalse(project2.is_favorite)

    def test_change_project_or_partner_company(self):
        """ Tests that it is impossible to change the company of a project
            if the company of the partner is different and vice versa if the company of the project is set.
            If the company of the project is not set, there are no restriction on its partner company-wise.
        """
        company_1 = self.env.company
        company_2 = self.env['res.company'].create({'name': 'Company 2'})
        partner = self.env['res.partner'].create({
            'name': 'Partner',
        })
        self.project_pigs.partner_id = partner

        # Neither the partner nor the project have a company. Their companies can be updated.
        self.assertFalse(partner.company_id)
        self.assertFalse(self.project_pigs.company_id)
        self.project_pigs.company_id = company_1
        self.assertEqual(self.project_pigs.company_id, company_1, "The company of the project should have been updated.")
        self.project_pigs.company_id = False
        # if the partner company is set, the project's should also be set
        partner.company_id = company_1

        # If the partner has a company, the project must have the same
        self.assertEqual(partner.company_id, self.project_pigs.company_id, "The company of the project should have been updated.")

        # The partner has a company and the project has a company. The partner's can only be set to False, the project's can not be changed
        with self.assertRaises(UserError):
            # Cannot change the company of a project if both the project and its partner have a company
            self.project_pigs.company_id = company_2
        with self.assertRaises(UserError):
            # Cannot unset the project's company if its associated partner has a company
            self.project_pigs.company_id = False
        with self.assertRaises(UserError):
            # Cannot change the company of a partner if both the project and its partner have a company
            partner.company_id = company_2
        partner.company_id = False
        self.project_pigs.company_id = False
        self.assertFalse(self.project_pigs.company_id, "The company of the project should have been set to False.")
        self.project_pigs.company_id = company_1
        self.project_goats.company_id = company_1
        self.project_goats.partner_id = partner
        with self.assertRaises(UserError):
            # Cannot change the company of a partner that part of multiple projects with different companies
            self.project_goats.partner_id.company_id = company_2


        # The project has a company, but the partner has none. The partner can only be set to False/project.company but the project can have any new company.
        with self.assertRaises(UserError):
            # Cannot change the company of a partner if both the project and its partner have a company
            partner.company_id = company_2
        self.project_pigs.company_id = company_2
        self.assertEqual(self.project_pigs.company_id, company_2, "The company of the project should have been updated.")
        self.project_pigs.company_id = False
        self.assertFalse(self.project_pigs.company_id, "The company of the project should have been set to False.")
        self.project_pigs.company_id = company_1
        partner.company_id = company_1
        self.assertEqual(partner.company_id, company_1, "The company of the partner should have been updated.")

    def test_add_customer_rating_project(self):
        """ Tests that the rating_ids field contains a rating once created
        """
        rate = self.env['rating.rating'].create({
            'res_id': self.task_1.id,
            'parent_res_id': self.project_pigs.id,
            'res_model_id': self.env['ir.model']._get('project.task').id,
            'parent_res_model_id': self.env['ir.model']._get('project.project').id,
        })
        rating = 5

        self.task_1.rating_apply(rating, token=rate.access_token)

        self.project_pigs.rating_ids.invalidate_recordset()
        self.assertEqual(len(self.project_pigs.rating_ids), 1, "There should be 1 rating linked to the project")

    def test_planned_dates_consistency_for_project(self):
        """ This test ensures that a project can not have date start set,
            if its date end is False and that it can not have a date end
            set if its date start is False .
        """
        self.assertFalse(self.project_goats.date_start)
        self.assertFalse(self.project_goats.date)

        self.project_goats.write({'date_start': '2021-09-27', 'date': '2021-09-28'})
        self.assertEqual(fields.Date.to_string(self.project_goats.date_start), '2021-09-27', "The start date should be set.")
        self.assertEqual(fields.Date.to_string(self.project_goats.date), '2021-09-28', "The expiration date should be set.")

        self.project_goats.date_start = False
        self.assertFalse(fields.Date.to_string(self.project_goats.date_start), "The start date should be unset.")
        self.assertFalse(fields.Date.to_string(self.project_goats.date), "The expiration date should be unset as well.")

        self.project_goats.write({'date_start': '2021-09-27', 'date': '2021-09-28'})
        self.project_goats.date = False
        self.assertFalse(fields.Date.to_string(self.project_goats.date), "The expiration date should be unset.")
        self.assertFalse(fields.Date.to_string(self.project_goats.date_start), "The start date should be unset as well.")

        self.project_goats.write({'date_start': '2021-09-27'})
        self.assertFalse(fields.Date.to_string(self.project_goats.date_start), "The start date should be unset since expiration date if not set.")
        self.assertFalse(fields.Date.to_string(self.project_goats.date), "The expiration date should stay be unset.")

        self.project_goats.write({'date': '2021-09-28'})
        self.assertFalse(fields.Date.to_string(self.project_goats.date), "The expiration date should be unset since the start date if not set.")
        self.assertFalse(fields.Date.to_string(self.project_goats.date_start), "The start date should be unset.")

        self.project_pigs.write({'date_start': '2021-09-23', 'date': '2021-09-24'})

        # Case 1: one project has date range set and the other one has no date range set.
        projects = self.project_goats + self.project_pigs
        projects.write({'date_start': '2021-09-27', 'date': '2021-09-28'})
        for p in projects:
            self.assertEqual(fields.Date.to_string(p.date_start), '2021-09-27', f'The start date of {p.name} should be updated.')
            self.assertEqual(fields.Date.to_string(p.date), '2021-09-28', f'The expiration date of {p.name} should be updated.')
        self.project_goats.date_start = False
        projects.write({'date_start': '2021-09-30'})
        self.assertFalse(fields.Date.to_string(self.project_goats.date_start), 'The start date should not be updated')
        self.assertFalse(fields.Date.to_string(self.project_goats.date), 'The expiration date should not be updated')
        self.assertEqual(fields.Date.to_string(self.project_pigs.date_start), '2021-09-27', 'The start date should not be updated.')
        self.assertEqual(fields.Date.to_string(self.project_pigs.date), '2021-09-28', 'The expiration date should not be updated.')
        projects.write({'date_start': False})
        for p in projects:
            self.assertFalse(fields.Date.to_string(p.date_start), f'The start date of {p.name} should be set to False.')
            self.assertFalse(fields.Date.to_string(p.date), f'The expiration date of {p.name} should be set to False.')
        self.project_pigs.write({'date_start': '2021-09-27', 'date': '2021-09-28'})
        projects.write({'date': False})
        for p in projects:
            self.assertFalse(fields.Date.to_string(p.date_start), f'The start date of {p.name} should be set to False.')
            self.assertFalse(fields.Date.to_string(p.date), f'The expiration date of {p.name} should be set to False.')

        # Case 2: both projects have no date range set
        projects.write({'date_start': '2021-09-27'})
        for p in projects:
            self.assertFalse(fields.Date.to_string(p.date_start), f'The start date of {p.name} should not be updated.')
            self.assertFalse(fields.Date.to_string(p.date), f'The expiration date of {p.name} should not be updated.')
        projects.write({'date': '2021-09-28'})
        for p in projects:
            self.assertFalse(fields.Date.to_string(p.date_start), f'The start date of {p.name} should not be updated.')
            self.assertFalse(fields.Date.to_string(p.date), f'The expiration date of {p.name} should not be updated.')

        projects.write({'date_start': '2021-09-27', 'date': '2021-09-28'})
        for p in projects:
            self.assertEqual(fields.Date.to_string(p.date_start), '2021-09-27', f'The start date of {p.name} should be updated.')
            self.assertEqual(fields.Date.to_string(p.date), '2021-09-28', f'The expiration date of {p.name} should be updated.')

        # Case 3: both projects have a different date range set
        self.project_pigs.write({'date_start': '2021-09-23', 'date': '2021-09-30'})
        projects.write({'date_start': '2021-09-22'})
        self.assertEqual(fields.Date.to_string(self.project_goats.date_start), '2021-09-22', 'The start date should be updated.')
        self.assertEqual(fields.Date.to_string(self.project_goats.date), '2021-09-28', 'The expiration date should not be updated.')
        self.assertEqual(fields.Date.to_string(self.project_pigs.date_start), '2021-09-22', 'The start date should be updated.')
        self.assertEqual(fields.Date.to_string(self.project_pigs.date), '2021-09-30', 'The expiration date should not be updated.')
        projects.write({'date': '2021-09-29'})
        self.assertEqual(fields.Date.to_string(self.project_goats.date_start), '2021-09-22', 'The start date should not be updated.')
        self.assertEqual(fields.Date.to_string(self.project_goats.date), '2021-09-29', 'The expiration date should be updated.')
        self.assertEqual(fields.Date.to_string(self.project_pigs.date_start), '2021-09-22', 'The start date should not be updated.')
        self.assertEqual(fields.Date.to_string(self.project_pigs.date), '2021-09-29', 'The expiration date should be updated.')
        projects.write({'date_start': False})
        for p in projects:
            self.assertFalse(fields.Date.to_string(p.date_start), f'The start date of {p.name} should be set to False.')
            self.assertFalse(fields.Date.to_string(p.date), f'The expiration date of {p.name} should be set to False.')
        self.project_goats.write({'date_start': '2021-09-27', 'date': '2021-09-28'})
        self.project_pigs.write({'date_start': '2021-09-23', 'date': '2021-09-30'})
        projects.write({'date': False})
        for p in projects:
            self.assertFalse(fields.Date.to_string(p.date_start), f'The start date of {p.name} should be set to False.')
            self.assertFalse(fields.Date.to_string(p.date), f'The expiration date of {p.name} should be set to False.')
        self.project_goats.write({'date_start': '2021-09-27', 'date': '2021-09-28'})
        self.project_pigs.write({'date_start': '2021-09-23', 'date': '2021-09-30'})
        projects.write({'date_start': '2021-09-25', 'date': '2021-09-26'})
        for p in projects:
            self.assertEqual(fields.Date.to_string(p.date_start), '2021-09-25', f'The start date of {p.name} should be updated.')
            self.assertEqual(fields.Date.to_string(p.date), '2021-09-26', f'The expiration date of {p.name} should be updated.')

    def test_create_task_in_batch_with_email_cc(self):
        user_a, user_b, user_c = self.env['res.users'].create([{
            'name': 'user A',
            'login': 'loginA',
            'email': 'email@bisous1',
        }, {
            'name': 'user B',
            'login': 'loginB',
            'email': 'email@bisous2',
        }, {
            'name': 'user C',
            'login': 'loginC',
            'email': 'email@bisous3',
        }])
        partner = self.env['res.partner'].create({
            'name': 'partner',
            'email': 'email@bisous4',
        })
        task_1, task_2 = self.env['project.task'].with_context({'mail_create_nolog': True}).create([{
            'name': 'task 1',
            'project_id': self.project_pigs.id,
            'email_cc': 'email@bisous1, email@bisous2, email@bisous4'
        }, {
            'name': 'task 2',
            'project_id': self.project_pigs.id,
            'email_cc': 'email@bisous3, email@bisous2, email@bisous4'
        }])
        self.assertTrue(user_a.partner_id in task_1.message_partner_ids)
        self.assertTrue(user_b.partner_id in task_1.message_partner_ids)
        self.assertFalse(user_c.partner_id in task_1.message_partner_ids)
        self.assertFalse(partner in task_1.message_partner_ids)
        self.assertFalse(user_a.partner_id in task_2.message_partner_ids)
        self.assertTrue(user_b.partner_id in task_2.message_partner_ids)
        self.assertTrue(user_c.partner_id in task_2.message_partner_ids)
        self.assertFalse(partner in task_2.message_partner_ids)

    def test_create_private_task_in_batch(self):
        """ This test ensures that copying private task in batch can be done correctly."""

        task_0, task_1 = self.env['project.task'].create([{
            'name': f'task {i}',
            'user_ids': self.env.user.ids,
            'project_id': False,
        } for i in range(2)]).copy()
        self.assertEqual(task_0.name, 'task 0 (copy)')
        self.assertEqual(task_1.name, 'task 1 (copy)')

    def test_duplicate_project_with_tasks(self):
        """ Test to check duplication of projects tasks active state. """
        project = self.env['project.project'].create({
            'name': 'Project',
        })
        task = self.env['project.task'].create({
            'name': 'Task',
            'project_id': project.id,
        })

        # Duplicate active project with active task
        project_dup = project.copy()
        self.assertTrue(project_dup.active, "Active project should remain active when duplicating an active project")
        self.assertEqual(project_dup.task_count, 1, "Duplicated project should have as many tasks as orginial project")
        self.assertTrue(project_dup.tasks.active, "Active task should remain active when duplicating an active project")

        # Duplicate active project with archived task
        task.active = False
        project_dup = project.copy()
        self.assertTrue(project_dup.active, "Active project should remain active when duplicating an active project")
        self.assertFalse(project_dup.tasks.active, "Archived task should remain archived when duplicating an active project")

        # Duplicate archived project with archived task
        project.active = False
        project_dup = project.copy()
        self.assertTrue(project_dup.active, "The new project should be active by default")
        self.assertTrue(project_dup.tasks.active, "Archived task should be active when duplicating an archived project")

    def test_create_analytic_account_batch(self):
        """ This test will check that the '_create_analytic_account' method assigns the accounts to the projects in the right order. """
        projects = self.env["project.project"].create([{
            "name": f"Project {x}",
        } for x in range(10)])
        projects._create_analytic_account()
        self.assertEqual(projects.mapped("name"), projects.account_id.mapped("name"), "The analytic accounts names should match with the projects.")

    def test_task_count(self):
        project1, project2 = self.env['project.project'].create([
            {'name': 'project1'},
            {'name': 'project2'},
        ])
        self.env['project.task'].with_context(default_project_id=project1.id).create([
            {'name': 'task1'},
            {'name': 'task2', 'state': '1_done'},
            {'name': 'task3', 'child_ids': [
                Command.create({'name': 'subtask1', 'project_id': project1.id}),
                Command.create({'name': 'subtask2', 'project_id': project1.id, 'state': '1_canceled'}),
                Command.create({'name': 'subtask3', 'project_id': project2.id}),
                Command.create({'name': 'subtask4', 'project_id': project1.id, 'child_ids': [
                    Command.create({'name': 'subsubtask41', 'project_id': project2.id}),
                    Command.create({'name': 'subsubtask42', 'project_id': project1.id})
                ]}),
                Command.create({'name': 'subtask5', 'state': '1_done', 'project_id': project1.id, 'child_ids': [
                    Command.create({'name': 'subsubtask51', 'project_id': project1.id, 'state': '1_done'}),
                ]}),
            ]}
        ])
        self.assertEqual(project1.task_count, 3)
        self.assertEqual(project1.open_task_count, 2)
        self.assertEqual(project1.closed_task_count, 1)
        self.assertEqual(project2.task_count, 2)
        self.assertEqual(project2.open_task_count, 2)
        self.assertEqual(project2.closed_task_count, 0)

    def test_archived_duplicate_task(self):
        """ Test to check duplication of an archived task.
            The duplicate of an archived task should be active.
        """
        project = self.env['project.project'].create({
            'name': 'Project',
        })
        task = self.env['project.task'].create({
            'name': 'Task',
            'project_id': project.id,
        })
        copy_task1 = task.copy()
        self.assertTrue(copy_task1.active, "Active task should be active when duplicating an active task")
        task.active = False
        copy_task2 = task.copy()
        self.assertTrue(copy_task2.active, "Archived task should be active when duplicating an archived task")

    def test_duplicate_doesnt_copy_date(self):
        project = self.env['project.project'].create({
            'name': 'Project',
            'date_start': '2021-09-20',
            'date': '2021-09-28',
        })
        task = self.env['project.task'].create({
            'name': 'Task',
            'project_id': project.id,
            'date_deadline': '2021-09-26',
        })
        project_copy = project.copy()
        self.assertFalse(project_copy.date_start, "The project's date fields shouldn't be copied on project duplication")
        self.assertFalse(project_copy.date, "The project's date fields shouldn't be copied on project duplication")
        self.assertFalse(project_copy.task_ids.date_deadline, "The task's date fields shouldn't be copied on project duplication")
        self.assertFalse(task.copy().date_deadline, "The task's date fields shouldn't be copied on task duplication")
