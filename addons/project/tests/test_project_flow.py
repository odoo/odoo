# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup

from .test_project_base import TestProjectCommon
from odoo import Command
from odoo.tools import mute_logger
from odoo.addons.mail.tests.common import MailCommon
from odoo.exceptions import AccessError


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


class TestProjectFlow(TestProjectCommon, MailCommon):

    def test_project_process_project_manager_duplicate(self):
        pigs = self.project_pigs.with_user(self.user_projectmanager)
        dogs = pigs.copy()
        self.assertEqual(len(dogs.tasks), 2, 'project: duplicating a project must duplicate its tasks')

    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_task_process_without_stage(self):
        # Do: incoming mail from an unknown partner on an alias creates a new task 'Frogs'
        task = self.format_and_process(
            EMAIL_TPL, to=f'project+pigs@{self.alias_domain}, valid.lelitre@agrolait.com', cc='valid.other@gmail.com',
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
        self.assertEqual(task.message_ids.subtype_id, self.env.ref('project.mt_task_new'),
                         'project: message_process: first message of new task should have Task Created subtype')
        self.assertEqual(task.message_ids.author_id, self.user_projectuser.partner_id,
                         'project: message_process: second message should be the one from Agrolait (partner failed)')
        self.assertEqual(task.message_ids.subject, 'Frogs',
                         'project: message_process: second message should be the one from Agrolait (subject failed)')
        # Test: task content
        self.assertEqual(task.name, 'Frogs', 'project_task: name should be the email subject')
        self.assertEqual(task.project_id, self.project_pigs, 'project_task: incorrect project')
        self.assertEqual(task.stage_id.sequence, False, "project_task: shouldn't have a stage, i.e. sequence=False")

    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_task_process_with_stages(self):
        # Do: incoming mail from an unknown partner on an alias creates a new task 'Cats'
        task = self.format_and_process(
            EMAIL_TPL, to=f'project+goats@{self.alias_domain}, valid.lelitre@agrolait.com', cc='valid.other@gmail.com',
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
        self.assertEqual(task.message_ids.subtype_id, self.env.ref('project.mt_task_new'),
                         'project: message_process: first message of new task should have Task Created subtype')
        self.assertEqual(task.message_ids.author_id, self.user_projectuser.partner_id,
                         'project: message_process: first message should be the one from Agrolait (partner failed)')
        self.assertEqual(task.message_ids.subject, 'Cats',
                         'project: message_process: first message should be the one from Agrolait (subject failed)')
        # Test: task content
        self.assertEqual(task.name, 'Cats', 'project_task: name should be the email subject')
        self.assertEqual(task.project_id, self.project_goats, 'project_task: incorrect project')
        self.assertEqual(task.stage_id.sequence, 1, "project_task: should have a stage with sequence=1")

    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_task_from_email_alias(self):
        # Do: incoming mail from a known partner email on an alias creates a new task 'Super Frog'
        task = self.format_and_process(
            EMAIL_TPL, to=f'project+goats@{self.alias_domain}, valid.lelitre@agrolait.com', cc='valid.other@gmail.com',
            email_from='%s' % self.user_portal.email,
            subject='Super Frog', msg_id='<1198923581.41972151344608186760.JavaMail@agrolait.com>',
            target_model='project.task')

        # Test: one task created by mailgateway administrator
        self.assertEqual(len(task), 1, 'project: message_process: a new project.task should have been created')
        # Test: check partner in message followers
        self.assertIn(self.partner_2, task.message_partner_ids, "Partner in message cc is not added as a task followers.")
        # Test: check partner has not been assgined
        self.assertFalse(task.user_ids, "Partner is not added as an assignees")
        # Test: messages
        self.assertEqual(len(task.message_ids), 1,
                         'project: message_process: newly created task should have 1 messages: email')
        self.assertEqual(task.message_ids.subtype_id, self.env.ref('project.mt_task_new'),
                         'project: message_process: first message of new task should have Task Created subtype')
        self.assertEqual(task.message_ids.author_id, self.user_portal.partner_id,
                         'project: message_process: first message should be the one from Agrolait (partner failed)')
        self.assertEqual(task.message_ids.subject, 'Super Frog',
                         'project: message_process: first message should be the one from Agrolait (subject failed)')
        # Test: task content
        self.assertEqual(task.name, 'Super Frog', 'project_task: name should be the email subject')
        self.assertEqual(task.project_id, self.project_goats, 'project_task: incorrect project')
        self.assertEqual(task.stage_id.sequence, 1, "project_task: should have a stage with sequence=1")
        self.assertEqual(
            task.description,
            Markup(
                '<pre>Hello,\n\nThis email should create a new entry in your module. Please check that it\neffectively works.\n\nThanks,\n<span data-o-mail-quote="1">\n--\nRaoul Boitempoils\nIntegrator at Agrolait</span></pre>\n'
            ),
            'The task description should be the email content.',
        )

    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_auto_create_partner(self):
        email = 'unknown@test.com'
        new_partner = self.env['res.partner'].search([('email', '=', email)])
        self.assertFalse(new_partner)

        task = self.format_and_process(
            EMAIL_TPL, to=f'project+pigs@{self.alias_domain}, valid.lelitre@agrolait.com',
                cc='valid.other@gmail.com',
                email_from=email,
                subject='subject',
                msg_id='<1198923581.41972151344608186760.JavaMail@agrolait.com>',
                target_model='project.task'
            )

        self.assertEqual(len(task), 1)
        new_partner = self.env['res.partner'].search([('email', '=', email)])
        self.assertTrue(new_partner)
        self.assertEqual(task.partner_id, new_partner)
        self.assertEqual(task.message_ids.author_id, new_partner)

    def test_subtask_process(self):
        """
        Check subtask mecanism and change it from project.

        For this test, 2 projects are used:
            - the 'pigs' project which has a partner_id
            - the 'goats' project where the partner_id is removed at the beginning of the tests and then restored.

        2 parent tasks are also used to be able to switch the parent task of a sub-task:
            - 'parent_task' linked to the partner_2
            - 'another_parent_task' linked to the partner_3
        """

        Task = self.env['project.task'].with_context({'tracking_disable': True})

        parent_task = Task.create({
            'name': 'Mother Task',
            'user_ids': self.user_projectuser,
            'project_id': self.project_pigs.id,
            'partner_id': self.partner_2.id,
            'allocated_hours': 12,
        })

        another_parent_task = Task.create({
            'name': 'Another Mother Task',
            'user_ids': self.user_projectuser,
            'project_id': self.project_pigs.id,
            'partner_id': self.partner_3.id,
            'allocated_hours': 0,
        })

        # remove the partner_id of the 'goats' project
        goats_partner_id = self.project_goats.partner_id

        self.project_goats.write({
            'partner_id': False
        })

        # the child task 1 is linked to a project without partner_id (goats project)
        child_task_1 = Task.with_context(default_project_id=self.project_goats.id, default_parent_id=parent_task.id).create({
            'name': 'Task Child with project',
            'allocated_hours': 3,
        })

        # the child task 2 is linked to a project with a partner_id (pigs project)
        child_task_2 = Task.create({
            'name': 'Task Child without project',
            'parent_id': parent_task.id,
            'project_id': self.project_pigs.id,
            'allocated_hours': 5,
        })

        self.assertEqual(
            child_task_1.partner_id, child_task_1.parent_id.partner_id,
            "When no project partner_id has been set, a subtask should have the same partner as its parent")

        self.assertEqual(
            child_task_2.partner_id, child_task_2.parent_id.partner_id,
            "When a project partner_id has been set, a subtask should have the same partner as its parent")

        self.assertEqual(
            parent_task.subtask_count, 2,
            "Parent task should have 2 children")

        self.assertEqual(
            parent_task.subtask_allocated_hours, 8,
            "Planned hours of subtask should impact parent task")

        # change the parent of a subtask without a project partner_id
        child_task_1.write({
            'parent_id': another_parent_task.id
        })

        self.assertEqual(
            child_task_1.partner_id, parent_task.partner_id,
            "When changing the parent task of a subtask with no project partner_id, the partner_id should remain the same.")

        # change the parent of a subtask with a project partner_id
        child_task_2.write({
            'parent_id': another_parent_task.id
        })

        self.assertEqual(
            child_task_2.partner_id, parent_task.partner_id,
            "When changing the parent task of a subtask with a project, the partner_id should remain the same.")

        # set a project with partner_id to a subtask without project partner_id
        child_task_1.write({
            'project_id': self.project_pigs.id
        })

        self.assertNotEqual(
            child_task_1.partner_id, self.project_pigs.partner_id,
            "When the project changes, the subtask should keep its partner id as its partner id is set.")

        # restore the partner_id of the 'goats' project
        self.project_goats.write({
            'partner_id': goats_partner_id
        })

        # set a project with partner_id to a subtask with a project partner_id
        child_task_2.write({
            'project_id': self.project_goats.id
        })

        self.assertEqual(
            child_task_2.partner_id, parent_task.partner_id,
            "When the project changes, the subtask should keep the same partner id even it has a new project.")

    def test_rating(self):
        """Check if rating works correctly even when task is changed from project A to project B"""
        Task = self.env['project.task'].with_context({'tracking_disable': True})
        first_task = Task.create({
            'name': 'first task',
            'user_ids': self.user_projectuser,
            'project_id': self.project_pigs.id,
            'partner_id': self.partner_2.id,
        })

        self.assertEqual(first_task.rating_count, 0, "Task should have no rating associated with it")

        rating_good = self.env['rating.rating'].create({
            'res_model_id': self.env['ir.model']._get('project.task').id,
            'res_id': first_task.id,
            'parent_res_model_id': self.env['ir.model']._get('project.project').id,
            'parent_res_id': self.project_pigs.id,
            'rated_partner_id': self.partner_2.id,
            'partner_id': self.partner_2.id,
            'rating': 5,
            'consumed': False,
        })

        rating_bad = self.env['rating.rating'].create({
            'res_model_id': self.env['ir.model']._get('project.task').id,
            'res_id': first_task.id,
            'parent_res_model_id': self.env['ir.model']._get('project.project').id,
            'parent_res_id': self.project_pigs.id,
            'rated_partner_id': self.partner_2.id,
            'partner_id': self.partner_2.id,
            'rating': 3,
            'consumed': True,
        })

        # We need to invalidate cache since it is not done automatically by the ORM
        # Our One2Many is linked to a res_id (int) for which the orm doesn't create an inverse
        self.env.invalidate_all()

        self.assertEqual(rating_good.rating_text, 'top')
        self.assertEqual(rating_bad.rating_text, 'ok')
        self.assertEqual(first_task.rating_count, 1, "Task should have only one rating associated, since one is not consumed")
        self.assertEqual(rating_good.parent_res_id, self.project_pigs.id)

        self.assertEqual(self.project_goats.rating_percentage_satisfaction, -1)
        self.assertEqual(self.project_goats.rating_avg, 0, 'Since there is no rating in this project, the Average Rating should be equal to 0.')
        self.assertEqual(self.project_pigs.rating_percentage_satisfaction, 0)  # There is a rating but not a "great" on, just an "okay".
        self.assertEqual(self.project_pigs.rating_avg, rating_bad.rating, 'Since there is only one rating the Average Rating should be equal to the rating value of this one.')

        # Consuming rating_good
        first_task.rating_apply(5, rating_good.access_token)

        # We need to invalidate cache since it is not done automatically by the ORM
        # Our One2Many is linked to a res_id (int) for which the orm doesn't create an inverse
        self.env.invalidate_all()

        rating_avg = (rating_good.rating + rating_bad.rating) / 2
        self.assertEqual(first_task.rating_count, 2, "Task should have two ratings associated with it")
        self.assertEqual(first_task.rating_avg_text, 'top')
        self.assertEqual(rating_good.parent_res_id, self.project_pigs.id)
        self.assertEqual(self.project_goats.rating_percentage_satisfaction, -1)
        self.assertEqual(self.project_pigs.rating_percentage_satisfaction, 50)
        self.assertEqual(self.project_pigs.rating_avg, rating_avg)
        self.assertEqual(self.project_pigs.rating_avg_percentage, rating_avg / 5)

        # We change the task from project_pigs to project_goats, ratings should be associated with the new project
        first_task.project_id = self.project_goats.id

        # We need to invalidate cache since it is not done automatically by the ORM
        # Our One2Many is linked to a res_id (int) for which the orm doesn't create an inverse
        self.env.invalidate_all()

        self.assertEqual(rating_good.parent_res_id, self.project_goats.id)
        self.assertEqual(self.project_goats.rating_percentage_satisfaction, 50)
        self.assertEqual(self.project_goats.rating_avg, rating_avg)
        self.assertEqual(self.project_pigs.rating_percentage_satisfaction, -1)
        self.assertEqual(self.project_pigs.rating_avg, 0)

    def test_task_with_no_project(self):
        """
            With this test, we want to make sure the fact that a task has no project doesn't affect the entire
            behaviours of projects.

            1) Try to compute every field of a task which has no project.
            2) Try to compute every field of a project and assert it isn't affected by this use case.
        """
        task_without_project = self.env['project.task'].with_context({'mail_create_nolog': True}).create({
            'name': 'Test task without project'
        })

        for field in task_without_project._fields.keys():
            try:
                task_without_project[field]
            except Exception as e:
                raise AssertionError("Error raised unexpectedly while computing a field of the task ! Exception : " + e.args[0])

        for field in self.project_pigs._fields.keys():
            try:
                self.project_pigs[field]
            except Exception as e:
                raise AssertionError("Error raised unexpectedly while computing a field of the project ! Exception : " + e.args[0])

        # tasks with no project set should only be visible to the users assigned to them
        task_without_project.user_ids = [Command.link(self.user_projectuser.id)]
        task_without_project.with_user(self.user_projectuser).read(['name'])
        with self.assertRaises(AccessError):
            task_without_project.with_user(self.user_projectmanager).read(['name'])

        # Tests that tasks assigned to the current user should be in the right default stage
        task = self.env['project.task'].create({
            'name': 'Test Task!',
            'user_ids': [Command.link(self.env.user.id)],
        })
        stages = task._get_default_personal_stage_create_vals(self.env.user.id)
        self.assertEqual(task.personal_stage_id.stage_id.name, stages[0].get('name'), "tasks assigned to the current user should be in the right default stage")

    def test_send_rating_review(self):
        project_settings = self.env["res.config.settings"].create({'group_project_rating': True})
        project_settings.execute()
        self.assertTrue(self.project_goats.rating_active, 'The customer ratings should be enabled in this project.')

        won_stage = self.project_goats.type_ids[-1]
        rating_request_mail_template = self.env.ref('project.rating_project_request_email_template')
        won_stage.write({'rating_template_id': rating_request_mail_template.id})
        tasks = self.env['project.task'].with_context(mail_create_nolog=True, default_project_id=self.project_goats.id).create([
            {'name': 'Goat Task 1', 'user_ids': [Command.set([])]},
            {'name': 'Goat Task 2', 'user_ids': [Command.link(self.user_projectuser.id)]},
            {
                'name': 'Goat Task 3',
                'user_ids': [
                    Command.link(self.user_projectmanager.id),
                    Command.link(self.user_projectuser.id),
                ],
            },
        ])

        with self.mock_mail_gateway():
            tasks.with_user(self.user_projectmanager).write({'stage_id': won_stage.id})

        tasks.invalidate_model(['rating_ids'])
        for task in tasks:
            self.assertEqual(len(task.rating_ids), 1, 'This task should have a generated rating when it arrives in the Won stage.')
            rating_request_message = task.message_ids[:1]
            if not task.user_ids or len(task.user_ids) > 1:
                self.assertFalse(task.rating_ids.rated_partner_id, 'This rating should have no assigned user if the task related have no assignees or more than one assignee.')
                self.assertEqual(rating_request_message.email_from, self.user_projectmanager.partner_id.email_formatted, 'The message should have the email of the Project Manager as email from.')
            else:
                self.assertEqual(task.rating_ids.rated_partner_id, task.user_ids.partner_id, 'The rating should have an assigned user if the task has only one assignee.')
                self.assertEqual(rating_request_message.email_from, task.user_ids.partner_id.email_formatted, 'The message should have the email of the assigned user in the task as email from.')
            self.assertTrue(self.partner_1 in rating_request_message.partner_ids, 'The customer of the task should be in the partner_ids of the rating request message.')

    def test_email_track_template(self):
        """ Update some tracked fields linked to some template -> message with onchange """
        project_settings = self.env["res.config.settings"].create({'group_project_stages': True})
        project_settings.execute()

        mail_template = self.env['mail.template'].create({
            'name': 'Test template',
            'subject': 'Test',
            'body_html': '<p>Test</p>',
            'auto_delete': True,
            'model_id': self.env.ref('project.model_project_project_stage').id,
        })
        project_A = self.env['project.project'].create({
            'name': 'project_A',
            'privacy_visibility': 'followers',
            'alias_name': 'project A',
            'partner_id': self.partner_1.id,
        })
        init_stage = project_A.stage_id.name

        project_stage = self.env.ref('project.project_project_stage_1')
        self.assertNotEqual(project_A.stage_id, project_stage)

        # Assign email template
        project_stage.mail_template_id = mail_template.id
        self.flush_tracking()
        init_nb_log = len(project_A.message_ids)
        project_A.stage_id = project_stage.id
        self.flush_tracking()
        self.assertNotEqual(init_stage, project_A.stage_id.name)

        self.assertEqual(len(project_A.message_ids), init_nb_log + 2,
            "should have 2 new messages: one for tracking, one for template")

    def test_project_notify_get_recipients_groups(self):
        projects = self.env['project.project'].create([
            {
                'name': 'public project',
                'privacy_visibility': 'portal',
                'partner_id': self.partner_1.id,
            },
            {
                'name': 'internal project',
                'privacy_visibility': 'employees',
                'partner_id': self.partner_1.id,
            },
            {
                'name': 'private project',
                'privacy_visibility': 'followers',
                'partner_id': self.partner_1.id,
            },
        ])
        for project in projects:
            groups = project._notify_get_recipients_groups(self.env['mail.message'], False)
            groups_per_key = {g[0]: g for g in groups}
            for key, group in groups_per_key.items():
                has_button_access = group[2]['has_button_access']
                if key in ['portal', 'portal_customer']:
                    self.assertEqual(
                        has_button_access,
                        project.name == 'public project',
                        "Only the public project should have its name clickable in the email sent to the customer when an email is sent via a email template set in the project stage for instance."
                    )
                elif key == 'user':
                    self.assertTrue(has_button_access)

    def test_private_task_search_tag(self):
        task = self.env['project.task'].create({
            'name': 'Test Private Task',
        })
        # Tag name_search should not raise Error if project_id is False
        task.tag_ids.with_context(project_id=task.project_id.id).name_search(
            args=["!", ["id", "in", []]])

    def test_task_mail_assignement(self):
        """ This test will check that an assignement mail is sent when adding an assignee to a task """
        with self.mock_mail_gateway():
            self.env['project.task'].create({
                'name': 'Mail Task',
                'user_ids': self.user_projectmanager,
                'project_id': self.project_pigs.id
            })
        self.assertSentEmail(self.env.user.email_formatted, [self.user_projectmanager.email_formatted])

    def test_task_copy_no_mail_assignement(self):
        """ This test will check that no assignement mail is sent to assignees of a duplicated task """
        with self.mock_mail_gateway():
            self.task_1.copy() # if the feature that prevents assignement mails from being sent when copying a task is broken, this will create a mail
        self.assertNotSentEmail(self.user_projectuser.email_formatted) # check that no mail was received for the assignee of the task

    def test_copy_project_with_default_name(self):
        """ Test the new project after the duplication got the exepected name

            Test Cases:
            ==========
            1. Duplicate a project
            2. Check the new project got the name of the project to copy plus `(copy)`
            3. Duplicate a project with default name
            4. Check the new project got the name defined in the default
        """
        project = self.project_pigs.copy()
        self.assertEqual(project.name, 'Pigs (copy)', "The name of the copied project should be 'Pigs (copy)'")

        project = self.project_pigs.copy({'name': 'Pigs 2'})
        self.assertEqual(project.name, 'Pigs 2', "The name of the copied project should be 'Pigs 2'")

    def test_description_field_history_on_update(self):
        """Test updating 'description' field in project task and checking history content at revision id."""

        task = self.env['project.task'].create({
            'name': 'Test Task',
            'description': 'Hello',
        })
        task.description = False
        self.assertEqual(task.html_field_history_get_content_at_revision('description', 1), '<p>Hello</p>', "should recover previous text for description")

    def test_copy_project_with_embedded_actions(self):
        project_pigs_milestone_action = self.env['ir.actions.act_window'].create({
            'name': 'Milestones',
            'res_model': 'project.milestone',
            'view_mode': 'kanban,list,form',
            'domain': f"[('project_id', '=', {self.project_pigs.id})]",
        })
        task_action = self.env['ir.actions.act_window'].create({
            'name': 'Tasks',
            'res_model': 'project.task',
            'view_mode': 'kanban,list,form',
            'domain': "[('project_id', '=', active_id), ('display_in_project', '=', True)]",
            'context': "{'default_project_id': active_id}",
        })
        task_embedded_action = self.env['ir.embedded.actions'].create({
            'parent_res_model': 'project.project',
            'parent_res_id': self.project_pigs.id,
            'action_id': project_pigs_milestone_action.id,
            'parent_action_id': task_action.id,
        })
        project_model = self.env['ir.model'].search([('model', '=', 'project.task')])
        task_embedded_filter = self.env['ir.filters'].create({
            'name': 'filter',
            'embedded_action_id': task_embedded_action.id,
            'embedded_parent_res_id': self.project_pigs.id,
            'action_id': project_pigs_milestone_action.id,
            'model_id': project_model.id,
        })

        new_project_pigs = self.project_pigs.copy()
        embedded_action = self.env['ir.embedded.actions'].search([
            ('parent_res_model', '=', 'project.project'),
            ('parent_res_id', '=', new_project_pigs.id),
        ])
        self.assertTrue(
            embedded_action,
            'The embedded action linked to project pigs should also be copied.',
        )
        self.assertEqual(
            embedded_action.action_id,
            task_embedded_action.action_id,
            "The new embedded action should have the same action than the one copied.",
        )
        self.assertEqual(
            embedded_action.parent_res_model,
            task_embedded_action.parent_res_model,
        )
        self.assertEqual(
            embedded_action.parent_action_id,
            task_embedded_action.parent_action_id,
        )
        duplicated_task_embedded_filter = embedded_action.filter_ids
        self.assertEqual(
            len(duplicated_task_embedded_filter),
            1,
            "The filter linked to the original embedded action should also be copied."
        )
        self.assertEqual(duplicated_task_embedded_filter.name, f"{task_embedded_filter.name} (copy)")
        self.assertEqual(duplicated_task_embedded_filter.embedded_action_id, embedded_action)
        self.assertEqual(duplicated_task_embedded_filter.embedded_parent_res_id, new_project_pigs.id)
        self.assertEqual(duplicated_task_embedded_filter.action_id, task_embedded_filter.action_id)
        self.assertEqual(duplicated_task_embedded_filter.model_id, task_embedded_filter.model_id)

    def test_mail_on_task_project_change(self):
        """
            This test will check that a mail is sent to the subscribers having the
            "Task created" follow subtype when the project_id of said task changes
        """
        subtype_id = self.env['ir.model.data']._xmlid_to_res_id('project.mt_project_task_new')
        partner = self.env['res.partner'].search([('user_ids', '=', self.user_projectuser.id)])
        self.env['mail.followers'].create({
            'res_model': 'project.project',
            'res_id': self.project_goats.id,
            'partner_id': partner.id,
            'subtype_ids': [subtype_id],  # task created subtype
        })  # set user as follower of project
        with self.mock_mail_gateway():
            self.task_1.project_id = self.project_goats.id
        self.assertSentEmail(self.env.user.email_formatted, [self.user_projectuser.email_formatted])

    def test_do_not_copy_project_stage(self):
        stage = self.env['project.project.stage'].create({'name': 'Custom stage'})  # Default sequence is 50
        self.project_pigs.stage_id = stage.id
        project_copy = self.project_pigs.with_context(default_stage_id=stage.id).copy()
        self.assertNotEqual(project_copy.stage_id, self.project_pigs.stage_id, 'Copied project should have lowest sequence stage')
