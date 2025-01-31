# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.addons.project.tests.test_access_rights import TestProjectPortalCommon
from odoo.exceptions import AccessError
from odoo.tests import HttpCase
from odoo.tools import mute_logger


class TestPortalProject(TestProjectPortalCommon, HttpCase):
    @mute_logger('odoo.addons.base.models.ir_model')
    def test_portal_project_access_rights(self):
        pigs = self.project_pigs
        pigs.write({'privacy_visibility': 'portal'})

        # Do: Alfred reads project -> ok (employee ok public)
        pigs.with_user(self.user_projectuser).read(['user_id'])
        # Test: all project tasks visible
        tasks = self.env['project.task'].with_user(self.user_projectuser).search([('project_id', '=', pigs.id)])
        self.assertEqual(tasks, self.task_1 | self.task_2 | self.task_3 | self.task_4 | self.task_5 | self.task_6,
                         'access rights: project user should see all tasks of a portal project')

        # Do: Bert reads project -> crash, no group
        self.assertRaises(AccessError, pigs.with_user(self.user_noone).read, ['user_id'])
        # Test: no project task searchable
        self.assertRaises(AccessError, self.env['project.task'].with_user(self.user_noone).search, [('project_id', '=', pigs.id)])

        # Data: task follower
        pigs.with_user(self.user_projectmanager).message_subscribe(partner_ids=[self.user_portal.partner_id.id])
        self.task_1.with_user(self.user_projectuser).message_subscribe(partner_ids=[self.user_portal.partner_id.id])
        self.task_3.with_user(self.user_projectuser).message_subscribe(partner_ids=[self.user_portal.partner_id.id])
        # Do: Chell reads project -> ok (portal ok public)
        pigs.with_user(self.user_portal).read(['user_id'])
        # Do: Donovan reads project -> ko (public ko portal)
        self.assertRaises(AccessError, pigs.with_user(self.user_public).read, ['user_id'])
        # Test: no access right to project.task
        self.assertRaises(AccessError, self.env['project.task'].with_user(self.user_public).search, [])
        # Data: task follower cleaning
        self.task_1.with_user(self.user_projectuser).message_unsubscribe(partner_ids=[self.user_portal.partner_id.id])
        self.task_3.with_user(self.user_projectuser).message_unsubscribe(partner_ids=[self.user_portal.partner_id.id])

    def test_reset_access_token_when_privacy_visibility_changes(self):
        self.assertNotEqual(self.project_pigs.privacy_visibility, 'portal', 'Make sure the privacy visibility is not yet the portal one.')
        self.assertFalse(self.project_pigs.access_token, 'The access token should not be set on the project since it is not public')
        self.project_pigs.privacy_visibility = 'portal'
        self.assertFalse(self.project_pigs.access_token, 'The access token should not yet available since the project has not been shared yet.')
        wizard = self.env['project.share.wizard'].create({
            'res_model': 'project.project',
            'res_id': self.project_pigs.id,
            'collaborator_ids': [
                Command.create({
                    'partner_id': self.partner_1.id,
                }),
            ]
        })
        wizard.action_send_mail()
        self.assertEqual(self.task_1.project_id, self.project_pigs)
        self.assertTrue(self.project_pigs.access_token, 'The access token should be set since the project has been shared.')
        self.assertTrue(self.task_1.access_token, 'The access token should be set since the task has been shared.')
        access_token = self.project_pigs.access_token
        task_access_token = self.task_1.access_token
        self.project_pigs.privacy_visibility = 'followers'
        self.assertFalse(self.project_pigs.access_token, 'The access token should no longer be set since now the project is private.')
        self.assertFalse(all(self.project_pigs.tasks.mapped('access_token')), 'The access token should no longer be set in any tasks linked to the project since now the project is private.')
        self.project_pigs.privacy_visibility = 'portal'
        self.assertFalse(self.project_pigs.access_token, 'The access token should still not be set since now the project has not been shared yet.')
        self.assertFalse(all(self.project_pigs.tasks.mapped('access_token')), 'The access token should no longer be set in any tasks linked to the project since now the project is private.')
        wizard.action_send_mail()
        self.assertTrue(self.project_pigs.access_token, 'The access token should now be regenerated for this project since that project has been shared to an external partner.')
        self.assertFalse(self.task_1.access_token)
        task_wizard = self.env['portal.share'].create({
            'res_model': 'project.task',
            'res_id': self.task_1.id,
            'partner_ids': [
                Command.link(self.partner_1.id),
            ],
        })
        task_wizard.action_send_mail()
        self.assertTrue(self.task_1.access_token, 'The access token should be set since the task has been shared.')
        self.assertNotEqual(self.project_pigs.access_token, access_token, 'The new access token generated for the project should not be the old one.')
        self.assertNotEqual(self.task_1.access_token, task_access_token, 'The new access token generated for the task should not be the old one.')
        self.project_pigs.privacy_visibility = 'employees'
        self.assertFalse(self.project_pigs.access_token, 'The access token should no longer be set since now the project is only available by internal users.')
        self.assertFalse(all(self.project_pigs.tasks.mapped('access_token')), 'The access token should no longer be set in any tasks linked to the project since now the project is only available by internal users.')

    def test_search_validates_results(self):
        project_manager = self.env['res.users'].search([
            ('group_ids', 'in', [self.env.ref('project.group_project_manager').id])
        ],limit=1)
        self.authenticate(project_manager.login, project_manager.login)
        self.project_1 = self.env['project.project'].create({'name': 'Portal Search Project 1'})
        self.project_2 = self.env['project.project'].create({'name': 'Portal Search Project 2'})
        self.task_1 = self.env['project.task'].create({
            'name': 'Test Task Name Match',
            'project_id': self.project_1.id,
            'user_ids': project_manager,
        })

        self.task_2 = self.env['project.task'].create({
            'name': 'Another Task For Searching',
            'project_id': self.project_2.id,
            'user_ids': project_manager,
        })

        url = '/my/tasks'
        response = self.url_open(url)
        self.assertIn(self.task_1.name, response.text)
        self.assertIn(self.task_2.name, response.text)

        url = '/my/tasks?search_in=name&search=Test+Task+Name+Match'
        response = self.url_open(url)
        self.assertIn(self.task_1.name, response.text)
        self.assertNotIn(self.task_2.name, response.text)

        url = '/my/tasks?search_in=project_id&search=%s' % (self.project_1.name)
        response = self.url_open(url)
        self.assertIn(self.task_1.name, response.text)
        self.assertNotIn(self.task_2.name, response.text)
