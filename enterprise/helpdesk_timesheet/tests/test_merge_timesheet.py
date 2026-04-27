# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import ValidationError
from odoo.tests import Form

from .common import TestHelpdeskTimesheetCommon


class TestTimesheetMerge(TestHelpdeskTimesheetCommon):

    def test_merge_helpdesk_timesheets(self):
        another_ticket = self.env['helpdesk.ticket'].create({
            'name': 'Test Ticket 2',
            'team_id': self.helpdesk_team.id,
            'partner_id': self.partner.id,
        })
        helpdesk_timesheet_1, helpdesk_timesheet_2, helpdesk_timesheet_3, timesheet_1 = self.env['account.analytic.line'].with_user(self.user_employee).create([
            {
                'name': "Timesheet linked to helpdesk ticket",
                'project_id': self.project.id,
                'helpdesk_ticket_id': self.helpdesk_ticket.id,
                'unit_amount': 1.0,
            },
            {
                'name': "Timesheet linked to the same helpdesk ticket",
                'project_id': self.project.id,
                'helpdesk_ticket_id': self.helpdesk_ticket.id,
                'unit_amount': 1.0,
            },
            {
                'name': "Timesheet linked to another helpdesk ticket",
                'project_id': self.project.id,
                'helpdesk_ticket_id': another_ticket.id,
                'unit_amount': 1.0,
            },
            {
                'name': "Timesheet not linked to a helpdesk ticket",
                'project_id': self.project.id,
                'unit_amount': 1.0,
            },
        ])

        ctx = {'active_ids': [helpdesk_timesheet_1.id, timesheet_1.id]}
        with self.assertRaises(ValidationError):
            Form(self.env['hr_timesheet.merge.wizard'].with_context(ctx)).save()

        ctx = {'active_ids': [helpdesk_timesheet_1.id, helpdesk_timesheet_3.id]}
        with self.assertRaises(ValidationError):
            Form(self.env['hr_timesheet.merge.wizard'].with_context(ctx)).save()

        ctx = {'active_ids': [helpdesk_timesheet_1.id, helpdesk_timesheet_2.id]}
        wizard = Form(self.env['hr_timesheet.merge.wizard'].with_context(ctx)).save()
        wizard.action_merge()

        merged_timesheet = self.env['account.analytic.line'].search([('project_id', '=', self.project.id), ('name', 'like', 'Timesheet linked to helpdesk ticket')])
        self.assertEqual(len(merged_timesheet), 1)
        self.assertEqual(merged_timesheet.unit_amount, 2.0)
        self.assertEqual(merged_timesheet.helpdesk_ticket_id, self.helpdesk_ticket)
