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
