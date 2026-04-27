# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime, timedelta
from freezegun import freeze_time

from odoo import Command

from odoo.addons.helpdesk.tests.common import HelpdeskCommon
from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon


class TestHelpdeskHolidays(HelpdeskCommon, TestHrHolidaysCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.leave_type = cls.env['hr.leave.type'].create({
            'name': 'Legal Leaves',
            'time_type': 'leave',
            'requires_allocation': 'no',
        })

        cls.user_hruser.groups_id |= cls.env.ref('helpdesk.group_helpdesk_user')
        cls.user_hrmanager.groups_id |= cls.env.ref('helpdesk.group_helpdesk_manager')
        cls.user_employee.groups_id |= cls.env.ref('helpdesk.group_helpdesk_user')

        cls.company_2 = cls.env['res.company'].create({
            'name': 'Company 2',
        })
        cls.employee_emp.company_id = cls.company_2

        cls.test_team.write({
            'auto_assignment': True,
            'assign_method': 'randomly',
            'member_ids': [
                Command.set([
                    cls.user_hruser_id,
                    cls.user_hrmanager_id,
                    cls.user_employee_id,
                ]),
            ],
        })

    def new_ticket(self):
        return self.env['helpdesk.ticket'].create({
            'name': 'Ticket',
            'team_id': self.test_team.id,
        })

    def test_random_assignment_employee_time_off(self):
        leave = self.env['hr.leave'].create({
            'employee_id': self.employee_hruser.id,
            'holiday_status_id': self.leave_type.id,
            'request_date_from': date.today(),
            'request_date_to': date.today() + timedelta(days=6),
        })
        leave.action_approve()

        self.assertEqual(self.new_ticket().user_id, self.user_hrmanager, "The created ticket should be automatically assigned to hrmanager")
        self.assertEqual(self.new_ticket().user_id, self.user_employee, "The created ticket should be automatically assigned to employee")
        self.assertEqual(self.new_ticket().user_id, self.user_hrmanager, "The created ticket should be automatically assigned to hrmanager")

    def test_balanced_assignment_employee_time_off(self):
        self.test_team.assign_method = 'balanced'

        for i, (stage_id, user_id) in enumerate((
            (self.stage_new, self.user_hrmanager),
            (self.stage_new, self.user_employee),
            (self.stage_progress, self.user_employee),
        )):
            self.env['helpdesk.ticket'].create({
                'name': f"Ticket {i}",
                'team_id': self.test_team.id,
                'stage_id': stage_id.id,
                'user_id': user_id.id,
            })

        leave = self.env['hr.leave'].create({
            'employee_id': self.employee_hrmanager.id,
            'holiday_status_id': self.leave_type.id,
            'request_date_from': date.today(),
            'request_date_to': date.today() + timedelta(days=6),
        })
        leave.action_approve()

        self.assertEqual(self.new_ticket().user_id, self.user_hruser, "The created ticket should be automatically assigned to hruser")
        self.assertEqual(self.new_ticket().user_id, self.user_hruser, "The created ticket should be automatically assigned to hruser")
        self.assertEqual(self.new_ticket().user_id, self.user_hruser, "The created ticket should be automatically assigned to hruser")

    def test_assignment_global_leave(self):
        self.env['resource.calendar.leaves'].create({
            'date_from': datetime.now().strftime('%Y-%m-%d 00:00:00'),
            'date_to': (datetime.now() + timedelta(days=6)).strftime('%Y-%m-%d 23:59:59'),
        })

        self.assertEqual(self.new_ticket().user_id, self.user_employee, "The created ticket should be automatically assigned to employee")
        self.assertEqual(self.new_ticket().user_id, self.user_employee, "The created ticket should be automatically assigned to employee")
        self.assertEqual(self.new_ticket().user_id, self.user_employee, "The created ticket should be automatically assigned to employee")

    # Freeze the time a Monday, so that it's outside the working schedule
    @freeze_time('2022-03-14')
    def test_assignment_resource_calendar(self):
        self.employee_hruser.resource_id.calendar_id = self.env['resource.calendar'].create({
            'name': 'Half Week',
            'hours_per_day': 8.0,
            'attendance_ids': [
                (0, 0, {'name': 'Wednesday Afternoon', 'dayofweek': '2', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Thursday Lunch', 'dayofweek': '3', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Thursday Afternoon', 'dayofweek': '3', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Friday Morning', 'dayofweek': '4', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Friday Lunch', 'dayofweek': '4', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Friday Afternoon', 'dayofweek': '4', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'})
            ]
        })

        self.assertEqual(self.new_ticket().user_id, self.user_hrmanager, "The created ticket should be automatically assigned to hrmanager")
        self.assertEqual(self.new_ticket().user_id, self.user_employee, "The created ticket should be automatically assigned to employee")
        self.assertEqual(self.new_ticket().user_id, self.user_hrmanager, "The created ticket should be automatically assigned to hrmanager")
