# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.project.tests.test_project_base import TestProjectBase
from odoo.exceptions import AccessError
from odoo.tools import mute_logger


class TestPortalProjectBase(TestProjectBase):

    def setUp(self):
        super(TestPortalProjectBase, self).setUp()
        self.user_noone = self.env['res.users'].with_context({'no_reset_password': True, 'mail_create_nosubscribe': True}).create({
            'name': 'Noemie NoOne',
            'login': 'noemie',
            'email': 'n.n@example.com',
            'signature': '--\nNoemie',
            'notification_type': 'email',
            'groups_id': [(6, 0, [])]})

        self.task_3 = self.env['project.task'].with_context({'mail_create_nolog': True}).create({
            'name': 'Test3', 'user_id': self.user_portal.id, 'project_id': self.project_pigs.id})
        self.task_4 = self.env['project.task'].with_context({'mail_create_nolog': True}).create({
            'name': 'Test4', 'user_id': self.user_public.id, 'project_id': self.project_pigs.id})
        self.task_5 = self.env['project.task'].with_context({'mail_create_nolog': True}).create({
            'name': 'Test5', 'user_id': False, 'project_id': self.project_pigs.id})
        self.task_6 = self.env['project.task'].with_context({'mail_create_nolog': True}).create({
            'name': 'Test5', 'user_id': False, 'project_id': self.project_pigs.id})


class TestPortalProject(TestPortalProjectBase):

    @mute_logger('odoo.addons.base.models.ir_model')
    def test_employee_project_access_rights(self):
        pigs = self.project_pigs

        pigs.write({'privacy_visibility': 'employees'})
        # Do: Alfred reads project -> ok (employee ok employee)
        pigs.with_user(self.user_projectuser).read(['user_id'])
        # Test: all project tasks visible
        tasks = self.env['project.task'].with_user(self.user_projectuser).search([('project_id', '=', pigs.id)])
        test_task_ids = set([self.task_1.id, self.task_2.id, self.task_3.id, self.task_4.id, self.task_5.id, self.task_6.id])
        self.assertEqual(set(tasks.ids), test_task_ids,
                        'access rights: project user cannot see all tasks of an employees project')
        # Do: Bert reads project -> crash, no group
        self.assertRaises(AccessError, pigs.with_user(self.user_noone).read, ['user_id'])
        # Do: Donovan reads project -> ko (public ko employee)
        self.assertRaises(AccessError, pigs.with_user(self.user_public).read, ['user_id'])
        # Do: project user is employee and can create a task
        tmp_task = self.env['project.task'].with_user(self.user_projectuser).with_context({'mail_create_nolog': True}).create({
            'name': 'Pigs task',
            'project_id': pigs.id})
        tmp_task.with_user(self.user_projectuser).unlink()

    @mute_logger('odoo.addons.base.models.ir_model')
    def test_favorite_project_access_rights(self):
        pigs = self.project_pigs.with_user(self.user_projectuser)

        # we can't write on project name
        self.assertRaises(AccessError, pigs.write, {'name': 'False Pigs'})
        # we can write on is_favorite
        pigs.write({'is_favorite': True})

    @mute_logger('odoo.addons.base.ir.ir_model')
    def test_followers_project_access_rights(self):
        pigs = self.project_pigs
        pigs.write({'privacy_visibility': 'followers'})
        pigs.flush(['privacy_visibility'])
        # Do: Alfred reads project -> ko (employee ko followers)
        self.assertRaises(AccessError, pigs.with_user(self.user_projectuser).read, ['user_id'])
        # Test: no project task visible
        tasks = self.env['project.task'].with_user(self.user_projectuser).search([('project_id', '=', pigs.id)])
        self.assertEqual(tasks, self.task_1,
                         'access rights: employee user should not see tasks of a not-followed followers project, only assigned')

        # Do: Bert reads project -> crash, no group
        self.assertRaises(AccessError, pigs.with_user(self.user_noone).read, ['user_id'])

        # Do: Donovan reads project -> ko (public ko employee)
        self.assertRaises(AccessError, pigs.with_user(self.user_public).read, ['user_id'])

        pigs.message_subscribe(partner_ids=[self.user_projectuser.partner_id.id])

        # Do: Alfred reads project -> ok (follower ok followers)
        donkey = pigs.with_user(self.user_projectuser)
        donkey.invalidate_cache()
        donkey.read(['user_id'])

        # Do: Donovan reads project -> ko (public ko follower even if follower)
        self.assertRaises(AccessError, pigs.with_user(self.user_public).read, ['user_id'])
        # Do: project user is follower of the project and can create a task
        self.env['project.task'].with_user(self.user_projectuser).with_context({'mail_create_nolog': True}).create({
            'name': 'Pigs task', 'project_id': pigs.id
        })
        # not follower user should not be able to create a task
        pigs.with_user(self.user_projectuser).message_unsubscribe(partner_ids=[self.user_projectuser.partner_id.id])
        self.assertRaises(AccessError, self.env['project.task'].with_user(self.user_projectuser).with_context({
            'mail_create_nolog': True}).create, {'name': 'Pigs task', 'project_id': pigs.id})

        # Do: project user can create a task without project
        self.assertRaises(AccessError, self.env['project.task'].with_user(self.user_projectuser).with_context({
            'mail_create_nolog': True}).create, {'name': 'Pigs task', 'project_id': pigs.id})
