# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon


class TestResourceCalendarLeaves(TestHrHolidaysCommon):
    def test_compute_associated_leaves_count(self):
        """Test the computation of associated_leaves_count, ensuring it correctly sums
        leaves specific to the calendar (calendar_id=self.id) and global leaves (calendar_id=False).
        """
        calendar_a = self.env['resource.calendar'].create({'name': 'Calendar A'})
        calendar_b = self.env['resource.calendar'].create({'name': 'Calendar B'})

        leave_a_1 = self.env['resource.calendar.leaves'].create({
            'name': 'CalendarA Specific Leave_1',
            'calendar_id': calendar_a.id,
            'date_from': datetime(2025, 1, 1),
            'date_to': datetime(2025, 1, 1),
        })

        leave_b_1 = self.env['resource.calendar.leaves'].create({
            'name': 'CalendarB Specific Leave_1',
            'calendar_id': calendar_b.id,
            'date_from': datetime(2025, 2, 1),
            'date_to': datetime(2025, 2, 1),
        })

        global_leave_1 = self.env['resource.calendar.leaves'].create({
            'name': 'Global Leave 1',
            'calendar_id': False,
            'date_from': datetime(2025, 3, 1),
            'date_to': datetime(2025, 3, 1),
        })

        # 1. Initial check: calendar_a (1 specific + 1 global = 2), calendar_b (1 specific + 1 global = 2)
        (calendar_a | calendar_b)._compute_associated_leaves_count()
        self.assertEqual(calendar_a.associated_leaves_count, 2, "Calendar A should have 1 specific + 1 global leave.")
        self.assertEqual(calendar_b.associated_leaves_count, 2, "Calendar B should have 1 specific + 1 global leave.")

        self.env['resource.calendar.leaves'].create({
            'name': 'Global Leave 2',
            'calendar_id': False,
            'date_from': datetime(2025, 4, 1),
            'date_to': datetime(2025, 4, 1),
        })

        # 2. Test updated counts: calendar_a (1 specific + 2 global = 3), calendar_b (1 specific + 2 global = 3)
        (calendar_a | calendar_b)._compute_associated_leaves_count()
        self.assertEqual(calendar_a.associated_leaves_count, 3, "Calendar A should have 1 specific + 2 global leaves.")
        self.assertEqual(calendar_b.associated_leaves_count, 3, "Calendar B should have 1 specific + 2 global leaves.")

        self.env['resource.calendar.leaves'].create({
            'name': 'CalendarA Specific Leave_2',
            'calendar_id': calendar_a.id,
            'date_from': datetime(2025, 2, 1),
            'date_to': datetime(2025, 2, 1),
        })

        # 3. Test updated counts: calendar_a (2 specific + 2 global = 4), calendar_b (1 specific + 2 global = 3)
        (calendar_a | calendar_b)._compute_associated_leaves_count()
        self.assertEqual(calendar_a.associated_leaves_count, 4, "Calendar A should have 2 specific + 2 global leaves.")
        self.assertEqual(calendar_b.associated_leaves_count, 3, "Calendar B should have 1 specific + 2 global leaves.")

        # 4. Test Remove a global leave: calendar_a (2 specific + 1 global = 3), calendar_b (1 specific + 1 global = 2)
        global_leave_1.unlink()
        (calendar_a | calendar_b)._compute_associated_leaves_count()
        self.assertEqual(calendar_a.associated_leaves_count, 3, "Calendar A should have 2 specific + 1 remaining global leave.")
        self.assertEqual(calendar_b.associated_leaves_count, 2, "Calendar B should have 1 specific + 1 remaining global leave.")

        # 5. Test Remove a specific leave to have no leaves specific to calendar_b:
        # calendar_a (2 specific + 1 global = 3), calendar_b (0 specific + 1 global = 1)
        leave_b_1.unlink()
        (calendar_a | calendar_b)._compute_associated_leaves_count()
        self.assertEqual(calendar_a.associated_leaves_count, 3, "Calendar A should still have 2 specific + 1 global leave.")
        self.assertEqual(calendar_b.associated_leaves_count, 1, "Calendar B should have 0 specific + 1 global leave.")

        # 6. Test Remove a specific leave calendar_a: calendar_a (1 specific + 1 global = 2), calendar_b (0 specific + 1 global = 1)
        leave_a_1.unlink()
        (calendar_a | calendar_b)._compute_associated_leaves_count()
        self.assertEqual(calendar_a.associated_leaves_count, 2, "Calendar A should still have 2 specific + 1 global leave.")
        self.assertEqual(calendar_b.associated_leaves_count, 1, "Calendar B should have 0 specific + 1 global leave.")

    def test_duration_visibility(self):
        # Create a working schedule with no work on friday afternoon
        self.calendar_34h = self.env['resource.calendar'].create({
            'name': 'Standard 34 hours/week',
            'company_id': False,
            'hours_per_day': 6.833,
            'attendance_ids': [(5, 0, 0),
                    (0, 0, {'dayofweek': '0', 'duration_hours': 7.6, 'hour_from': 0, 'hour_to': 0}),
                    (0, 0, {'dayofweek': '1', 'duration_hours': 7.6, 'hour_from': 0, 'hour_to': 0}),
                    (0, 0, {'dayofweek': '2', 'duration_hours': 7.6, 'hour_from': 0, 'hour_to': 0}),
                    (0, 0, {'dayofweek': '3', 'duration_hours': 7.6, 'hour_from': 0, 'hour_to': 0}),
                    (0, 0, {'dayofweek': '4', 'duration_hours': 3.8, 'hour_from': 0, 'hour_to': 0}),

                    ],
        })
        test_leave_type = self.env['hr.leave.type'].create({
            'name': 'Test type',
            'request_unit': 'half_day',
            'unit_of_measure': 'day',
            'leave_validation_type': 'no_validation',
            'time_type': 'leave',
            'requires_allocation': False,
        })

        self.employee_emp.resource_calendar_id = self.calendar_34h.id
        test_leave = self.env['hr.leave'].create({
            'name': 'Test Leave',
            'employee_id': self.employee_emp.id,
            'holiday_status_id': test_leave_type.id,
            'request_date_from': '2026-02-09',  # Monday
            'request_date_to': '2026-02-13',
        })
        self.assertEqual(test_leave.number_of_days, 4.5)
        self.assertEqual(test_leave.duration_display, '4.5 days')
