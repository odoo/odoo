# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (c) 2013-TODAY OpenERP S.A. <http://www.openerp.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.addons.mail.tests.common import TestMail


class TestProjectBase(TestMail):

    @classmethod
    def setUpClass(cls):
        super(TestProjectBase, cls).setUpClass()
        cr, uid = cls.cr, cls.uid

        # Usefull models
        cls.project_project = cls.registry('project.project')
        cls.project_task = cls.registry('project.task')
        cls.project_task_delegate = cls.registry('project.task.delegate')

        # Find Project User group
        cls.group_project_user_id = cls.env.ref('project.group_project_user').id or False

        # Find Project Manager group
        cls.group_project_manager_id = cls.env.ref('project.group_project_manager').id or False

        # Test partners to use through the various tests
        cls.project_partner_id = cls.res_partner.create(cr, uid, {
            'name': 'Gertrude AgrolaitPartner',
            'email': 'gertrude.partner@agrolait.com',
        })
        cls.email_partner_id = cls.res_partner.create(cr, uid, {
            'name': 'Patrick Ratatouille',
            'email': 'patrick.ratatouille@agrolait.com',
        })

        # Test users to use through the various tests
        cls.user_projectuser_id = cls.res_users.create(cr, uid, {
            'name': 'Armande ProjectUser',
            'login': 'Armande',
            'alias_name': 'armande',
            'email': 'armande.projectuser@example.com',
            'groups_id': [(6, 0, [cls.group_employee_id, cls.group_project_user_id])]
        }, {'no_reset_password': True})
        cls.user_projectmanager_id = cls.res_users.create(cr, uid, {
            'name': 'Bastien ProjectManager',
            'login': 'bastien',
            'alias_name': 'bastien',
            'email': 'bastien.projectmanager@example.com',
            'groups_id': [(6, 0, [cls.group_employee_id, cls.group_project_manager_id])]
        }, {'no_reset_password': True})
        cls.user_none_id = cls.res_users.create(cr, uid, {
            'name': 'Charlie Avotbonkeur',
            'login': 'charlie',
            'alias_name': 'charlie',
            'email': 'charlie.noone@example.com',
            'groups_id': [(6, 0, [])]
        }, {'no_reset_password': True})
        cls.user_projectuser = cls.res_users.browse(cr, uid, cls.user_projectuser_id)
        cls.user_projectmanager = cls.res_users.browse(cr, uid, cls.user_projectmanager_id)
        cls.partner_projectuser_id = cls.user_projectuser.partner_id.id
        cls.partner_projectmanager_id = cls.user_projectmanager.partner_id.id

        # Test 'Pigs' project
        cls.project_pigs_id = cls.project_project.create(cr, uid, {
            'name': 'Pigs',
            'privacy_visibility': 'public',
            'alias_name': 'project+pigs',
            'partner_id': cls.partner_raoul_id,
        }, {'mail_create_nolog': True})

        # Already-existing tasks in Pigs
        cls.task_1_id = cls.project_task.create(cr, uid, {
            'name': 'Pigs UserTask',
            'user_id': cls.user_projectuser_id,
            'project_id': cls.project_pigs_id,
        }, {'mail_create_nolog': True})
        cls.task_2_id = cls.project_task.create(cr, uid, {
            'name': 'Pigs ManagerTask',
            'user_id': cls.user_projectmanager_id,
            'project_id': cls.project_pigs_id,
        }, {'mail_create_nolog': True})
