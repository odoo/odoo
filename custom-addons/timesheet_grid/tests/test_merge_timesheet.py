# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import fields
from odoo.tests.common import Form

from odoo.addons.hr_timesheet.tests.test_timesheet import TestCommonTimesheet

class TestTimesheetMerge(TestCommonTimesheet):

    def setUp(self):
        super(TestTimesheetMerge, self).setUp()

        yesterday = fields.Date.today() - timedelta(days=1)
        self.timesheet1 = self.env['account.analytic.line'].with_user(self.user_employee).create({
            'name': "my timesheet 1",
            'project_id': self.project_customer.id,
            'task_id': self.task1.id,
            'date': yesterday,
            'unit_amount': 1.0,
        })
        self.timesheet2 = self.env['account.analytic.line'].with_user(self.user_employee).create({
            'name': "my timesheet 2",
            'project_id': self.project_customer.id,
            'task_id': self.task2.id,
            'date': yesterday,
            'unit_amount': 2.0,
        })
        self.timesheet3 = self.env['account.analytic.line'].with_user(self.user_employee).create({
            'name': "my timesheet 2",
            'project_id': self.project_customer.id,
            'task_id': self.task2.id,
            'date': yesterday,
            'unit_amount': 3.0,
        })
        self.timesheet3.with_user(self.user_manager).action_validate_timesheet()

    def test_action_merge_validated(self):
        action = (self.timesheet2 + self.timesheet3).action_merge_timesheets()

        # Cannot merge a validated timesheet
        self.assertEqual(action.get('type'), 'ir.actions.client')
        self.assertEqual(action.get('tag'), 'display_notification')

        action = (self.timesheet1 + self.timesheet2).action_merge_timesheets()

        # Should open the wizard
        self.assertEqual(action.get('type'), 'ir.actions.act_window')

    def test_merge_timesheets(self):
        ctx = {'active_ids': [self.timesheet1.id, self.timesheet2.id, self.timesheet3.id]}
        wizard = Form(self.env['hr_timesheet.merge.wizard'].with_context(ctx)).save()

        self.assertEqual(wizard.unit_amount, 3.0, "should not consider the validated timesheet")
        self.assertEqual(wizard.task_id, self.task1, "should take the task of the 1st timesheet")
        wizard.action_merge()

        timesheets = self.env['account.analytic.line'].search([('project_id', '=', self.project_customer.id), ('date', '=', fields.Date.today() - timedelta(days=1))])
        self.assertEqual(len(timesheets), 2)

        merged_timesheet = timesheets.filtered(lambda l: not l.validated)
        self.assertEqual(merged_timesheet.name, "my timesheet 1 / my timesheet 2")
        self.assertEqual(merged_timesheet.unit_amount, 3.0)
