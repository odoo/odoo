from odoo.addons.test_resource.tests.common import TestResourceCommon


class TestResourceType(TestResourceCommon):
    def test_resource_type_change_fully_fixed_fixed_time(self):
        default_calendar = self.env["resource.calendar"].create(
            {
                "name": "Default Calendar",
            }
        )

        # check on the default attendance and type
        self.assertEqual(default_calendar.schedule_type, "fully_fixed", "Default calendar should be fully_fixed")
        self.assertEqual(
            len(default_calendar.attendance_ids),
            15,  # Should have 3 attendances for each of the 5 days (morning, lunch, afternoon)
            "Default calendar should have a default attendance with 15 attendances",
        )
        self.assertEqual(
            default_calendar.hours_per_day,
            8.0,
            "Default calendar should have an average hours per day = 8.0 hours",
        )
        # switch to fixed time and check the new attendance
        default_calendar.schedule_type = "fixed_time"
        self.assertEqual(default_calendar.schedule_type, "fixed_time", "Default calendar should be fixed_time")
        self.assertEqual(
            len(default_calendar.attendance_ids),
            5,  # Should have 1 attendance for each of the 5 days
            "Default calendar should have a default attendance with 5 attendances",
        )
        self.assertEqual(
            default_calendar.attendance_ids[0].duration_hours,
            8.0,
            "Default calendar should have a default attendance with duration = 8.0 hours",
        )
        default_calendar.attendance_ids[0].unlink()
        # check if the attendance is removed
        self.assertEqual(
            len(default_calendar.attendance_ids),
            4,  # Should have 1 attendance for each of the 5 days
            "Default calendar should have a default attendance with 4 attendances",
        )
        self.assertEqual(
            default_calendar.hours_per_day,
            8.0,
            "Default calendar should have an average hours per day = 8.0 hours",
        )
        # switch back and check if reset to default
        default_calendar.schedule_type = "fully_fixed"
        self.assertEqual(default_calendar.schedule_type, "fully_fixed", "Default calendar should be fully_fixed")
        self.assertEqual(
            len(default_calendar.attendance_ids),
            15,  # Should have 3 attendances for each of the 5 days (morning, lunch, afternoon)
            "Default calendar should have a default attendance with 15 attendances",
        )
        self.assertEqual(
            default_calendar.hours_per_day,
            8.0,
            "Default calendar should have an average hours per day = 8.0 hours",
        )
