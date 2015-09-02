# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.addons.project.tests.test_project_base import TestProjectBase
from openerp.exceptions import AccessError
from openerp.exceptions import except_orm
from openerp.tools import mute_logger


class TestPortalProjectBase(TestProjectBase):

    def setUp(self):
        super(TestPortalProjectBase, self).setUp()
        self.user_noone = self.env['res.users'].with_context({'no_reset_password': True, 'mail_create_nosubscribe': True}).create({
            'name': 'Noemie NoOne',
            'login': 'noemie',
            'alias_name': 'noemie',
            'email': 'n.n@example.com',
            'signature': '--\nNoemie',
            'notify_email': 'always',
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

    @mute_logger('openerp.addons.base.ir.ir_model')
    def test_portal_project_access_rights(self):
        pigs = self.project_pigs
        pigs.write({'privacy_visibility': 'portal'})

        # Do: Alfred reads project -> ok (employee ok public)
        pigs.sudo(self.user_projectuser).read(['state'])
        # Test: all project tasks visible
        tasks = self.env['project.task'].sudo(self.user_projectuser).search([('project_id', '=', pigs.id)])
        self.assertEqual(tasks, self.task_1 | self.task_2 | self.task_3 | self.task_4 | self.task_5 | self.task_6,
                         'access rights: project user should see all tasks of a portal project')

        # Do: Bert reads project -> crash, no group
        self.assertRaises(AccessError, pigs.sudo(self.user_noone).read, ['state'])
        # Test: no project task searchable
        self.assertRaises(AccessError, self.env['project.task'].sudo(self.user_noone).search, [('project_id', '=', pigs.id)])

        # Data: task follower
        pigs.sudo(self.user_projectmanager).message_subscribe_users(user_ids=[self.user_portal.id])
        self.task_1.sudo(self.user_projectuser).message_subscribe_users(user_ids=[self.user_portal.id])
        self.task_3.sudo(self.user_projectuser).message_subscribe_users(user_ids=[self.user_portal.id])
        # Do: Chell reads project -> ok (portal ok public)
        pigs.sudo(self.user_portal).read(['state'])
        # Do: Donovan reads project -> ko (public ko portal)
        # TODO: Change the except_orm to Warning ( Because here it's call check_access_rule
        # which still generate exception in except_orm.)
        self.assertRaises(except_orm, pigs.sudo(self.user_public).read, ['state'])
        # Test: no access right to project.task
        self.assertRaises(AccessError, self.env['project.task'].sudo(self.user_public).search, [])
        # Data: task follower cleaning
        self.task_1.sudo(self.user_projectuser).message_unsubscribe_users(user_ids=[self.user_portal.id])
        self.task_3.sudo(self.user_projectuser).message_unsubscribe_users(user_ids=[self.user_portal.id])

    @mute_logger('openerp.addons.base.ir.ir_model')
    def test_employee_project_access_rights(self):
        pigs = self.project_pigs

        pigs.write({'privacy_visibility': 'employees'})
        # Do: Alfred reads project -> ok (employee ok employee)
        pigs.sudo(self.user_projectuser).read(['state'])
        # Test: all project tasks visible
        tasks = self.env['project.task'].sudo(self.user_projectuser).search([('project_id', '=', pigs.id)])
        test_task_ids = set([self.task_1.id, self.task_2.id, self.task_3.id, self.task_4.id, self.task_5.id, self.task_6.id])
        self.assertEqual(set(tasks.ids), test_task_ids,
                        'access rights: project user cannot see all tasks of an employees project')
        # Do: Bert reads project -> crash, no group
        self.assertRaises(AccessError, pigs.sudo(self.user_noone).read, ['state'])
        # Do: Chell reads project -> ko (portal ko employee)
        # TODO Change the except_orm to Warning
        self.assertRaises(except_orm, pigs.sudo(self.user_portal).read, ['state'])
        # Test: no project task visible + assigned
        tasks = self.env['project.task'].sudo(self.user_portal).search([('project_id', '=', pigs.id)])
        self.assertFalse(tasks.ids, 'access rights: portal user should not see tasks of an employees project, even if assigned')
        # Do: Donovan reads project -> ko (public ko employee)
        # TODO Change the except_orm to Warning
        self.assertRaises(except_orm, pigs.sudo(self.user_public).read, ['state'])
        # Do: project user is employee and can create a task
        tmp_task = self.env['project.task'].sudo(self.user_projectuser).with_context({'mail_create_nolog': True}).create({
            'name': 'Pigs task',
            'project_id': pigs.id})
        tmp_task.sudo(self.user_projectuser).unlink()

    @mute_logger('openerp.addons.base.ir.ir_model')
    def test_followers_project_access_rights(self):
        pigs = self.project_pigs
        pigs.write({'privacy_visibility': 'followers'})

        # Do: Alfred reads project -> ko (employee ko followers)
        # TODO Change the except_orm to Warning
        self.assertRaises(AccessError, pigs.sudo(self.user_projectuser).read, ['state'])
        # Test: no project task visible
        tasks = self.env['project.task'].sudo(self.user_projectuser).search([('project_id', '=', pigs.id)])
        self.assertEqual(tasks, self.task_1,
                         'access rights: employee user should not see tasks of a not-followed followers project, only assigned')

        # Do: Bert reads project -> crash, no group
        self.assertRaises(AccessError, pigs.sudo(self.user_noone).read, ['state'])

        # Do: Chell reads project -> ko (portal ko employee)
        self.assertRaises(except_orm, pigs.sudo(self.user_portal).read, ['state'])
        # Test: no project task visible
        tasks = self.env['project.task'].sudo(self.user_portal).search([('project_id', '=', pigs.id)])
        self.assertEqual(tasks, self.task_3,
                         'access rights: portal user should not see tasks of a not-followed followers project, only assigned')

        # Do: Donovan reads project -> ko (public ko employee)
        # TODO Change the except_orm to Warning
        self.assertRaises(except_orm, pigs.sudo(self.user_public).read, ['state'])

        # Data: subscribe Alfred, Chell and Donovan as follower
        pigs.message_subscribe_users(user_ids=[self.user_projectuser.id, self.user_portal.id, self.user_public.id])
        self.task_1.sudo(self.user_projectmanager).message_subscribe_users(user_ids=[self.user_portal.id, self.user_projectuser.id])
        self.task_3.sudo(self.user_projectmanager).message_subscribe_users(user_ids=[self.user_portal.id, self.user_projectuser.id])

        # Do: Alfred reads project -> ok (follower ok followers)
        prout = pigs.sudo(self.user_projectuser)
        prout.invalidate_cache()
        prout.read(['state'])
        # Do: Chell reads project -> ok (follower ok follower)
        pigs.sudo(self.user_portal).read(['state'])
        # Do: Donovan reads project -> ko (public ko follower even if follower)
        # TODO Change the except_orm to Warning
        self.assertRaises(except_orm, pigs.sudo(self.user_public).read, ['state'])
        # Do: project user is follower of the project and can create a task
        self.env['project.task'].sudo(self.user_projectuser.id).with_context({'mail_create_nolog': True}).create({
            'name': 'Pigs task', 'project_id': pigs.id
        })
        # not follower user should not be able to create a task
        pigs.sudo(self.user_projectuser).message_unsubscribe_users(user_ids=[self.user_projectuser.id])
        self.assertRaises(except_orm, self.env['project.task'].sudo(self.user_projectuser).with_context({
            'mail_create_nolog': True}).create, {'name': 'Pigs task', 'project_id': pigs.id})

        # Do: project user can create a task without project
        self.assertRaises(except_orm, self.env['project.task'].sudo(self.user_projectuser).with_context({
            'mail_create_nolog': True}).create, {'name': 'Pigs task', 'project_id': pigs.id})
