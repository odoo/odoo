# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from .test_project_base import TestProjectBase
from odoo.tools import mute_logger
from odoo.modules.module import get_resource_path


EMAIL_TPL = """Return-Path: <whatever-2a840@postmaster.twitter.com>
X-Original-To: {to}
Delivered-To: {to}
To: {to}
cc: {cc}
Received: by mail1.odoo.com (Postfix, from userid 10002)
    id 5DF9ABFB2A; Fri, 10 Aug 2012 16:16:39 +0200 (CEST)
Message-ID: {msg_id}
Date: Tue, 29 Nov 2011 12:43:21 +0530
From: {email_from}
MIME-Version: 1.0
Subject: {subject}
Content-Type: text/plain; charset=ISO-8859-1; format=flowed

Hello,

This email should create a new entry in your module. Please check that it
effectively works.

Thanks,

--
Raoul Boitempoils
Integrator at Agrolait"""


class TestProjectFlow(TestProjectBase):

    def test_project_process_project_manager_duplicate(self):
        pigs = self.project_pigs.with_user(self.user_projectmanager)
        dogs = pigs.copy()
        self.assertEqual(len(dogs.tasks), 2, 'project: duplicating a project must duplicate its tasks')

    @mute_logger('odoo.addons.mail.mail_thread')
    def test_task_process_without_stage(self):
        # Do: incoming mail from an unknown partner on an alias creates a new task 'Frogs'
        task = self.format_and_process(
            EMAIL_TPL, to='project+pigs@mydomain.com, valid.lelitre@agrolait.com', cc='valid.other@gmail.com',
            email_from='%s' % self.user_projectuser.email,
            subject='Frogs', msg_id='<1198923581.41972151344608186760.JavaMail@agrolait.com>',
            target_model='project.task')

        # Test: one task created by mailgateway administrator
        self.assertEqual(len(task), 1, 'project: message_process: a new project.task should have been created')
        # Test: check partner in message followers
        self.assertIn(self.partner_2, task.message_partner_ids, "Partner in message cc is not added as a task followers.")
        # Test: messages
        self.assertEqual(len(task.message_ids), 1,
                         'project: message_process: newly created task should have 1 message: email')
        self.assertEqual(task.message_ids[0].subtype_id, self.env.ref('project.mt_task_new'),
                         'project: message_process: first message of new task should have Task Created subtype')
        self.assertEqual(task.message_ids[0].author_id, self.user_projectuser.partner_id,
                         'project: message_process: second message should be the one from Agrolait (partner failed)')
        self.assertEqual(task.message_ids[0].subject, 'Frogs',
                         'project: message_process: second message should be the one from Agrolait (subject failed)')
        # Test: task content
        self.assertEqual(task.name, 'Frogs', 'project_task: name should be the email subject')
        self.assertEqual(task.project_id.id, self.project_pigs.id, 'project_task: incorrect project')
        self.assertEqual(task.stage_id.sequence, False, "project_task: shouldn't have a stage, i.e. sequence=False")

    @mute_logger('odoo.addons.mail.mail_thread')
    def test_task_process_with_stages(self):
        # Do: incoming mail from an unknown partner on an alias creates a new task 'Cats'
        task = self.format_and_process(
            EMAIL_TPL, to='project+goats@mydomain.com, valid.lelitre@agrolait.com', cc='valid.other@gmail.com',
            email_from='%s' % self.user_projectuser.email,
            subject='Cats', msg_id='<1198923581.41972151344608186760.JavaMail@agrolait.com>',
            target_model='project.task')

        # Test: one task created by mailgateway administrator
        self.assertEqual(len(task), 1, 'project: message_process: a new project.task should have been created')
        # Test: check partner in message followers
        self.assertIn(self.partner_2, task.message_partner_ids, "Partner in message cc is not added as a task followers.")
        # Test: messages
        self.assertEqual(len(task.message_ids), 1,
                         'project: message_process: newly created task should have 1 messages: email')
        self.assertEqual(task.message_ids[0].subtype_id, self.env.ref('project.mt_task_new'),
                         'project: message_process: first message of new task should have Task Created subtype')
        self.assertEqual(task.message_ids[0].author_id, self.user_projectuser.partner_id,
                         'project: message_process: first message should be the one from Agrolait (partner failed)')
        self.assertEqual(task.message_ids[0].subject, 'Cats',
                         'project: message_process: first message should be the one from Agrolait (subject failed)')
        # Test: task content
        self.assertEqual(task.name, 'Cats', 'project_task: name should be the email subject')
        self.assertEqual(task.project_id.id, self.project_goats.id, 'project_task: incorrect project')
        self.assertEqual(task.stage_id.sequence, 1, "project_task: should have a stage with sequence=1")

    def test_subtask_process(self):
        """ Check subtask mecanism and change it from project. """
        Task = self.env['project.task'].with_context({'tracking_disable': True})
        parent_task = Task.create({
            'name': 'Mother Task',
            'user_id': self.user_projectuser.id,
            'project_id': self.project_pigs.id,
            'partner_id': self.partner_2.id,
            'planned_hours': 12,
        })
        child_task = Task.create({
            'name': 'Task Child',
            'parent_id': parent_task.id,
            'project_id': self.project_pigs.id,
            'planned_hours': 3,
        })

        self.assertEqual(parent_task.partner_id, child_task.partner_id, "Subtask should have the same partner than its parent")
        self.assertEqual(parent_task.subtask_count, 1, "Parent task should have 1 child")
        self.assertEqual(parent_task.subtask_planned_hours, 3, "Planned hours of subtask should impact parent task")

        # change project
        child_task.write({
            'project_id': self.project_goats.id  # customer is partner_1
        })

        self.assertEqual(parent_task.partner_id, child_task.partner_id, "Subtask partner should not change when changing project")

    def test_rating(self):
        """Check if rating works correctly even when task is changed from project A to project B"""
        Task = self.env['project.task'].with_context({'tracking_disable': True})
        first_task = Task.create({
            'name': 'first task',
            'user_id': self.user_projectuser.id,
            'project_id': self.project_pigs.id,
            'partner_id': self.partner_2.id,
        })

        self.assertEqual(first_task.rating_count, 0, "Task should have no rating associated with it")

        Rating = self.env['rating.rating']
        rating_good = Rating.create({
            'res_model_id': self.env['ir.model']._get('project.task').id,
            'res_id': first_task.id,
            'parent_res_model_id': self.env['ir.model']._get('project.project').id,
            'parent_res_id': self.project_pigs.id,
            'rated_partner_id': self.partner_2.id,
            'partner_id': self.partner_2.id,
            'rating': 10,
            'consumed': False,
        })

        rating_bad = Rating.create({
            'res_model_id': self.env['ir.model']._get('project.task').id,
            'res_id': first_task.id,
            'parent_res_model_id': self.env['ir.model']._get('project.project').id,
            'parent_res_id': self.project_pigs.id,
            'rated_partner_id': self.partner_2.id,
            'partner_id': self.partner_2.id,
            'rating': 5,
            'consumed': True,
        })

        # We need to invalidate cache since it is not done automatically by the ORM
        # Our One2Many is linked to a res_id (int) for which the orm doesn't create an inverse
        first_task.invalidate_cache()

        self.assertEqual(rating_good.rating_text, 'satisfied')
        self.assertEqual(rating_bad.rating_text, 'not_satisfied')
        self.assertEqual(first_task.rating_count, 1, "Task should have only one rating associated, since one is not consumed")
        self.assertEqual(rating_good.parent_res_id, self.project_pigs.id)

        self.assertEqual(self.project_goats.rating_percentage_satisfaction, -1)
        self.assertEqual(self.project_pigs.rating_percentage_satisfaction, 0)  # There is a rating but not a "great" on, just an "okay".

        # Consuming rating_good
        first_task.rating_apply(10, rating_good.access_token)

        # We need to invalidate cache since it is not done automatically by the ORM
        # Our One2Many is linked to a res_id (int) for which the orm doesn't create an inverse
        first_task.invalidate_cache()

        self.assertEqual(first_task.rating_count, 2, "Task should have two ratings associated with it")
        self.assertEqual(rating_good.parent_res_id, self.project_pigs.id)
        self.assertEqual(self.project_goats.rating_percentage_satisfaction, -1)
        self.assertEqual(self.project_pigs.rating_percentage_satisfaction, 50)

        # We change the task from project_pigs to project_goats, ratings should be associated with the new project
        first_task.project_id = self.project_goats.id

        # We need to invalidate cache since it is not done automatically by the ORM
        # Our One2Many is linked to a res_id (int) for which the orm doesn't create an inverse
        first_task.invalidate_cache()

        self.assertEqual(rating_good.parent_res_id, self.project_goats.id)
        self.assertEqual(self.project_goats.rating_percentage_satisfaction, 50)
        self.assertEqual(self.project_pigs.rating_percentage_satisfaction, -1)
