# -*- coding: utf-8 -*-

from openerp.addons.project.tests.test_access_rights import TestPortalProjectBase
from openerp.exceptions import AccessError
from openerp.tools import mute_logger


class TestPortalProjectBase(TestPortalProjectBase):

    def setUp(self):
        super(TestPortalProjectBase, self).setUp()

        Issue = self.env['project.issue'].with_context({'mail_create_nolog': True})
        self.issue_1 = Issue.create({
            'name': 'Test1', 'user_id': False, 'project_id': self.project_pigs.id})
        self.issue_2 = Issue.create({
            'name': 'Test2', 'user_id': False, 'project_id': self.project_pigs.id})
        self.issue_3 = Issue.create({
            'name': 'Test3', 'user_id': False, 'project_id': self.project_pigs.id})
        self.issue_4 = Issue.create({
            'name': 'Test4', 'user_id': self.user_projectuser.id, 'project_id': self.project_pigs.id})
        self.issue_5 = Issue.create({
            'name': 'Test5', 'user_id': self.user_portal.id, 'project_id': self.project_pigs.id})
        self.issue_6 = Issue.create({
            'name': 'Test6', 'user_id': self.user_public.id, 'project_id': self.project_pigs.id})


class TestPortalIssue(TestPortalProjectBase):
    @mute_logger('openerp.addons.base.ir.ir_model', 'openerp.models')
    def test_00_project_access_rights(self):
        """ Test basic project access rights, for project and portal_project """
        pigs_id = self.project_pigs.id
        Issue = self.env['project.issue']

        # ----------------------------------------
        # CASE1: portal project
        # ----------------------------------------
        self.project_pigs.write({'privacy_visibility': 'portal'})

        # Do: Alfred reads project -> ok (employee ok public)
        # Test: all project issues visible
        issues = Issue.sudo(self.user_projectuser.id).search([('project_id', '=', pigs_id)])
        test_issue_ids = set([self.issue_1.id, self.issue_2.id, self.issue_3.id, self.issue_4.id, self.issue_5.id, self.issue_6.id])
        self.assertEqual(set(issues.ids), test_issue_ids,
                         'access rights: project user cannot see all issues of a portal project')

        # Do: Bert reads project -> crash, no group
        # Test: no project issue searchable
        self.assertRaises(AccessError, Issue.sudo(self.user_noone.id).search, [('project_id', '=', pigs_id)])

        # Data: issue follower
        self.issue_1.sudo(self.user_projectuser.id).message_subscribe_users(user_ids=[self.user_portal.id])
        self.issue_3.sudo(self.user_projectuser.id).message_subscribe_users(user_ids=[self.user_portal.id])

        # Do: Chell reads project -> ok (portal ok public)
        # Test: only followed project issues visible + assigned
        issues = Issue.sudo(self.user_portal.id).search([('project_id', '=', pigs_id)])
        self.assertEqual(set(issues.ids), set([self.issue_1.id, self.issue_3.id, self.issue_5.id]),
                         'access rights: portal user should see the followed issues of a portal project')

        # Data: issue follower cleaning
        self.issue_1.sudo(self.user_projectuser.id).message_unsubscribe_users(user_ids=[self.user_portal.id])
        self.issue_3.sudo(self.user_projectuser.id).message_unsubscribe_users(user_ids=[self.user_portal.id])

        # ----------------------------------------
        # CASE2: employee project
        # ----------------------------------------
        self.project_pigs.write({'privacy_visibility': 'employees'})

        # Do: Alfred reads project -> ok (employee ok employee)
        # Test: all project issues visible
        issues = Issue.sudo(self.user_projectuser.id).search([('project_id', '=', pigs_id)])
        self.assertEqual(set(issues.ids), set([self.issue_1.id, self.issue_2.id, self.issue_3.id,
                        self.issue_4.id, self.issue_5.id, self.issue_6.id]),
                        'access rights: project user cannot see all issues of an employees project')

        # Do: Chell reads project -> ko (portal ko employee)
        # Test: no project issue visible + assigned
        issues = Issue.sudo(self.user_portal.id).search([('project_id', '=', pigs_id)])
        self.assertFalse(issues.ids, 'access rights: portal user should not see issues of an employees project, even if assigned')

        # ----------------------------------------
        # CASE3: followers project
        # ----------------------------------------
        self.project_pigs.write({'privacy_visibility': 'followers'})

        # Do: Alfred reads project -> ko (employee ko followers)
        # Test: no project issue visible
        issues = Issue.sudo(self.user_projectuser.id).search([('project_id', '=', pigs_id)])
        self.assertEqual(set(issues.ids), set([self.issue_4.id]),
                         'access rights: employee user should not see issues of a not-followed followers project, only assigned')

        # Do: Chell reads project -> ko (portal ko employee)
        # Test: no project issue visible
        issues = Issue.sudo(self.user_portal.id).search([('project_id', '=', pigs_id)])
        self.assertEqual(set(issues.ids), set([self.issue_5.id]),
                         'access rights: portal user should not see issues of a not-followed followers project, only assigned')

        # Data: subscribe Alfred, Chell and Donovan as follower
        self.project_pigs.message_subscribe_users(user_ids=[self.user_projectuser.id, self.user_portal.id, self.user_public.id])
        self.issue_1.sudo(self.user_projectmanager.id).message_subscribe_users(user_ids=[self.user_portal.id, self.user_projectuser.id])
        self.issue_3.sudo(self.user_projectmanager.id).message_subscribe_users(user_ids=[self.user_portal.id, self.user_projectuser.id])

        # Do: Alfred reads project -> ok (follower ok followers)
        # Test: followed + assigned issues visible
        issues = Issue.sudo(self.user_projectuser.id).search([('project_id', '=', pigs_id)])
        self.assertEqual(set(issues.ids), set([self.issue_1.id, self.issue_3.id, self.issue_4.id]),
                         'access rights: employee user should not see followed + assigned issues of a follower project')

        # Do: Chell reads project -> ok (follower ok follower)
        # Test: followed + assigned issues visible
        issues = Issue.sudo(self.user_portal.id).search([('project_id', '=', pigs_id)])
        self.assertEqual(set(issues.ids), set([self.issue_1.id, self.issue_3.id, self.issue_5.id]),
                         'access rights: employee user should not see followed + assigned issues of a follower project')
