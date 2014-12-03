# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (c) 2013-TODAY OpenERP S.A. <http://openerp.com>
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

from openerp.addons.project.tests.test_project_base import TestProjectBase
from openerp.exceptions import AccessError
from openerp.osv.orm import except_orm
from openerp.tools import mute_logger


class TestPortalProjectBase(TestProjectBase):

    def setUp(self):
        super(TestPortalProjectBase, self).setUp()
        cr, uid = self.cr, self.uid

        # Find Portal group
        group_portal_ref = self.registry('ir.model.data').get_object_reference(cr, uid, 'base', 'group_portal')
        self.group_portal_id = group_portal_ref and group_portal_ref[1] or False

        # Find Public group
        group_public_ref = self.registry('ir.model.data').get_object_reference(cr, uid, 'base', 'group_public')
        self.group_public_id = group_public_ref and group_public_ref[1] or False

        # # Test users to use through the various tests
        self.user_portal_id = self.res_users.create(cr, uid, {
            'name': 'Chell Portal',
            'login': 'chell',
            'alias_name': 'chell',
            'groups_id': [(6, 0, [self.group_portal_id])]
        })
        self.user_public_id = self.res_users.create(cr, uid, {
            'name': 'Donovan Public',
            'login': 'donovan',
            'alias_name': 'donovan',
            'groups_id': [(6, 0, [self.group_public_id])]
        })
        self.user_manager_id = self.res_users.create(cr, uid, {
            'name': 'Eustache Manager',
            'login': 'eustache',
            'alias_name': 'eustache',
            'groups_id': [(6, 0, [self.group_project_manager_id])]
        })

        # Test 'Pigs' project
        self.project_pigs_id = self.project_project.create(cr, uid, {
            'name': 'Pigs', 'privacy_visibility': 'public'}, {'mail_create_nolog': True})
        # Various test tasks
        self.task_1_id = self.project_task.create(cr, uid, {
            'name': 'Test1', 'user_id': False, 'project_id': self.project_pigs_id}, {'mail_create_nolog': True})
        self.task_2_id = self.project_task.create(cr, uid, {
            'name': 'Test2', 'user_id': False, 'project_id': self.project_pigs_id}, {'mail_create_nolog': True})
        self.task_3_id = self.project_task.create(cr, uid, {
            'name': 'Test3', 'user_id': False, 'project_id': self.project_pigs_id}, {'mail_create_nolog': True})
        self.task_4_id = self.project_task.create(cr, uid, {
            'name': 'Test4', 'user_id': self.user_projectuser_id, 'project_id': self.project_pigs_id}, {'mail_create_nolog': True})
        self.task_5_id = self.project_task.create(cr, uid, {
            'name': 'Test5', 'user_id': self.user_portal_id, 'project_id': self.project_pigs_id}, {'mail_create_nolog': True})
        self.task_6_id = self.project_task.create(cr, uid, {
            'name': 'Test6', 'user_id': self.user_public_id, 'project_id': self.project_pigs_id}, {'mail_create_nolog': True})


class TestPortalProject(TestPortalProjectBase):
    @mute_logger('openerp.addons.base.ir.ir_model', 'openerp.models')
    def test_00_project_access_rights(self):
        """ Test basic project access rights, for project and portal_project """
        cr, uid, pigs_id = self.cr, self.uid, self.project_pigs_id

        # ----------------------------------------
        # CASE1: public project
        # ----------------------------------------

        # Do: Alfred reads project -> ok (employee ok public)
        self.project_project.read(cr, self.user_projectuser_id, [pigs_id], ['state'])
        # Test: all project tasks visible
        task_ids = self.project_task.search(cr, self.user_projectuser_id, [('project_id', '=', pigs_id)])
        test_task_ids = set([self.task_1_id, self.task_2_id, self.task_3_id, self.task_4_id, self.task_5_id, self.task_6_id])
        self.assertEqual(set(task_ids), test_task_ids,
                         'access rights: project user cannot see all tasks of a public project')
        # Test: all project tasks readable
        self.project_task.read(cr, self.user_projectuser_id, task_ids, ['name'])
        # Test: all project tasks writable
        self.project_task.write(cr, self.user_projectuser_id, task_ids, {'description': 'TestDescription'})

        # Do: Bert reads project -> crash, no group
        self.assertRaises(AccessError, self.project_project.read, cr, self.user_none_id, [pigs_id], ['state'])
        # Test: no project task visible
        self.assertRaises(AccessError, self.project_task.search, cr, self.user_none_id, [('project_id', '=', pigs_id)])
        # Test: no project task readable
        self.assertRaises(AccessError, self.project_task.read, cr, self.user_none_id, task_ids, ['name'])
        # Test: no project task writable
        self.assertRaises(AccessError, self.project_task.write, cr, self.user_none_id, task_ids, {'description': 'TestDescription'})

        # Do: Chell reads project -> ok (portal ok public)
        self.project_project.read(cr, self.user_portal_id, [pigs_id], ['state'])
        # Test: all project tasks visible
        task_ids = self.project_task.search(cr, self.user_portal_id, [('project_id', '=', pigs_id)])
        self.assertEqual(set(task_ids), test_task_ids,
                         'access rights: project user cannot see all tasks of a public project')
        # Test: all project tasks readable
        self.project_task.read(cr, self.user_portal_id, task_ids, ['name'])
        # Test: no project task writable
        self.assertRaises(AccessError, self.project_task.write, cr, self.user_portal_id, task_ids, {'description': 'TestDescription'})

        # Do: Donovan reads project -> ok (public)
        self.project_project.read(cr, self.user_public_id, [pigs_id], ['state'])
        # Test: all project tasks visible
        task_ids = self.project_task.search(cr, self.user_public_id, [('project_id', '=', pigs_id)])
        self.assertEqual(set(task_ids), test_task_ids,
                         'access rights: public user cannot see all tasks of a public project')
        # Test: all project tasks readable
        self.project_task.read(cr, self.user_public_id, task_ids, ['name'])
        # Test: no project task writable
        self.assertRaises(AccessError, self.project_task.write, cr, self.user_public_id, task_ids, {'description': 'TestDescription'})

        # ----------------------------------------
        # CASE2: portal project
        # ----------------------------------------
        self.project_project.write(cr, uid, [pigs_id], {'privacy_visibility': 'portal'})
        self.project_project.invalidate_cache(cr, uid)

        # Do: Alfred reads project -> ok (employee ok public)
        self.project_project.read(cr, self.user_projectuser_id, [pigs_id], ['state'])
        # Test: all project tasks visible
        task_ids = self.project_task.search(cr, self.user_projectuser_id, [('project_id', '=', pigs_id)])
        self.assertEqual(set(task_ids), test_task_ids,
                         'access rights: project user cannot see all tasks of a portal project')

        # Do: Bert reads project -> crash, no group
        self.assertRaises(AccessError, self.project_project.read, cr, self.user_none_id, [pigs_id], ['state'])
        # Test: no project task searchable
        self.assertRaises(AccessError, self.project_task.search, cr, self.user_none_id, [('project_id', '=', pigs_id)])

        # Data: task follower
        self.project_project.message_subscribe_users(cr, self.user_manager_id, [pigs_id], [self.user_portal_id])
        self.project_task.message_subscribe_users(cr, self.user_projectuser_id, [self.task_1_id, self.task_3_id], [self.user_portal_id])

        # Do: Chell reads project -> ok (portal ok portal)
        self.project_project.read(cr, self.user_portal_id, [pigs_id], ['state'])

        # Do: Donovan reads project -> ko (public ko portal)
        self.assertRaises(except_orm, self.project_project.read, cr, self.user_public_id, [pigs_id], ['state'])
        # Test: no project task visible
        task_ids = self.project_task.search(cr, self.user_public_id, [('project_id', '=', pigs_id)])
        self.assertFalse(task_ids, 'access rights: public user should not see tasks of a portal project')

        # Data: task follower cleaning
        self.project_task.message_unsubscribe_users(cr, self.user_projectuser_id, [self.task_1_id, self.task_3_id], [self.user_portal_id])

        # ----------------------------------------
        # CASE3: employee project
        # ----------------------------------------
        self.project_project.write(cr, uid, [pigs_id], {'privacy_visibility': 'employees'})
        self.project_project.invalidate_cache(cr, uid)

        # Do: Alfred reads project -> ok (employee ok employee)
        self.project_project.read(cr, self.user_projectuser_id, [pigs_id], ['state'])
        # Test: all project tasks visible
        task_ids = self.project_task.search(cr, self.user_projectuser_id, [('project_id', '=', pigs_id)])
        test_task_ids = set([self.task_1_id, self.task_2_id, self.task_3_id, self.task_4_id, self.task_5_id, self.task_6_id])
        self.assertEqual(set(task_ids), test_task_ids,
                         'access rights: project user cannot see all tasks of an employees project')

        # Do: Bert reads project -> crash, no group
        self.assertRaises(AccessError, self.project_project.read, cr, self.user_none_id, [pigs_id], ['state'])

        # Do: Chell reads project -> ko (portal ko employee)
        self.assertRaises(except_orm, self.project_project.read, cr, self.user_portal_id, [pigs_id], ['state'])
        # Test: no project task visible + assigned
        task_ids = self.project_task.search(cr, self.user_portal_id, [('project_id', '=', pigs_id)])
        self.assertFalse(task_ids, 'access rights: portal user should not see tasks of an employees project, even if assigned')

        # Do: Donovan reads project -> ko (public ko employee)
        self.assertRaises(except_orm, self.project_project.read, cr, self.user_public_id, [pigs_id], ['state'])
        # Test: no project task visible
        task_ids = self.project_task.search(cr, self.user_public_id, [('project_id', '=', pigs_id)])
        self.assertFalse(task_ids, 'access rights: public user should not see tasks of an employees project')

        # Do: project user is employee and can create a task
        tmp_task_id = self.project_task.create(cr, self.user_projectuser_id, {
            'name': 'Pigs task', 'project_id': pigs_id
        }, {'mail_create_nolog': True})
        self.project_task.unlink(cr, self.user_projectuser_id, [tmp_task_id])

        # ----------------------------------------
        # CASE4: followers project
        # ----------------------------------------
        self.project_project.write(cr, uid, [pigs_id], {'privacy_visibility': 'followers'})
        self.project_project.invalidate_cache(cr, uid)

        # Do: Alfred reads project -> ko (employee ko followers)
        self.assertRaises(except_orm, self.project_project.read, cr, self.user_projectuser_id, [pigs_id], ['state'])
        # Test: no project task visible
        task_ids = self.project_task.search(cr, self.user_projectuser_id, [('project_id', '=', pigs_id)])
        test_task_ids = set([self.task_4_id])
        self.assertEqual(set(task_ids), test_task_ids,
                         'access rights: employee user should not see tasks of a not-followed followers project, only assigned')

        # Do: Bert reads project -> crash, no group
        self.assertRaises(AccessError, self.project_project.read, cr, self.user_none_id, [pigs_id], ['state'])

        # Do: Chell reads project -> ko (portal ko followers)
        self.project_project.message_unsubscribe_users(cr, self.user_portal_id, [pigs_id], [self.user_portal_id])
        self.assertRaises(except_orm, self.project_project.read, cr, self.user_portal_id, [pigs_id], ['state'])
        # Test: no project task visible
        task_ids = self.project_task.search(cr, self.user_portal_id, [('project_id', '=', pigs_id)])
        test_task_ids = set([self.task_5_id])
        self.assertEqual(set(task_ids), test_task_ids,
                         'access rights: portal user should not see tasks of a not-followed followers project, only assigned')

        # Do: Donovan reads project -> ko (public ko employee)
        self.assertRaises(except_orm, self.project_project.read, cr, self.user_public_id, [pigs_id], ['state'])
        # Test: no project task visible
        task_ids = self.project_task.search(cr, self.user_public_id, [('project_id', '=', pigs_id)])
        self.assertFalse(task_ids, 'access rights: public user should not see tasks of a followers project')

        # Data: subscribe Alfred, Chell and Donovan as follower
        self.project_project.message_subscribe_users(cr, uid, [pigs_id], [self.user_projectuser_id, self.user_portal_id, self.user_public_id])
        self.project_task.message_subscribe_users(cr, self.user_manager_id, [self.task_1_id, self.task_3_id], [self.user_portal_id, self.user_projectuser_id])

        # Do: Alfred reads project -> ok (follower ok followers)
        self.project_project.read(cr, self.user_projectuser_id, [pigs_id], ['state'])

        # Do: Chell reads project -> ok (follower ok follower)
        self.project_project.read(cr, self.user_portal_id, [pigs_id], ['state'])

        # Do: Donovan reads project -> ko (public ko follower even if follower)
        self.assertRaises(except_orm, self.project_project.read, cr, self.user_public_id, [pigs_id], ['state'])

        # Do: project user is follower of the project and can create a task
        self.project_task.create(cr, self.user_projectuser_id, {
            'name': 'Pigs task', 'project_id': pigs_id
        }, {'mail_create_nolog': True})

        # not follower user should not be able to create a task
        self.project_project.message_unsubscribe_users(cr, self.user_projectuser_id, [pigs_id], [self.user_projectuser_id])
        self.assertRaises(except_orm,
            self.project_task.create, cr, self.user_projectuser_id, {'name': 'Pigs task', 'project_id': pigs_id}, {'mail_create_nolog': True}
        )

        # Do: project user can create a task without project
        self.project_task.create(cr, self.user_projectuser_id, {
            'name': 'Pigs task', 'project_id': False
        }, {'mail_create_nolog': True})
