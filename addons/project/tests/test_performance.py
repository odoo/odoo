# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from email.utils import formataddr

from odoo.tests.common import TransactionCase, users, warmup
from odoo.tests import tagged
from odoo.tools import mute_logger


@tagged('performance')
class TestProjectPerformance(TransactionCase):

    def setUp(self):
        super(TestProjectPerformance, self).setUp()

        # Test users to use through the various tests
        Users = self.env['res.users'].with_context({'no_reset_password': True})
        self.user_projectuser = Users.create({
            'name': 'ProjectUser',
            'login': 'project_user',
            'email': 'projectuser@example.com',
            'notification_type': 'email',
            'groups_id': [(4, self.env.ref('project.group_project_user').id)]
        })
        self.user_projectmanager = Users.create({
            'name': 'ProjectMnager',
            'login': 'project_manager',
            'email': 'projectmanager@example.com',
            'notification_type': 'email',
            'groups_id': [(4, self.env.ref('project.group_project_user').id)]
        })

        self.customer = self.env['res.partner'].create({
            'name': 'Valid Lelitre',
            'email': 'valid.lelitre@agrolait.com',
        })

        self.project = self.env['project.project'].with_context({'mail_create_nolog': True}).create({
            'name': 'TestProject',
            'privacy_visibility': 'employees',
            'alias_name': 'project+test',
            'type_ids': [
                (0, 0, {
                    'name': 'New',
                    'sequence': 1,
                }),
                (0, 0, {
                    'name': 'Won',
                    'sequence': 10,
                })]
        })

        # patch registry to simulate a ready environment
        self.patch(self.env.registry, 'ready', True)

    @users('__system__', 'project_user')
    @warmup
    def test_create_task(self):
        project_id = self.project.id

        with self.assertQueryCount(__system__=26, project_user=57):
            self.env['project.task'].create({
                'project_id': project_id,
                'name': 'Test task',
            })

    @users('__system__', 'project_user')
    @warmup
    def test_create_task_followers(self):
        self.project.message_subscribe(
            partner_ids=[self.user_projectmanager.id],
            subtype_ids=[self.env.ref('mail.mt_comment').id, self.env.ref('project.mt_project_task_new').id, self.env.ref('project.mt_project_task_ready').id])
        project_id = self.project.id

        with self.assertQueryCount(__system__=80, project_user=141):
            self.env['project.task'].create({
                'project_id': project_id,
                'name': 'Test task',
            })

    @users('__system__', 'project_user')
    @warmup
    def test_create_task_followers_assignation(self):
        self.project.message_subscribe(
            partner_ids=[self.user_projectmanager.id],
            subtype_ids=[self.env.ref('mail.mt_comment').id, self.env.ref('project.mt_project_task_new').id, self.env.ref('project.mt_project_task_ready').id])
        user_id = self.user_projectmanager.id
        project_id = self.project.id

        with self.assertQueryCount(__system__=300, project_user=300):
            self.env['project.task'].create({
                'project_id': project_id,
                'name': 'Test task',
                'user_id': user_id,
            })
