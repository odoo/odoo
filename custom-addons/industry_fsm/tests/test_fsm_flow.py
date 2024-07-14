# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details

from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests import tagged
from odoo.tests.common import users

from .common import TestIndustryFsmCommon

@tagged('post_install', '-at_install')
class TestFsmFlow(TestIndustryFsmCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project = cls.env['project.project'].create({
            'name': 'project 2',
            'privacy_visibility': 'followers',
        })

    def test_stop_timers_on_mark_as_done(self):
        self.assertEqual(len(self.task.sudo().timesheet_ids), 0, 'There is no timesheet associated to the task')
        timesheet = self.env['account.analytic.line'].with_user(self.marcel_user).create({'name': '', 'project_id': self.fsm_project.id})
        timesheet.action_add_time_to_timer(3)
        timesheet.action_change_project_task(self.fsm_project.id, self.task.id)
        self.assertTrue(timesheet.user_timer_id, 'A timer is linked to the timesheet')
        self.assertTrue(timesheet.user_timer_id.is_timer_running, 'The timer linked to the timesheet is running')
        task_with_henri_user = self.task.with_user(self.henri_user)
        task_with_henri_user.action_timer_start()
        self.assertTrue(task_with_henri_user.user_timer_id, 'A timer is linked to the task')
        self.assertTrue(task_with_henri_user.user_timer_id.is_timer_running, 'The timer linked to the task is running')
        task_with_george_user = self.task.with_user(self.george_user)
        result = task_with_george_user.action_fsm_validate()
        self.assertEqual(result['type'], 'ir.actions.act_window', 'As there are still timers to stop, an action is returned')
        Timer = self.env['timer.timer']
        tasks_running_timer_ids = Timer.search([('res_model', '=', 'project.task'), ('res_id', '=', self.task.id)])
        timesheets_running_timer_ids = Timer.search([('res_model', '=', 'account.analytic.line'), ('res_id', '=', timesheet.id)])
        self.assertEqual(len(timesheets_running_timer_ids), 1, 'There is still a timer linked to the timesheet')
        self.task.invalidate_model(['timesheet_ids'])
        self.assertEqual(len(tasks_running_timer_ids), 1, 'There is still a timer linked to the task')
        wizard = self.env['project.task.stop.timers.wizard'].create({'line_ids': [Command.create({'task_id': self.task.id})]})
        wizard.action_confirm()
        tasks_running_timer_ids = Timer.search([('res_model', '=', 'project.task'), ('res_id', '=', self.task.id)])
        timesheets_running_timer_ids = Timer.search([('res_model', '=', 'account.analytic.line'), ('res_id', '=', timesheet.id)])
        self.assertFalse(timesheets_running_timer_ids, 'There is no more timer linked to the timesheet')
        self.task.invalidate_model(['timesheet_ids'])
        self.assertFalse(tasks_running_timer_ids, 'There is no more timer linked to the task')
        self.assertEqual(len(self.task.sudo().timesheet_ids), 2, 'There are two timesheets')

    def test_mark_task_done_state_change(self):
        self.task.write({
            'state': '01_in_progress',
        })
        self.task.action_fsm_validate()
        self.assertEqual(self.task.state, '1_done', 'task state should change to done')

        second_task = self.env['project.task'].create({
            'name': 'Fsm task 2',
            'project_id': self.fsm_project.id,
            'partner_id': self.partner.id,
            'state': '02_changes_requested',
        })

        second_task.action_fsm_validate()
        self.assertEqual(second_task.state, '1_done', 'second task state should change to done')

    @users('Project user', 'Project admin', 'Base user')
    def test_base_user_no_create_stop_timers_wizard(self):
        with self.assertRaises(AccessError):
            self.env['project.task.stop.timers.wizard'].with_user(self.env.user).create({'line_ids': [Command.create({'task_id': self.task.id})]})

    @users('Fsm user')
    def test_fsm_user_can_create_stop_timers_wizard(self):
        self.env['project.task.stop.timers.wizard'].with_user(self.env.user).create({'line_ids': [Command.create({'task_id': self.task.id})]})
