# -*- coding: utf-8 -*-

from openerp.addons.mail.tests.common import TestMail


class TestProjectBase(TestMail):

    def setUp(self):
        super(TestProjectBase, self).setUp()

        user_group_employee = self.env.ref('base.group_user')
        user_group_project_user = self.env.ref('project.group_project_user')
        user_group_project_manager = self.env.ref('project.group_project_manager')

        # Test users to use through the various tests
        Users = self.env['res.users'].with_context({'no_reset_password': True})
        self.user_projectuser = Users.create({
            'name': 'Armande ProjectUser',
            'login': 'Armande',
            'alias_name': 'armande',
            'email': 'armande.projectuser@example.com',
            'groups_id': [(6, 0, [user_group_employee.id, user_group_project_user.id])]
        })
        self.user_projectmanager = Users.create({
            'name': 'Bastien ProjectManager',
            'login': 'bastien',
            'alias_name': 'bastien',
            'email': 'bastien.projectmanager@example.com',
            'groups_id': [(6, 0, [user_group_employee.id, user_group_project_manager.id])]})

        # Test 'Pigs' project
        self.project_pigs = self.env['project.project'].with_context({'mail_create_nolog': True}).create({
            'name': 'Pigs',
            'privacy_visibility': 'public',
            'alias_name': 'project+pigs',
            'partner_id': self.user_employee_2.partner_id.id})
        # Already-existing tasks in Pigs
        self.task_1 = self.env['project.task'].with_context({'mail_create_nolog': True}).create({
            'name': 'Pigs UserTask',
            'user_id': self.user_projectuser.id,
            'project_id': self.project_pigs.id})
        self.task_2 = self.env['project.task'].with_context({'mail_create_nolog': True}).create({
            'name': 'Pigs ManagerTask',
            'user_id': self.user_projectmanager.id,
            'project_id': self.project_pigs.id})
