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

from openerp.addons.portal_project.tests.test_access_rights import TestPortalProject
from openerp.osv.orm import except_orm
from openerp.tools import mute_logger


class TestPortalIssueProject(TestPortalProject):

    def setUp(self):
        super(TestPortalIssueProject, self).setUp()
        cr, uid = self.cr, self.uid

        # Useful models
        self.project_issue = self.registry('project.issue')

        # Various test issues
        self.issue_1_id = self.project_issue.create(cr, uid,
            {'name': 'Test1', 'user_id': False, 'project_id': self.project_pigs_id},
            {'mail_create_nolog': True})
        self.issue_2_id = self.project_issue.create(cr, uid,
            {'name': 'Test2', 'user_id': False, 'project_id': self.project_pigs_id},
            {'mail_create_nolog': True})
        self.issue_3_id = self.project_issue.create(cr, uid,
            {'name': 'Test3', 'user_id': False, 'project_id': self.project_pigs_id},
            {'mail_create_nolog': True})
        self.issue_4_id = self.project_issue.create(cr, uid,
            {'name': 'Test4', 'user_id': self.user_alfred_id, 'project_id': self.project_pigs_id},
            {'mail_create_nolog': True})
        self.issue_5_id = self.project_issue.create(cr, uid,
            {'name': 'Test5', 'user_id': self.user_chell_id, 'project_id': self.project_pigs_id},
            {'mail_create_nolog': True})
        self.issue_6_id = self.project_issue.create(cr, uid,
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
        # Test: all project issues visible
        issue_ids = self.project_issue.search(cr, self.user_alfred_id, [('project_id', '=', pigs_id)])
        test_issue_ids = set([self.issue_1_id, self.issue_2_id, self.issue_3_id, self.issue_4_id, self.issue_5_id, self.issue_6_id])
        self.assertEqual(set(issue_ids), test_issue_ids,
                        'access rights: project user cannot see all issues of a public project')
        # Test: all project issues readable
        self.project_issue.read(cr, self.user_alfred_id, issue_ids, ['name'])
        # Test: all project issues writable
        self.project_issue.write(cr, self.user_alfred_id, issue_ids, {'description': 'TestDescription'})

        # Do: Bert reads project -> crash, no group
        # Test: no project issue visible
        self.assertRaises(except_orm, self.project_issue.search,
            cr, self.user_bert_id, [('project_id', '=', pigs_id)])
        # Test: no project issue readable
        self.assertRaises(except_orm, self.project_issue.read,
            cr, self.user_bert_id, issue_ids, ['name'])
        # Test: no project issue writable
        self.assertRaises(except_orm, self.project_issue.write,
            cr, self.user_bert_id, issue_ids, {'description': 'TestDescription'})

        # Do: Chell reads project -> ok (portal ok public)
        # Test: all project issues visible
        issue_ids = self.project_issue.search(cr, self.user_chell_id, [('project_id', '=', pigs_id)])
        self.assertEqual(set(issue_ids), test_issue_ids,
                        'access rights: project user cannot see all issues of a public project')
        # Test: all project issues readable
        self.project_issue.read(cr, self.user_chell_id, issue_ids, ['name'])
        # Test: no project issue writable
        self.assertRaises(except_orm, self.project_issue.write,
            cr, self.user_chell_id, issue_ids, {'description': 'TestDescription'})

        # Do: Donovan reads project -> ok (anonymous ok public)
        # Test: no project issue visible (no read on project.issue)
        self.assertRaises(except_orm, self.project_issue.search,
            cr, self.user_donovan_id, [('project_id', '=', pigs_id)])

        # ----------------------------------------
        # CASE2: portal project
        # ----------------------------------------
        self.project_project.write(cr, uid, [pigs_id], {'privacy_visibility': 'portal'})

        # Do: Alfred reads project -> ok (employee ok public)
        # Test: all project issues visible
        issue_ids = self.project_issue.search(cr, self.user_alfred_id, [('project_id', '=', pigs_id)])
        self.assertEqual(set(issue_ids), test_issue_ids,
                        'access rights: project user cannot see all issues of a portal project')

        # Do: Bert reads project -> crash, no group
        # Test: no project issue searchable
        self.assertRaises(except_orm, self.project_issue.search,
            cr, self.user_bert_id, [('project_id', '=', pigs_id)])

        # Data: issue follower
        self.project_issue.message_subscribe_users(cr, self.user_alfred_id, [self.issue_1_id, self.issue_3_id], [self.user_chell_id])

        # Do: Chell reads project -> ok (portal ok public)
        # Test: only followed project issues visible + assigned
        issue_ids = self.project_issue.search(cr, self.user_chell_id, [('project_id', '=', pigs_id)])
        test_issue_ids = set([self.issue_1_id, self.issue_3_id, self.issue_5_id])
        self.assertEqual(set(issue_ids), test_issue_ids,
                        'access rights: portal user should see the followed issues of a portal project')

        # Data: issue follower cleaning
        self.project_issue.message_unsubscribe_users(cr, self.user_alfred_id, [self.issue_1_id, self.issue_3_id], [self.user_chell_id])

        # ----------------------------------------
        # CASE3: employee project
        # ----------------------------------------
        self.project_project.write(cr, uid, [pigs_id], {'privacy_visibility': 'employees'})

        # Do: Alfred reads project -> ok (employee ok employee)
        # Test: all project issues visible
        issue_ids = self.project_issue.search(cr, self.user_alfred_id, [('project_id', '=', pigs_id)])
        test_issue_ids = set([self.issue_1_id, self.issue_2_id, self.issue_3_id, self.issue_4_id, self.issue_5_id, self.issue_6_id])
        self.assertEqual(set(issue_ids), test_issue_ids,
                        'access rights: project user cannot see all issues of an employees project')

        # Do: Chell reads project -> ko (portal ko employee)
        # Test: no project issue visible + assigned
        issue_ids = self.project_issue.search(cr, self.user_chell_id, [('project_id', '=', pigs_id)])
        self.assertFalse(issue_ids, 'access rights: portal user should not see issues of an employees project, even if assigned')

        # ----------------------------------------
        # CASE4: followers project
        # ----------------------------------------
        self.project_project.write(cr, uid, [pigs_id], {'privacy_visibility': 'followers'})

        # Do: Alfred reads project -> ko (employee ko followers)
        # Test: no project issue visible
        issue_ids = self.project_issue.search(cr, self.user_alfred_id, [('project_id', '=', pigs_id)])
        test_issue_ids = set([self.issue_4_id])
        self.assertEqual(set(issue_ids), test_issue_ids,
                        'access rights: employee user should not see issues of a not-followed followers project, only assigned')

        # Do: Chell reads project -> ko (portal ko employee)
        # Test: no project issue visible
        issue_ids = self.project_issue.search(cr, self.user_chell_id, [('project_id', '=', pigs_id)])
        test_issue_ids = set([self.issue_5_id])
        self.assertEqual(set(issue_ids), test_issue_ids,
                        'access rights: portal user should not see issues of a not-followed followers project, only assigned')

        # Data: subscribe Alfred, Chell and Donovan as follower
        self.project_project.message_subscribe_users(cr, uid, [pigs_id], [self.user_alfred_id, self.user_chell_id, self.user_donovan_id])
        self.project_issue.message_subscribe_users(cr, self.user_alfred_id, [self.issue_1_id, self.issue_3_id], [self.user_chell_id, self.user_alfred_id])

        # Do: Alfred reads project -> ok (follower ok followers)
        # Test: followed + assigned issues visible
        issue_ids = self.project_issue.search(cr, self.user_alfred_id, [('project_id', '=', pigs_id)])
        test_issue_ids = set([self.issue_1_id, self.issue_3_id, self.issue_4_id])
        self.assertEqual(set(issue_ids), test_issue_ids,
                        'access rights: employee user should not see followed + assigned issues of a follower project')

        # Do: Chell reads project -> ok (follower ok follower)
        # Test: followed + assigned issues visible
        issue_ids = self.project_issue.search(cr, self.user_chell_id, [('project_id', '=', pigs_id)])
        test_issue_ids = set([self.issue_1_id, self.issue_3_id, self.issue_5_id])
        self.assertEqual(set(issue_ids), test_issue_ids,
                        'access rights: employee user should not see followed + assigned issues of a follower project')
