# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.project.tests.test_access_rights import TestPortalProjectBase
from odoo.exceptions import AccessError
from odoo.tools import mute_logger


class TestPortalProject(TestPortalProjectBase):
    @mute_logger('odoo.addons.base.models.ir_model')
    def test_portal_project_access_rights(self):
        pigs = self.project_pigs
        pigs.write({'privacy_visibility': 'portal'})

        # Do: Alfred reads project -> ok (employee ok public)
        pigs.sudo(self.user_projectuser).read(['user_id'])
        # Test: all project tasks visible
        tasks = self.env['project.task'].sudo(self.user_projectuser).search([('project_id', '=', pigs.id)])
        self.assertEqual(tasks, self.task_1 | self.task_2 | self.task_3 | self.task_4 | self.task_5 | self.task_6,
                         'access rights: project user should see all tasks of a portal project')

        # Do: Bert reads project -> crash, no group
        self.assertRaises(AccessError, pigs.sudo(self.user_noone).read, ['user_id'])
        # Test: no project task searchable
        self.assertRaises(AccessError, self.env['project.task'].sudo(self.user_noone).search, [('project_id', '=', pigs.id)])

        # Data: task follower
        pigs.sudo(self.user_projectmanager).message_subscribe_users(user_ids=[self.user_portal.id])
        self.task_1.sudo(self.user_projectuser).message_subscribe_users(user_ids=[self.user_portal.id])
        self.task_3.sudo(self.user_projectuser).message_subscribe_users(user_ids=[self.user_portal.id])
        # Do: Chell reads project -> ok (portal ok public)
        pigs.sudo(self.user_portal).read(['user_id'])
        # Do: Donovan reads project -> ko (public ko portal)
        self.assertRaises(AccessError, pigs.sudo(self.user_public).read, ['user_id'])
        # Test: no access right to project.task
        self.assertRaises(AccessError, self.env['project.task'].sudo(self.user_public).search, [])
        # Data: task follower cleaning
        self.task_1.sudo(self.user_projectuser).message_unsubscribe_users(user_ids=[self.user_portal.id])
        self.task_3.sudo(self.user_projectuser).message_unsubscribe_users(user_ids=[self.user_portal.id])
