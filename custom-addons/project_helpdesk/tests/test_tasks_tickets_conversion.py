# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.exceptions import AccessError
from odoo.tests import new_test_user
from odoo.tests.common import Form

from odoo.addons.helpdesk.tests.common import HelpdeskCommon
from odoo.addons.project.tests.test_project_base import TestProjectCommon


class TestTasksTicketsConversion(TestProjectCommon, HelpdeskCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.ticket_1 = cls.env['helpdesk.ticket'].with_user(cls.helpdesk_user).create({
            'name': 'test ticket 1',
            'team_id': cls.test_team.id,
        })

        cls.ticket_2 = cls.env['helpdesk.ticket'].with_user(cls.helpdesk_user).create({
            'name': 'test ticket 2',
            'team_id': cls.test_team.id,
        })

        cls.task_stage = cls.env['project.task.type'].search([('project_ids', '=', cls.project_goats.id), ('name', '=', 'New')])

    def test_convert_task_to_ticket(self):
        form = Form(self.env['project.task.convert.wizard'].with_context({'to_convert': [self.task_1.id]}))

        form.team_id = self.test_team
        form.stage_id = self.stage_progress

        wizard = form.save()
        view = wizard.action_convert()

        ticket = self.env['helpdesk.ticket'].search([('team_id', '=', self.test_team.id), ('stage_id', '=', self.stage_progress.id)])

        self.assertFalse(self.task_1.active, "Selected task should get archived")
        self.assertEqual(len(ticket), 1, "A ticket should have been created")
        self.assertEqual(ticket.team_id, self.test_team, "Created ticket should be in the selected team")
        self.assertEqual(ticket.stage_id, self.stage_progress, "Created ticket should be in the selected stage")
        self.assertEqual(view['view_mode'], 'form', "Wizard should redirect to a form view")
        self.assertEqual(view['res_model'], 'helpdesk.ticket', "Wizard should redirect to a helpdesk.ticket view")
        self.assertEqual(view['res_id'], ticket.id, "Wizard should redirect to a form view of the created ticket")

    def test_convert_tasks_to_tickets(self):
        form = Form(self.env['project.task.convert.wizard'].with_context({'to_convert': [self.task_1.id, self.task_2.id]}))

        form.team_id = self.test_team
        form.stage_id = self.stage_progress

        wizard = form.save()
        view = wizard.action_convert()

        tickets = self.env['helpdesk.ticket'].search([('team_id', '=', self.test_team.id), ('stage_id', '=', self.stage_progress.id)])

        self.assertFalse(self.task_1.active or self.task_2.active, "Selected tasks should get archived")
        self.assertEqual(len(tickets), 2, "2 tickets should have been created")
        self.assertEqual(tickets.team_id, self.test_team, "Created tickets should be in the selected team")
        self.assertEqual(tickets.stage_id, self.stage_progress, "Created tickets should be in the selected stage")
        self.assertEqual(view['view_mode'], 'tree,form', "Wizard should redirect to a tree view")
        self.assertEqual(view['res_model'], 'helpdesk.ticket', "Wizard should redirect to a helpdesk.ticket view")
        self.assertCountEqual(view['domain'][0][2], tickets.ids, "Wizard should redirect to a tree view of the created tickets")

    def test_convert_task_to_ticket_no_rights(self):
        user = new_test_user(self.env, 'project', 'project.group_project_user')
        with self.assertRaises(AccessError):
            Form(self.env['project.task.convert.wizard'].with_user(user).with_context({'to_convert': [self.task_1.id]}))

    def test_convert_ticket_to_task(self):
        form = Form(self.env['helpdesk.ticket.convert.wizard'].with_context({'to_convert': [self.ticket_1.id]}))

        form.project_id = self.project_goats
        form.stage_id = self.task_stage

        wizard = form.save()
        view = wizard.action_convert()

        task = self.env['project.task'].search([('project_id', '=', self.project_goats.id), ('stage_id', '=', self.task_stage.id)])

        self.assertFalse(self.ticket_1.active, "Selected ticket should get archived")
        self.assertEqual(len(task), 1, "A task should have been created")
        self.assertEqual(task.project_id, self.project_goats, "Created task should be in the selected project")
        self.assertEqual(task.stage_id, self.task_stage, "Created task should be in the selected stage")
        self.assertEqual(view['view_mode'], 'form', "Wizard should redirect to a form view")
        self.assertEqual(view['res_model'], 'project.task', "Wizard should redirect to a project.task view")
        self.assertEqual(view['res_id'], task.id, "Wizard should redirect to a form view of the created task")

    def test_convert_tickets_to_tasks(self):
        form = Form(self.env['helpdesk.ticket.convert.wizard'].with_context({'to_convert': [self.ticket_1.id, self.ticket_2.id]}))

        form.project_id = self.project_goats
        form.stage_id = self.task_stage

        wizard = form.save()
        view = wizard.action_convert()

        tasks = self.env['project.task'].search([('project_id', '=', self.project_goats.id), ('stage_id', '=', self.task_stage.id)])

        self.assertFalse(self.ticket_1.active or self.ticket_2.active, "Selected tickets should get archived")
        self.assertEqual(len(tasks), 2, "2 tasks should have been created")
        self.assertEqual(tasks.project_id, self.project_goats, "Created tasks should be in the selected project")
        self.assertEqual(tasks.stage_id, self.task_stage, "Created tasks should be in the selected stage")
        self.assertEqual(view['view_mode'], 'tree,form', "Wizard should redirect to a tree view")
        self.assertEqual(view['res_model'], 'project.task', "Wizard should redirect to a project.task view")
        self.assertCountEqual(view['domain'][0][2], tasks.ids, "Wizard should redirect to a tree view of the created tasks")

    def test_convert_ticket_to_task_no_rights(self):
        user = new_test_user(self.env, 'helpdesk', 'helpdesk.group_helpdesk_user')
        with self.assertRaises(AccessError):
            Form(self.env['helpdesk.ticket.convert.wizard'].with_user(user).with_context({'to_convert': [self.ticket_1.id]}))
