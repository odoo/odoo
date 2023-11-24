# -*- coding: utf-8 -*-

from lxml import etree

from odoo import fields
from odoo.osv import expression
from odoo.tests import users
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class TestProjectCommon(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestProjectCommon, cls).setUpClass()

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
        partner.company_id = company_1

        # The partner has a company, but the project has none. The partner can have any new company, but the project can only be set to False/partner.company
        with self.assertRaises(UserError):
            # Cannot change the company of a project if the company of the partner is different
            self.project_pigs.company_id = company_2
        partner.company_id = company_2
        partner.company_id = False
        partner.company_id = company_1
        self.project_pigs.company_id = company_1
        self.assertEqual(self.project_pigs.company_id, company_1, "The company of the project should have been updated.")

        # The partner has a company and the project has a company. The project can only be set to False, the partner can not be changed
        with self.assertRaises(UserError):
            # Cannot change the company of a project if both the project and its partner have a company
            self.project_pigs.company_id = company_2
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
