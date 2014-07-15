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
X-Original-To: {email_to}
Delivered-To: {email_to}
To: {email_to}
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
    def test_00_project_process(self):
        """ Testing project management """
        cr, uid, user_projectuser_id, user_projectmanager_id, project_pigs_id = self.cr, self.uid, self.user_projectuser_id, self.user_projectmanager_id, self.project_pigs_id

        # ProjectUser: set project as template -> raise
        self.assertRaises(AccessError, self.project_project.set_template, cr, user_projectuser_id, [project_pigs_id])

        # Other tests are done using a ProjectManager
        project = self.project_project.browse(cr, user_projectmanager_id, project_pigs_id)
        self.assertNotEqual(project.state, 'template', 'project: incorrect state, should not be a template')

        # Set test project as template
        self.project_project.set_template(cr, user_projectmanager_id, [project_pigs_id])
        project.refresh()
        self.assertEqual(project.state, 'template', 'project: set_template: project state should be template')
        self.assertEqual(len(project.tasks), 0, 'project: set_template: project tasks should have been set inactive')

        # Duplicate template
        new_template_act = self.project_project.duplicate_template(cr, user_projectmanager_id, [project_pigs_id])
        new_project = self.project_project.browse(cr, user_projectmanager_id, new_template_act['res_id'])
        self.assertEqual(new_project.state, 'open', 'project: incorrect duplicate_template')
        self.assertEqual(len(new_project.tasks), 2, 'project: duplicating a project template should duplicate its tasks')

        # Convert into real project
        self.project_project.reset_project(cr, user_projectmanager_id, [project_pigs_id])
        project.refresh()
        self.assertEqual(project.state, 'open', 'project: resetted project should be in open state')
        self.assertEqual(len(project.tasks), 2, 'project: reset_project: project tasks should have been set active')

        # Put as pending
        self.project_project.set_pending(cr, user_projectmanager_id, [project_pigs_id])
        project.refresh()
        self.assertEqual(project.state, 'pending', 'project: should be in pending state')

        # Re-open
        self.project_project.set_open(cr, user_projectmanager_id, [project_pigs_id])
        project.refresh()
        self.assertEqual(project.state, 'open', 'project: reopened project should be in open state')

        # Close project
        self.project_project.set_done(cr, user_projectmanager_id, [project_pigs_id])
        project.refresh()
        self.assertEqual(project.state, 'close', 'project: closed project should be in close state')

        # Re-open
        self.project_project.set_open(cr, user_projectmanager_id, [project_pigs_id])
        project.refresh()

        # Re-convert into a template and schedule tasks
        self.project_project.set_template(cr, user_projectmanager_id, [project_pigs_id])
        self.project_project.schedule_tasks(cr, user_projectmanager_id, [project_pigs_id])

        # Copy the project
        new_project_id = self.project_project.copy(cr, user_projectmanager_id, project_pigs_id)
        new_project = self.project_project.browse(cr, user_projectmanager_id, new_project_id)
        self.assertEqual(len(new_project.tasks), 2, 'project: copied project should have copied task')

        # Cancel the project
        self.project_project.set_cancel(cr, user_projectmanager_id, [project_pigs_id])
        self.assertEqual(project.state, 'cancelled', 'project: cancelled project should be in cancel state')

    def test_10_task_process(self):
        """ Testing task creation and management """
        cr, uid, user_projectuser_id, user_projectmanager_id, project_pigs_id = self.cr, self.uid, self.user_projectuser_id, self.user_projectmanager_id, self.project_pigs_id

        # create new partner
        self.partner_id = self.registry('res.partner').create(cr, uid, {
            'name': 'Pigs',
            'email': 'otherid@gmail.com',
        }, {'mail_create_nolog': True})

        def format_and_process(template, email_to='project+pigs@mydomain.com, other@gmail.com', cc='otherid@gmail.com', subject='Frogs',
                               email_from='Patrick Ratatouille <patrick.ratatouille@agrolait.com>',
                               msg_id='<1198923581.41972151344608186760.JavaMail@agrolait.com>'):
            self.assertEqual(self.project_task.search(cr, uid, [('name', '=', subject)]), [])
            mail = template.format(email_to=email_to, cc=cc, subject=subject, email_from=email_from, msg_id=msg_id)
            self.mail_thread.message_process(cr, uid, None, mail)
            return self.project_task.search(cr, uid, [('name', '=', subject)])

        # Do: incoming mail from an unknown partner on an alias creates a new task 'Frogs'
        frogs = format_and_process(EMAIL_TPL)

        # Test: one task created by mailgateway administrator
        self.assertEqual(len(frogs), 1, 'project: message_process: a new project.task should have been created')
        task = self.project_task.browse(cr, user_projectuser_id, frogs[0])
        
        # Test: check partner in message followers
        self.assertTrue((self.partner_id in [follower.id for follower in task.message_follower_ids]),"Partner in message cc is not added as a task followers.")
        
        res = self.project_task.get_metadata(cr, uid, [task.id])[0].get('create_uid') or [None]
        self.assertEqual(res[0], uid,
                         'project: message_process: task should have been created by uid as alias_user_id is False on the alias')
        # Test: messages
        self.assertEqual(len(task.message_ids), 3,
                         'project: message_process: newly created task should have 2 messages: creation and email')
        self.assertEqual(task.message_ids[2].subtype_id.name, 'Task Created',
                         'project: message_process: first message of new task should have Task Created subtype')
        self.assertEqual(task.message_ids[1].subtype_id.name, 'Task Assigned',
                         'project: message_process: first message of new task should have Task Created subtype')
        self.assertEqual(task.message_ids[0].author_id.id, self.email_partner_id,
                         'project: message_process: second message should be the one from Agrolait (partner failed)')
        self.assertEqual(task.message_ids[0].subject, 'Frogs',
                         'project: message_process: second message should be the one from Agrolait (subject failed)')
        # Test: task content
        self.assertEqual(task.name, 'Frogs', 'project_task: name should be the email subject')
        self.assertEqual(task.project_id.id, self.project_pigs_id, 'project_task: incorrect project')
        self.assertEqual(task.stage_id.sequence, 1, 'project_task: should have a stage with sequence=1')

        # Open the delegation wizard
        delegate_id = self.project_task_delegate.create(cr, user_projectuser_id, {
            'user_id': user_projectuser_id,
            'planned_hours': 12.0,
            'planned_hours_me': 2.0,
        }, {'active_id': task.id})
        self.project_task_delegate.delegate(cr, user_projectuser_id, [delegate_id], {'active_id': task.id})

        # Check delegation details
        task.refresh()
        self.assertEqual(task.planned_hours, 2, 'project_task_delegate: planned hours is not correct after delegation')
