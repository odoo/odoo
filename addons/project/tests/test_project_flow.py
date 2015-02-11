# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (c) 2013-TODAY OpenERP S.A. <http://www.openerp.com>
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
from openerp.tools import mute_logger


EMAIL_TPL = """Return-Path: <whatever-2a840@postmaster.twitter.com>
X-Original-To: {to}
Delivered-To: {to}
To: {to}
cc: {cc}
Received: by mail1.openerp.com (Postfix, from userid 10002)
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

    @mute_logger('openerp.addons.base.ir.ir_model', 'openerp.models')
    def test_project_process_project_user(self):
        self.assertRaises(AccessError, self.project_pigs.sudo(self.user_projectuser).set_template)

    def test_project_process_project_manager_set_template(self):
        pigs = self.project_pigs.sudo(self.user_projectmanager)
        pigs.set_template()
        self.assertEqual(pigs.state, 'template')
        self.assertEqual(len(pigs.tasks), 0, 'project: set_template: project tasks should have been set inactive')

        # pigs.reset_project()
        # self.assertEqual(pigs.state, 'open')
        # self.assertEqual(len(pigs.tasks), 2, 'project: reset_project: project tasks should have been set active')

    def test_project_process_project_manager_duplicate(self):
        pigs = self.project_pigs.sudo(self.user_projectmanager)
        new_template_act = pigs.duplicate_template()
        new_project = self.env['project.project'].sudo(self.user_projectmanager).browse(new_template_act['res_id'])
        self.assertEqual(new_project.state, 'open')
        self.assertEqual(len(new_project.tasks), 2, 'project: duplicating a project template should duplicate its tasks')

    def test_project_process_project_manager_state(self):
        pigs = self.project_pigs.sudo(self.user_projectmanager)
        pigs.state = 'pending'
        self.assertEqual(pigs.state, 'pending')
        # Re-open
        pigs.state = 'open'
        self.assertEqual(pigs.state, 'open')
        # Close project
        pigs.state = 'close'
        self.assertEqual(pigs.state, 'close')
        # Re-open
        pigs.state = 'open'
        # Re-convert into a template and schedule tasks
        pigs.set_template()
        pigs.schedule_tasks()
        # Copy the project
        new_project = pigs.copy()
        self.assertEqual(len(new_project.tasks), 2, 'project: copied project should have copied task')
        # Cancel the project
        pigs.state = 'cancelled'
        self.assertEqual(pigs.state, 'cancelled', 'project: cancelled project should be in cancel state')

    @mute_logger('openerp.addons.mail.mail_thread')
    def test_task_process(self):
        # Do: incoming mail from an unknown partner on an alias creates a new task 'Frogs'
        task = self.format_and_process(
            EMAIL_TPL, to='project+pigs@mydomain.com, valid.lelitre@agrolait.com', cc='valid.other@gmail.com',
            email_from='%s' % self.user_projectuser.email,
            subject='Frogs', msg_id='<1198923581.41972151344608186760.JavaMail@agrolait.com>',
            target_model='project.task')

        # Test: one task created by mailgateway administrator
        self.assertEqual(len(task), 1, 'project: message_process: a new project.task should have been created')
        # Test: check partner in message followers
        self.assertIn(self.partner_2, task.message_follower_ids, "Partner in message cc is not added as a task followers.")
        # Test: messages
        self.assertEqual(len(task.message_ids), 2,
                         'project: message_process: newly created task should have 2 messages: creation and email')
        self.assertEqual(task.message_ids[1].subtype_id.name, 'Task Opened',
                         'project: message_process: first message of new task should have Task Created subtype')
        self.assertEqual(task.message_ids[0].author_id, self.user_projectuser.partner_id,
                         'project: message_process: second message should be the one from Agrolait (partner failed)')
        self.assertEqual(task.message_ids[0].subject, 'Frogs',
                         'project: message_process: second message should be the one from Agrolait (subject failed)')
        # Test: task content
        self.assertEqual(task.name, 'Frogs', 'project_task: name should be the email subject')
        self.assertEqual(task.project_id.id, self.project_pigs.id, 'project_task: incorrect project')
        self.assertEqual(task.stage_id.sequence, 1, 'project_task: should have a stage with sequence=1')
        # Open the delegation wizard
        self.env['project.task.delegate'].with_context({
            'active_id': task.id}).sudo(self.user_projectuser).create({
                'user_id': self.user_projectuser.id,
                'planned_hours': 12.0,
                'planned_hours_me': 2.0,
            }).with_context({'active_id': task.id}).delegate()
        # Check delegation details
        self.assertEqual(task.planned_hours, 2, 'project_task_delegate: planned hours is not correct after delegation')
