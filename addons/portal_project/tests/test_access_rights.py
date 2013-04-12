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

from openerp.osv.orm import except_orm
from openerp.tests import common
from openerp.tools import mute_logger


class TestPortalProject(common.TransactionCase):

    def setUp(self):
        super(TestPortalProject, self).setUp()
        cr, uid = self.cr, self.uid

        # Useful models
        self.project_project = self.registry('project.project')
        self.project_task = self.registry('project.task')
        self.res_users = self.registry('res.users')
        self.res_partner = self.registry('res.partner')

        # Find Employee group
        group_employee_ref = self.registry('ir.model.data').get_object_reference(cr, uid, 'base', 'group_user')
        self.group_employee_id = group_employee_ref and group_employee_ref[1] or False

        # Find Project User group
        group_project_user_ref = self.registry('ir.model.data').get_object_reference(cr, uid, 'project', 'group_project_user')
        self.group_project_user_id = group_project_user_ref and group_project_user_ref[1] or False

        # Find Project Manager group
        group_project_manager_ref = self.registry('ir.model.data').get_object_reference(cr, uid, 'project', 'group_project_manager')
        self.group_project_manager_id = group_project_manager_ref and group_project_manager_ref[1] or False

        # Find Portal group
        group_portal_ref = self.registry('ir.model.data').get_object_reference(cr, uid, 'portal', 'group_portal')
        self.group_portal_id = group_portal_ref and group_portal_ref[1] or False

        # Find Anonymous group
        group_anonymous_ref = self.registry('ir.model.data').get_object_reference(cr, uid, 'portal', 'group_anonymous')
        self.group_anonymous_id = group_anonymous_ref and group_anonymous_ref[1] or False

        # Test users to use through the various tests
        self.user_alfred_id = self.res_users.create(cr, uid, {
                        'name': 'Alfred EmployeeUser',
                        'login': 'alfred',
                        'alias_name': 'alfred',
                        'groups_id': [(6, 0, [self.group_employee_id, self.group_project_user_id])]
                    })
        self.user_bert_id = self.res_users.create(cr, uid, {
                        'name': 'Bert Nobody',
                        'login': 'bert',
                        'alias_name': 'bert',
                        'groups_id': [(6, 0, [])]
                    })
        self.user_chell_id = self.res_users.create(cr, uid, {
                        'name': 'Chell Portal',
                        'login': 'chell',
                        'alias_name': 'chell',
                        'groups_id': [(6, 0, [self.group_portal_id])]
                    })
        self.user_donovan_id = self.res_users.create(cr, uid, {
                        'name': 'Donovan Anonymous',
                        'login': 'donovan',
                        'alias_name': 'donovan',
                        'groups_id': [(6, 0, [self.group_anonymous_id])]
                    })
        self.user_ernest_id = self.res_users.create(cr, uid, {
                        'name': 'Ernest Manager',
                        'login': 'ernest',
                        'alias_name': 'ernest',
                        'groups_id': [(6, 0, [self.group_project_manager_id])]
                    })

        # Test 'Pigs' project
        self.project_pigs_id = self.project_project.create(cr, uid,
            {'name': 'Pigs', 'alias_contact': 'everyone', 'privacy_visibility': 'public'},
            {'mail_create_nolog': True})
        # Various test tasks
        self.task_1_id = self.project_task.create(cr, uid,
            {'name': 'Test1', 'user_id': False, 'project_id': self.project_pigs_id},
            {'mail_create_nolog': True})
        self.task_2_id = self.project_task.create(cr, uid,
            {'name': 'Test2', 'user_id': False, 'project_id': self.project_pigs_id},
            {'mail_create_nolog': True})
        self.task_3_id = self.project_task.create(cr, uid,
            {'name': 'Test3', 'user_id': False, 'project_id': self.project_pigs_id},
            {'mail_create_nolog': True})
        self.task_4_id = self.project_task.create(cr, uid,
            {'name': 'Test4', 'user_id': self.user_alfred_id, 'project_id': self.project_pigs_id},
            {'mail_create_nolog': True})
        self.task_5_id = self.project_task.create(cr, uid,
            {'name': 'Test5', 'user_id': self.user_chell_id, 'project_id': self.project_pigs_id},
            {'mail_create_nolog': True})
        self.task_6_id = self.project_task.create(cr, uid,
            {'name': 'Test6', 'user_id': self.user_donovan_id, 'project_id': self.project_pigs_id},
            {'mail_create_nolog': True})

    @mute_logger('openerp.addons.base.ir.ir_model', 'openerp.osv.orm')
    def test_00_project_access_rights(self):
        """ Test basic project access rights, for project and portal_project """
        cr, uid, pigs_id = self.cr, self.uid, self.project_pigs_id

        # ----------------------------------------
        # CASE1: public project
        # ----------------------------------------

        # Do: Alfred reads project -> ok (employee ok public)
        self.project_project.read(cr, self.user_alfred_id, pigs_id, ['name'])
        # Test: all project tasks visible
        task_ids = self.project_task.search(cr, self.user_alfred_id, [('project_id', '=', pigs_id)])
        test_task_ids = set([self.task_1_id, self.task_2_id, self.task_3_id, self.task_4_id, self.task_5_id, self.task_6_id])
        self.assertEqual(set(task_ids), test_task_ids,
                        'access rights: project user cannot see all tasks of a public project')
        # Test: all project tasks readable
        self.project_task.read(cr, self.user_alfred_id, task_ids, ['name'])
        # Test: all project tasks writable
        self.project_task.write(cr, self.user_alfred_id, task_ids, {'description': 'TestDescription'})

        # Do: Bert reads project -> crash, no group
        self.assertRaises(except_orm, self.project_project.read,
            cr, self.user_bert_id, pigs_id, ['name'])
        # Test: no project task visible
        self.assertRaises(except_orm, self.project_task.search,
            cr, self.user_bert_id, [('project_id', '=', pigs_id)])
        # Test: no project task readable
        self.assertRaises(except_orm, self.project_task.read,
            cr, self.user_bert_id, task_ids, ['name'])
        # Test: no project task writable
        self.assertRaises(except_orm, self.project_task.write,
            cr, self.user_bert_id, task_ids, {'description': 'TestDescription'})

        # Do: Chell reads project -> ok (portal ok public)
        self.project_project.read(cr, self.user_chell_id, pigs_id, ['name'])
        # Test: all project tasks visible
        task_ids = self.project_task.search(cr, self.user_chell_id, [('project_id', '=', pigs_id)])
        self.assertEqual(set(task_ids), test_task_ids,
                        'access rights: project user cannot see all tasks of a public project')
        # Test: all project tasks readable
        self.project_task.read(cr, self.user_chell_id, task_ids, ['name'])
        # Test: no project task writable
        self.assertRaises(except_orm, self.project_task.write,
            cr, self.user_chell_id, task_ids, {'description': 'TestDescription'})

        # Do: Donovan reads project -> ok (anonymous ok public)
        self.project_project.read(cr, self.user_donovan_id, pigs_id, ['name'])
        # Test: all project tasks visible
        task_ids = self.project_task.search(cr, self.user_donovan_id, [('project_id', '=', pigs_id)])
        self.assertEqual(set(task_ids), test_task_ids,
                        'access rights: anonymous user cannot see all tasks of a public project')
        # Test: all project tasks readable
        self.project_task.read(cr, self.user_donovan_id, task_ids, ['name'])
        # Test: no project task writable
        self.assertRaises(except_orm, self.project_task.write,
            cr, self.user_donovan_id, task_ids, {'description': 'TestDescription'})

        # ----------------------------------------
        # CASE2: portal project
        # ----------------------------------------
        self.project_project.write(cr, uid, [pigs_id], {'privacy_visibility': 'portal'})

        # Do: Alfred reads project -> ok (employee ok public)
        self.project_project.read(cr, self.user_alfred_id, pigs_id, ['name'])
        # Test: all project tasks visible
        task_ids = self.project_task.search(cr, self.user_alfred_id, [('project_id', '=', pigs_id)])
        self.assertEqual(set(task_ids), test_task_ids,
                        'access rights: project user cannot see all tasks of a portal project')

        # Do: Bert reads project -> crash, no group
        self.assertRaises(except_orm, self.project_project.read,
            cr, self.user_bert_id, pigs_id, ['name'])
        # Test: no project task searchable
        self.assertRaises(except_orm, self.project_task.search,
            cr, self.user_bert_id, [('project_id', '=', pigs_id)])

        # Data: task follower
        self.project_task.message_subscribe_users(cr, self.user_alfred_id, [self.task_1_id, self.task_3_id], [self.user_chell_id])

        # Do: Chell reads project -> ok (portal ok public)
        self.project_project.read(cr, self.user_chell_id, pigs_id, ['name'])
        # Test: only followed project tasks visible + assigned
        task_ids = self.project_task.search(cr, self.user_chell_id, [('project_id', '=', pigs_id)])
        test_task_ids = set([self.task_1_id, self.task_3_id, self.task_5_id])
        self.assertEqual(set(task_ids), test_task_ids,
                        'access rights: portal user should see the followed tasks of a portal project')

        # Do: Donovan reads project -> ko (anonymous ko portal)
        self.assertRaises(except_orm, self.project_project.read,
            cr, self.user_donovan_id, pigs_id, ['name'])
        # Test: no project task visible
        task_ids = self.project_task.search(cr, self.user_donovan_id, [('project_id', '=', pigs_id)])
        self.assertFalse(task_ids, 'access rights: anonymous user should not see tasks of a portal project')

        # Data: task follower cleaning
        self.project_task.message_unsubscribe_users(cr, self.user_alfred_id, [self.task_1_id, self.task_3_id], [self.user_chell_id])

        # ----------------------------------------
        # CASE3: employee project
        # ----------------------------------------
        self.project_project.write(cr, uid, [pigs_id], {'privacy_visibility': 'employees'})

        # Do: Alfred reads project -> ok (employee ok employee)
        self.project_project.read(cr, self.user_alfred_id, pigs_id, ['name'])
        # Test: all project tasks visible
        task_ids = self.project_task.search(cr, self.user_alfred_id, [('project_id', '=', pigs_id)])
        test_task_ids = set([self.task_1_id, self.task_2_id, self.task_3_id, self.task_4_id, self.task_5_id, self.task_6_id])
        self.assertEqual(set(task_ids), test_task_ids,
                        'access rights: project user cannot see all tasks of an employees project')

        # Do: Bert reads project -> crash, no group
        self.assertRaises(except_orm, self.project_project.read,
            cr, self.user_bert_id, pigs_id, ['name'])

        # Do: Chell reads project -> ko (portal ko employee)
        self.assertRaises(except_orm, self.project_project.read,
            cr, self.user_chell_id, pigs_id, ['name'])
        # Test: no project task visible + assigned
        task_ids = self.project_task.search(cr, self.user_chell_id, [('project_id', '=', pigs_id)])
        self.assertFalse(task_ids, 'access rights: portal user should not see tasks of an employees project, even if assigned')

        # Do: Donovan reads project -> ko (anonymous ko employee)
        self.assertRaises(except_orm, self.project_project.read,
            cr, self.user_donovan_id, pigs_id, ['name'])
        # Test: no project task visible
        task_ids = self.project_task.search(cr, self.user_donovan_id, [('project_id', '=', pigs_id)])
        self.assertFalse(task_ids, 'access rights: anonymous user should not see tasks of an employees project')

        # ----------------------------------------
        # CASE4: followers project
        # ----------------------------------------
        self.project_project.write(cr, uid, [pigs_id], {'privacy_visibility': 'followers'})

        # Do: Alfred reads project -> ko (employee ko followers)
        self.assertRaises(except_orm, self.project_project.read,
            cr, self.user_alfred_id, pigs_id, ['name'])
        # Test: no project task visible
        task_ids = self.project_task.search(cr, self.user_alfred_id, [('project_id', '=', pigs_id)])
        test_task_ids = set([self.task_4_id])
        self.assertEqual(set(task_ids), test_task_ids,
                        'access rights: employee user should not see tasks of a not-followed followers project, only assigned')

        # Do: Bert reads project -> crash, no group
        self.assertRaises(except_orm, self.project_project.read,
            cr, self.user_bert_id, pigs_id, ['name'])

        # Do: Chell reads project -> ko (portal ko employee)
        self.assertRaises(except_orm, self.project_project.read,
            cr, self.user_chell_id, pigs_id, ['name'])
        # Test: no project task visible
        task_ids = self.project_task.search(cr, self.user_chell_id, [('project_id', '=', pigs_id)])
        test_task_ids = set([self.task_5_id])
        self.assertEqual(set(task_ids), test_task_ids,
                        'access rights: portal user should not see tasks of a not-followed followers project, only assigned')

        # Do: Donovan reads project -> ko (anonymous ko employee)
        self.assertRaises(except_orm, self.project_project.read,
            cr, self.user_donovan_id, pigs_id, ['name'])
        # Test: no project task visible
        task_ids = self.project_task.search(cr, self.user_donovan_id, [('project_id', '=', pigs_id)])
        self.assertFalse(task_ids, 'access rights: anonymous user should not see tasks of a followers project')

        # Data: subscribe Alfred, Chell and Donovan as follower
        self.project_project.message_subscribe_users(cr, uid, [pigs_id], [self.user_alfred_id, self.user_chell_id, self.user_donovan_id])
        self.project_task.message_subscribe_users(cr, self.user_alfred_id, [self.task_1_id, self.task_3_id], [self.user_chell_id, self.user_alfred_id])

        # Do: Alfred reads project -> ok (follower ok followers)
        self.project_project.read(cr, self.user_alfred_id, pigs_id, ['name'])
        # Test: followed + assigned tasks visible
        task_ids = self.project_task.search(cr, self.user_alfred_id, [('project_id', '=', pigs_id)])
        test_task_ids = set([self.task_1_id, self.task_3_id, self.task_4_id])
        self.assertEqual(set(task_ids), test_task_ids,
                        'access rights: employee user should not see followed + assigned tasks of a follower project')

        # Do: Chell reads project -> ok (follower ok follower)
        self.project_project.read(cr, self.user_chell_id, pigs_id, ['name'])
        # Test: followed + assigned tasks visible
        task_ids = self.project_task.search(cr, self.user_chell_id, [('project_id', '=', pigs_id)])
        test_task_ids = set([self.task_1_id, self.task_3_id, self.task_5_id])
        self.assertEqual(set(task_ids), test_task_ids,
                        'access rights: employee user should not see followed + assigned tasks of a follower project')

        # Do: Donovan reads project -> ko (anonymous ko follower even if follower)
        self.assertRaises(except_orm, self.project_project.read,
            cr, self.user_donovan_id, pigs_id, ['name'])
