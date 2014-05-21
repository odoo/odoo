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

    def setUp(self):
        super(TestProjectBase, self).setUp()
        cr, uid = self.cr, self.uid

        # Usefull models
        self.project_project = self.registry('project.project')
        self.project_task = self.registry('project.task')
        self.project_task_delegate = self.registry('project.task.delegate')

        # Find Project User group
        group_project_user_ref = self.registry('ir.model.data').get_object_reference(cr, uid, 'project', 'group_project_user')
        self.group_project_user_id = group_project_user_ref and group_project_user_ref[1] or False

        # Find Project Manager group
        group_project_manager_ref = self.registry('ir.model.data').get_object_reference(cr, uid, 'project', 'group_project_manager')
        self.group_project_manager_id = group_project_manager_ref and group_project_manager_ref[1] or False

        # Test partners to use through the various tests
        self.project_partner_id = self.res_partner.create(cr, uid, {
            'name': 'Gertrude AgrolaitPartner',
            'email': 'gertrude.partner@agrolait.com',
        })
        self.email_partner_id = self.res_partner.create(cr, uid, {
            'name': 'Patrick Ratatouille',
            'email': 'patrick.ratatouille@agrolait.com',
        })

        # Test users to use through the various tests
        self.user_projectuser_id = self.res_users.create(cr, uid, {
            'name': 'Armande ProjectUser',
            'login': 'Armande',
            'alias_name': 'armande',
            'email': 'armande.projectuser@example.com',
            'groups_id': [(6, 0, [self.group_employee_id, self.group_project_user_id])]
        })
        self.user_projectmanager_id = self.res_users.create(cr, uid, {
            'name': 'Bastien ProjectManager',
            'login': 'bastien',
            'alias_name': 'bastien',
            'email': 'bastien.projectmanager@example.com',
            'groups_id': [(6, 0, [self.group_employee_id, self.group_project_manager_id])]
        })
        self.user_none_id = self.res_users.create(cr, uid, {
            'name': 'Charlie Avotbonkeur',
            'login': 'charlie',
            'alias_name': 'charlie',
            'email': 'charlie.noone@example.com',
            'groups_id': [(6, 0, [])]
        })
        self.user_projectuser = self.res_users.browse(cr, uid, self.user_projectuser_id)
        self.user_projectmanager = self.res_users.browse(cr, uid, self.user_projectmanager_id)
        self.partner_projectuser_id = self.user_projectuser.partner_id.id
        self.partner_projectmanager_id = self.user_projectmanager.partner_id.id

        # Test 'Pigs' project
        self.project_pigs_id = self.project_project.create(cr, uid, {
            'name': 'Pigs',
            'privacy_visibility': 'public',
            'alias_name': 'project+pigs',
            'partner_id': self.partner_raoul_id,
        }, {'mail_create_nolog': True})

        # Already-existing tasks in Pigs
        self.task_1_id = self.project_task.create(cr, uid, {
            'name': 'Pigs UserTask',
            'user_id': self.user_projectuser_id,
            'project_id': self.project_pigs_id,
        }, {'mail_create_nolog': True})
        self.task_2_id = self.project_task.create(cr, uid, {
            'name': 'Pigs ManagerTask',
            'user_id': self.user_projectmanager_id,
            'project_id': self.project_pigs_id,
        }, {'mail_create_nolog': True})
